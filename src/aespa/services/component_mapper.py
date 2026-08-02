"""Bounded LLM extraction of language-agnostic component interface facts."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session, select

from aespa.config import get_settings
from aespa.db import get_engine
from aespa.models import (
    ApplicationComponent,
    AssessmentCampaign,
    CampaignSourceMember,
    ComponentFact,
    ComponentSnapshot,
    SastRun,
)
from aespa.services import events as events_svc
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

_FACT_TYPES = {
    "route",
    "http_call",
    "queue_publish",
    "queue_consume",
    "rpc_client",
    "rpc_server",
}
_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
_MAX_TOOL_CALLS = 40
_MAX_FACTS = 200
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
    }
    if fact_type in {"route", "http_call"} and not result["path"]:
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
            nonlocal rejected, tool_calls
            tool_calls += 1
            if tool_calls > _MAX_TOOL_CALLS:
                raise CorrelationTransientError(
                    "Interface mapping tool-call budget exhausted."
                )
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
                start = tool_input.get("start_line")
                end = tool_input.get("end_line")
                result = read_file(root, path, start, end)
                if not result.startswith("Error:"):
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
                if len(facts) >= _MAX_FACTS:
                    raise CorrelationTransientError(
                        "Interface mapping fact budget exhausted."
                    )
                try:
                    facts.append(_validate_fact(root, tool_input, read_ranges))
                except (TypeError, ValueError, OSError) as exc:
                    rejected += 1
                    return f"Error: rejected interface fact: {exc}"
                return f"Interface fact accepted ({len(facts)}/{_MAX_FACTS})."
            if tool_name == "done":
                return str(tool_input.get("summary") or "")
            return f"Error: unsupported mapper tool {tool_name!r}"

        from aespa.services import llm as llm_svc

        summary = await llm_svc.thinking_agentic_loop(
            llm_config,
            system_message=COMPONENT_MAPPER_SYSTEM_PROMPT,
            initial_user_message=(
                f"Map the external interfaces of component {component.name!r}. "
                "Begin by listing the repository and reading its manifests/configuration."
            ),
            tool_executor=executor,
            stop_check=stop_check,
            tools=COMPONENT_MAPPER_TOOLS,
            max_context_chars=120_000,
            text_only_repair_message=(
                "Your previous response did not call a tool. Continue by calling "
                "exactly one mapper tool: list_files, glob, read_file, grep, "
                "record_interface_fact, or done."
            ),
        )
        if stop_check and stop_check():
            raise asyncio.CancelledError
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
                "outcome": f"{recorded} fact(s), {rejected} rejected",
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
