"""Bounded LLM extraction of language-agnostic component interface facts."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import or_
from sqlmodel import Session, select

from aespa.config import get_settings
from aespa.db import get_engine
from aespa.models import (
    ApplicationComponent,
    AssessmentCampaign,
    CampaignSourceMember,
    ComponentConnection,
    ComponentFact,
    ComponentSnapshot,
    SastRun,
    ScanLead,
    ScanLeadComponentProvenance,
)
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import settings as settings_svc
from aespa.services.component_facts import interface_fact_fingerprint
from aespa.services.prompts.component_mapper import (
    COMPONENT_MAPPER_SYSTEM_PROMPT,
    COMPONENT_MAPPER_TOOLS,
)
from aespa.services.source_tools import (
    glob_files,
    grep,
    jail,
    list_files,
    read_file,
    safe_unzip,
)

log = logging.getLogger(__name__)


def _format_tool_desc(tool_name: str, tool_input: dict) -> str:
    if tool_name == "list_files":
        path = tool_input.get("path") or "."
        return f"listed files in '{path}'"
    if tool_name == "glob":
        pattern = tool_input.get("pattern") or "*"
        return f"matched glob pattern '{pattern}'"
    if tool_name == "read_file":
        path = tool_input.get("path") or ""
        start = tool_input.get("start_line")
        end = tool_input.get("end_line")
        lines = f":L{start}-L{end}" if start and end else ""
        return f"read source file '{path}{lines}'"
    if tool_name == "grep":
        pattern = tool_input.get("pattern") or ""
        path = tool_input.get("path") or ""
        scope = f" in '{path}'" if path else ""
        return f"searched pattern '{pattern}'{scope}"
    if tool_name == "record_interface_fact":
        fact_type = tool_input.get("fact_type") or "fact"
        name = tool_input.get("name") or tool_input.get("path") or ""
        return f"recorded {fact_type} fact '{name}'"
    if tool_name == "done":
        return "completed interface mapping"
    return f"executed {tool_name}"


_FACT_TYPES = {
    "route",
    "http_call",
    "ui_route",
    "ui_action",
    "handler",
    "lead_anchor",
    "queue_publish",
    "queue_consume",
    "rpc_client",
    "rpc_server",
}
_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
_MAX_STRING = 2000
_LOCATION_RE = re.compile(r"^(?P<path>.+):(?P<line>[1-9][0-9]*)$")


class ComponentMappingError(RuntimeError):
    """Base class for source interface mapping failures."""


class CorrelationTransientError(ComponentMappingError):
    """A provider/protocol failure that can be retried without rerunning SAST."""


@dataclass(frozen=True)
class ComponentMappingResult:
    component_id: int
    sast_run_id: int
    facts_recorded: int
    facts_rejected: int
    tool_calls: int
    summary: str


def _parse_location(value: object) -> tuple[str, int] | None:
    if not isinstance(value, str):
        return None
    match = _LOCATION_RE.fullmatch(value.strip().replace("\\", "/"))
    if not match:
        return None
    path = match.group("path")
    if path.startswith("/") or path == ".." or "/../" in f"/{path}/":
        return None
    return path, int(match.group("line"))


def _line_count(root: Path, relative_path: str) -> int:
    target = jail(root, relative_path)
    if not target.is_file():
        raise ValueError(f"not a file: {relative_path!r}")
    return len(target.read_text(encoding="utf-8", errors="replace").splitlines())


def _validate_evidence(
    root: Path,
    location: object,
    read_ranges: dict[str, list[tuple[int, int]]],
) -> tuple[str, int]:
    parsed = _parse_location(location)
    if parsed is None:
        raise ValueError("evidence_location must be a relative file:line")
    path, line = parsed
    total_lines = _line_count(root, path)
    if line > total_lines:
        raise ValueError(f"evidence line is outside file: {path}:{line}")
    ranges = read_ranges.get(path, [])
    if not any(start <= line <= end for start, end in ranges):
        raise ValueError(f"evidence location was not read: {path}:{line}")
    return path, line


def _record_read_range(
    root: Path,
    read_ranges: dict[str, list[tuple[int, int]]],
    path: str,
    start_line: int | None,
    end_line: int | None,
    result: str,
) -> None:
    parsed_path = _parse_location(f"{path}:1")
    if parsed_path is None:
        return
    relative = parsed_path[0]
    try:
        total = _line_count(root, relative)
    except (OSError, ValueError):
        return
    start = max(1, start_line or 1)
    requested_end = end_line or total
    if "[... truncated ...]" in result:
        returned = max(0, len(result.splitlines()) - 1)
        requested_end = min(requested_end, start + returned - 1)
    read_ranges.setdefault(relative, []).append((start, min(requested_end, total)))


def _merge_detail(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    origins = set(merged.get("origins") or [])
    origin = merged.get("origin")
    if origin:
        origins.add(origin)
    elif not origins:
        origins.add("deterministic")
    origins.update(incoming.get("origins") or [])
    origins.add("llm")
    merged["origins"] = sorted(origins)
    merged["origin"] = "llm" if origins == {"llm"} else "deterministic+llm"
    if incoming.get("confidence") is not None:
        merged["llm_confidence"] = incoming["confidence"]
    if incoming.get("reasoning"):
        merged["llm_reasoning"] = incoming["reasoning"]
    locations = set(merged.get("supporting_locations") or [])
    locations.update(incoming.get("supporting_locations") or [])
    if incoming.get("evidence_location"):
        locations.add(incoming["evidence_location"])
    merged["supporting_locations"] = sorted(locations)[:8]
    return merged


def _delete_component_facts(session: Session, rows: list[ComponentFact]) -> None:
    """Delete facts after clearing graph and provenance references."""
    fact_ids = {row.id for row in rows if row.id is not None}
    if not fact_ids:
        return

    for connection in session.exec(
        select(ComponentConnection).where(
            or_(
                ComponentConnection.source_fact_id.in_(fact_ids),
                ComponentConnection.target_fact_id.in_(fact_ids),
            )
        )
    ).all():
        session.delete(connection)
    for provenance in session.exec(
        select(ScanLeadComponentProvenance).where(
            ScanLeadComponentProvenance.fact_id.in_(fact_ids)
        )
    ).all():
        provenance.fact_id = None
        session.add(provenance)
    session.flush()
    for row in rows:
        session.delete(row)


def purge_llm_component_facts(sast_run_id: int) -> int:
    """Purge previously recorded LLM ComponentFact rows for one run."""
    with Session(get_engine()) as session:
        all_rows = list(
            session.exec(
                select(ComponentFact).where(ComponentFact.sast_run_id == sast_run_id)
            ).all()
        )
        rows = []
        for row in all_rows:
            try:
                detail = json.loads(row.detail_json or "{}")
            except (TypeError, ValueError):
                detail = {}
            if "llm" in str(detail.get("origin") or "").lower():
                rows.append(row)
        deleted = len(rows)
        if not rows:
            return 0

        _delete_component_facts(session, rows)
        session.commit()
        return deleted


def _persist_facts(
    *,
    sast_run_id: int,
    component_id: int,
    facts: list[dict],
) -> int:
    with Session(get_engine()) as session:
        existing_rows = list(
            session.exec(
                select(ComponentFact).where(ComponentFact.sast_run_id == sast_run_id)
            ).all()
        )
        stale_rows = []
        for row in existing_rows:
            try:
                detail = json.loads(row.detail_json or "{}")
            except (TypeError, ValueError):
                detail = {}
            if "llm" in str(detail.get("origin") or "").lower():
                stale_rows.append(row)
        _delete_component_facts(session, stale_rows)
        session.flush()

        existing_rows = list(
            session.exec(
                select(ComponentFact).where(ComponentFact.sast_run_id == sast_run_id)
            ).all()
        )
        by_fingerprint = {row.fingerprint: row for row in existing_rows}
        for row in existing_rows:
            semantic_fingerprint = interface_fact_fingerprint(
                fact_type=row.fact_type,
                method=row.method,
                path=row.path,
                host=row.host,
                name=row.name,
            )
            by_fingerprint.setdefault(semantic_fingerprint, row)
        recorded = 0
        for raw in facts:
            fingerprint = interface_fact_fingerprint(
                fact_type=raw["fact_type"],
                method=raw.get("method"),
                path=raw.get("path"),
                host=raw.get("host"),
                name=raw.get("name"),
            )
            detail = {
                "origin": "llm",
                "confidence": raw["confidence"],
                "reasoning": raw["reasoning"],
                "supporting_locations": raw["supporting_locations"],
                **(raw["detail"] if isinstance(raw.get("detail"), dict) else {}),
            }
            row = by_fingerprint.get(fingerprint)
            if row is None:
                row = ComponentFact(
                    sast_run_id=sast_run_id,
                    component_id=component_id,
                    fact_type=raw["fact_type"],
                    method=raw.get("method"),
                    path=raw.get("path"),
                    host=raw.get("host"),
                    name=raw.get("name"),
                    detail_json=json.dumps(detail),
                    evidence_location=raw["evidence_location"],
                    fingerprint=fingerprint,
                )
                session.add(row)
                by_fingerprint[fingerprint] = row
                recorded += 1
                continue
            try:
                old_detail = json.loads(row.detail_json or "{}")
            except (TypeError, ValueError):
                old_detail = {}
            row.detail_json = json.dumps(_merge_detail(old_detail, detail))
            row.component_id = component_id
            row.fingerprint = fingerprint
            session.add(row)
            recorded += 1
        session.commit()
        return recorded


def _load_component_context(
    campaign_id: int, member_id: int
) -> tuple[
    AssessmentCampaign,
    CampaignSourceMember,
    ApplicationComponent,
    ComponentSnapshot,
    SastRun,
]:
    with Session(get_engine()) as session:
        campaign = session.get(AssessmentCampaign, campaign_id)
        member = session.get(CampaignSourceMember, member_id)
        if campaign is None or member is None or member.campaign_id != campaign_id:
            raise ComponentMappingError(
                "Campaign source member does not belong to campaign"
            )
        component = session.get(ApplicationComponent, member.component_id)
        snapshot = session.get(ComponentSnapshot, member.snapshot_id)
        run = session.get(SastRun, member.sast_run_id) if member.sast_run_id else None
        if component is None or snapshot is None or run is None:
            raise ComponentMappingError(
                "Campaign source member has incomplete source metadata"
            )
        if run.status != "completed":
            raise ComponentMappingError(
                f"SAST run {run.id} is not completed (status={run.status!r})"
            )
        return campaign, member, component, snapshot, run


def _validate_fact(
    root: Path,
    raw: dict,
    read_ranges: dict[str, list[tuple[int, int]]],
    eligible_lead_ids: set[int] | None = None,
) -> dict:
    fact_type = raw.get("fact_type")
    if fact_type not in _FACT_TYPES:
        raise ValueError(f"unsupported interface fact type: {fact_type!r}")
    method = raw.get("method")
    if method is not None:
        method = str(method).upper()
        if method not in _HTTP_METHODS:
            raise ValueError(f"unsupported HTTP method: {method!r}")
    evidence_location, _line = _validate_evidence(
        root, raw.get("evidence_location"), read_ranges
    )
    confidence = float(raw.get("confidence", 0.0))
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    supporting: list[str] = []
    for location in list(raw.get("supporting_locations") or [])[:8]:
        parsed = _parse_location(location)
        if parsed is None:
            continue
        try:
            _validate_evidence(root, location, read_ranges)
        except ValueError:
            continue
        supporting.append(f"{parsed[0]}:{parsed[1]}")
    detail = dict(raw.get("detail")) if isinstance(raw.get("detail"), dict) else {}
    for key in (
        "handler_locations",
        "route_locations",
        "trigger_locations",
        "source_locations",
        "related_locations",
    ):
        values = detail.get(key)
        if isinstance(values, str):
            values = [values]
        if values is None:
            continue
        if not isinstance(values, list):
            raise ValueError(f"detail.{key} must be a list of file:line values")
        validated_locations: list[str] = []
        for location in values[:8]:
            parsed_location, line = _validate_evidence(root, location, read_ranges)
            validated_locations.append(f"{parsed_location}:{line}")
        detail[key] = validated_locations
    if "handler_location" in detail:
        parsed_location, line = _validate_evidence(
            root, detail["handler_location"], read_ranges
        )
        detail["handler_location"] = f"{parsed_location}:{line}"
    if "route_location" in detail:
        parsed_location, line = _validate_evidence(
            root, detail["route_location"], read_ranges
        )
        detail["route_location"] = f"{parsed_location}:{line}"
    if "source_location" in detail:
        parsed_location, line = _validate_evidence(
            root, detail["source_location"], read_ranges
        )
        detail["source_location"] = f"{parsed_location}:{line}"
    if fact_type == "lead_anchor":
        try:
            lead_id = int(detail["lead_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("lead_anchor facts require a lead_id") from exc
        if eligible_lead_ids is not None and lead_id not in eligible_lead_ids:
            raise ValueError("lead_anchor references an ineligible SAST lead")
    result = {
        "fact_type": fact_type,
        "method": method,
        "path": str(raw.get("path") or "")[:_MAX_STRING] or None,
        "host": str(raw.get("host") or "")[:_MAX_STRING] or None,
        "name": str(raw.get("name") or "")[:_MAX_STRING] or None,
        "confidence": confidence,
        "evidence_location": f"{evidence_location}:{_line}",
        "supporting_locations": supporting,
        "reasoning": str(raw.get("reasoning") or "")[:1000],
        "detail": detail,
    }
    if fact_type in {"route", "http_call", "ui_route"} and not result["path"]:
        raise ValueError("route and http_call facts require a path")
    if fact_type not in {"route", "http_call"} and not (
        result["name"] or result["path"]
    ):
        raise ValueError("non-HTTP interface facts require a name or path")
    return result


async def map_campaign_component(
    campaign_id: int,
    member_id: int,
    *,
    llm_config,
    stop_check=None,
) -> ComponentMappingResult:
    """Map one frozen campaign source member using a bounded tool-use session."""
    try:
        _campaign, member, component, snapshot, run = _load_component_context(
            campaign_id, member_id
        )
    except Exception as exc:
        events_svc.emit(
            campaign_id,
            {
                "type": "agent_status",
                "agent_id": f"component-mapper-{member_id}",
                "role": "Component Mapper",
                "status": "failed",
                "current_task": "Loading component snapshot",
                "outcome": str(exc),
                "_persist": True,
            },
        )
        raise
    archive_path = Path(snapshot.stored_path)
    if not archive_path.is_file():
        error = ComponentMappingError(f"Source snapshot is missing: {archive_path}")
        events_svc.emit(
            campaign_id,
            {
                "type": "agent_status",
                "agent_id": f"component-mapper-{member_id}",
                "role": "Component Mapper",
                "status": "failed",
                "current_task": "Loading component snapshot",
                "outcome": str(error),
                "_persist": True,
            },
        )
        raise error
    with Session(get_engine()) as session:
        mapper_config = settings_svc.get_component_mapper_config(session)
        eligible_leads = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "sast")
            .where(ScanLead.producer_run_id == run.id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .where(ScanLead.reportable == True)  # noqa: E712
            .order_by(ScanLead.id)
            .limit(200)
        ).all()
    lead_context = [
        {
            "lead_id": lead.id,
            "title": lead.title,
            "location": lead.location,
            "fingerprint": lead.fingerprint,
            "source": lead.source,
        }
        for lead in eligible_leads
    ]
    eligible_lead_ids = {lead.id for lead in eligible_leads if lead.id is not None}

    workdir = (
        Path(get_settings().data_dir)
        / "campaign_correlation"
        / str(campaign_id)
        / str(member_id)
    )
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True, exist_ok=True)
    root = workdir.resolve()
    read_ranges: dict[str, list[tuple[int, int]]] = {}
    facts: list[dict] = []
    rejected = 0
    tool_calls = 0
    read_files: set[str] = set()
    source_bytes = 0
    budget_reason: str | None = None
    source_budget_reason: str | None = None

    events_svc.emit(
        campaign_id,
        {
            "type": "agent_status",
            "agent_id": f"component-mapper-{member_id}",
            "role": "Component Mapper",
            "status": "active",
            "current_task": f"Mapping interfaces for {component.name}",
            "outcome": None,
            "_persist": True,
        },
    )
    try:
        try:
            safe_unzip(str(archive_path), str(workdir))
        except Exception as exc:
            raise ComponentMappingError(
                f"Source snapshot could not be extracted: {exc}"
            ) from exc

        async def executor(tool_name: str, tool_input: dict, _step: int) -> str:
            nonlocal rejected, tool_calls, source_bytes
            nonlocal budget_reason, source_budget_reason
            tool_desc = _format_tool_desc(tool_name, tool_input)
            events_svc.emit(
                campaign_id,
                {
                    "type": "agent_status",
                    "agent_id": f"component-mapper-{member_id}",
                    "role": "Component Mapper",
                    "status": "active",
                    "current_task": f"[{component.name}] Turn {_step + 1}: {tool_desc}",
                    "outcome": None,
                    "_persist": True,
                },
            )
            events_svc.emit(
                campaign_id,
                {
                    "type": "scanner_phase",
                    "phase": "component_mapping",
                    "status": "running",
                    "message": f"[{component.name}] Turn {_step + 1}: {tool_desc}",
                    "data": {
                        "component_id": component.id,
                        "component_name": component.name,
                        "step": _step + 1,
                        "tool": tool_name,
                    },
                },
            )
            if tool_calls >= mapper_config.max_tool_calls:
                budget_reason = (
                    "Interface mapping tool-call budget exhausted "
                    f"({mapper_config.max_tool_calls} calls)."
                )
                return f"{budget_reason} Record no more facts; mapping will stop."
            tool_calls += 1
            if stop_check and stop_check():
                return "Mapping stopped by campaign."
            if tool_name == "list_files":
                return list_files(
                    root,
                    str(tool_input.get("path") or ""),
                    int(tool_input.get("max_depth", 3)),
                )
            if tool_name == "glob":
                return glob_files(root, str(tool_input.get("pattern") or ""))
            if tool_name == "read_file":
                path = str(tool_input.get("path") or "")
                parsed = _parse_location(f"{path}:1")
                normalized_path = parsed[0] if parsed else None
                if (
                    normalized_path
                    and normalized_path not in read_files
                    and len(read_files) >= mapper_config.max_source_files
                ):
                    source_budget_reason = (
                        "Source file budget exhausted "
                        f"({mapper_config.max_source_files} files)."
                    )
                    return (
                        f"Error: {source_budget_reason} "
                        "Record facts from files already read or call done."
                    )
                start = tool_input.get("start_line")
                end = tool_input.get("end_line")
                result = read_file(root, path, start, end)
                if not result.startswith("Error:"):
                    result_bytes = len(result.encode("utf-8", errors="replace"))
                    if source_bytes + result_bytes > mapper_config.max_source_bytes:
                        source_budget_reason = (
                            "Source byte budget exhausted "
                            f"({mapper_config.max_source_bytes:,} bytes)."
                        )
                        return (
                            f"Error: {source_budget_reason} "
                            "Record facts from files already read or call done."
                        )
                    source_bytes += result_bytes
                    if normalized_path:
                        read_files.add(normalized_path)
                    _record_read_range(root, read_ranges, path, start, end, result)
                return result
            if tool_name == "grep":
                result = grep(
                    root,
                    str(tool_input.get("pattern") or ""),
                    path=str(tool_input.get("path") or ""),
                    include_pattern=str(tool_input.get("include_pattern") or ""),
                )
                if not result.startswith("(") and not result.startswith("Error:"):
                    result_bytes = len(result.encode("utf-8", errors="replace"))
                    if source_bytes + result_bytes > mapper_config.max_source_bytes:
                        source_budget_reason = (
                            "Source byte budget exhausted "
                            f"({mapper_config.max_source_bytes:,} bytes)."
                        )
                        return (
                            f"Error: {source_budget_reason} "
                            "Record facts from files already read or call done."
                        )
                    matched_paths = {
                        match.group(1).replace("\\", "/")
                        for line in result.splitlines()
                        if (match := re.match(r"^(.+):([0-9]+):", line))
                    }
                    new_paths = matched_paths - read_files
                    if (
                        len(read_files) + len(new_paths)
                        > mapper_config.max_source_files
                    ):
                        source_budget_reason = (
                            "Source file budget exhausted "
                            f"({mapper_config.max_source_files} files)."
                        )
                        return (
                            f"Error: {source_budget_reason} "
                            "Record facts from files already read or call done."
                        )
                    source_bytes += result_bytes
                    read_files.update(matched_paths)
                    for line in result.splitlines():
                        match = re.match(r"^(.+):([0-9]+):", line)
                        if match:
                            _record_read_range(
                                root,
                                read_ranges,
                                match.group(1),
                                int(match.group(2)),
                                int(match.group(2)),
                                line,
                            )
                return result
            if tool_name == "record_interface_fact":
                if len(facts) >= mapper_config.max_facts:
                    budget_reason = (
                        "Interface mapping fact budget exhausted "
                        f"({mapper_config.max_facts} facts)."
                    )
                    return f"{budget_reason} Record no more facts; mapping will stop."
                try:
                    facts.append(
                        _validate_fact(
                            root,
                            tool_input,
                            read_ranges,
                            eligible_lead_ids,
                        )
                    )
                except (TypeError, ValueError, OSError) as exc:
                    rejected += 1
                    return f"Error: rejected interface fact: {exc}"
                return (
                    f"Interface fact accepted ({len(facts)}/{mapper_config.max_facts})."
                )
            if tool_name == "done":
                return str(tool_input.get("summary") or "")
            return f"Error: unsupported mapper tool {tool_name!r}"

        llm_svc.set_run_context(
            campaign_id,
            lambda evt: events_svc.emit(campaign_id, evt),
            run_kind="campaign",
        )

        summary = await llm_svc.thinking_agentic_loop(
            llm_config,
            system_message=COMPONENT_MAPPER_SYSTEM_PROMPT,
            initial_user_message=(
                f"Map the external interfaces of component {component.name!r}. "
                "Begin by listing the repository and reading its manifests/configuration. "
                "The following validated SAST leads are immutable candidates for "
                "lead_anchor facts; connect only when source evidence proves reachability:\n"
                + json.dumps(lead_context, separators=(",", ":"))
            ),
            tool_executor=executor,
            stop_check=stop_check,
            tools=COMPONENT_MAPPER_TOOLS,
            max_context_chars=120_000,
            termination_check=lambda: budget_reason,
            text_only_repair_message=(
                "Your previous response did not call a tool. Continue by calling "
                "exactly one mapper tool: list_files, glob, read_file, grep, "
                "record_interface_fact, or done."
            ),
        )
        if stop_check and stop_check():
            raise asyncio.CancelledError
        if budget_reason and not summary:
            summary = budget_reason
        recorded = _persist_facts(
            sast_run_id=run.id,
            component_id=component.id,
            facts=facts,
        )
        events_svc.emit(
            campaign_id,
            {
                "type": "agent_status",
                "agent_id": f"component-mapper-{member_id}",
                "role": "Component Mapper",
                "status": "complete",
                "current_task": f"Mapped interfaces for {component.name}",
                "outcome": (
                    f"{recorded} fact(s), {rejected} rejected"
                    + (f"; {budget_reason}" if budget_reason else "")
                    + (f"; {source_budget_reason}" if source_budget_reason else "")
                ),
                "_persist": True,
            },
        )
        return ComponentMappingResult(
            component_id=component.id,
            sast_run_id=run.id,
            facts_recorded=recorded,
            facts_rejected=rejected,
            tool_calls=tool_calls,
            summary=summary,
        )
    except asyncio.CancelledError:
        raise
    except ComponentMappingError as exc:
        events_svc.emit(
            campaign_id,
            {
                "type": "agent_status",
                "agent_id": f"component-mapper-{member_id}",
                "role": "Component Mapper",
                "status": "failed",
                "current_task": f"Mapping interfaces for {component.name}",
                "outcome": str(exc),
                "_persist": True,
            },
        )
        raise
    except Exception as exc:
        events_svc.emit(
            campaign_id,
            {
                "type": "agent_status",
                "agent_id": f"component-mapper-{member_id}",
                "role": "Component Mapper",
                "status": "failed",
                "current_task": f"Mapping interfaces for {component.name}",
                "outcome": str(exc),
                "_persist": True,
            },
        )
        raise CorrelationTransientError(
            f"Component interface mapping failed for {component.name}: {exc}"
        ) from exc
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
