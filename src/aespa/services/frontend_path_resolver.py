"""Resolve approved frontend attack paths against one web crawl's evidence."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from urllib.parse import urlparse

from aespa.services import llm as llm_svc

_REWRITE_SYSTEM_PROMPT = """You revise a frontend security-test objective from supplied
evidence only. Return one JSON object with these optional keys:
dynamic_test (string), prerequisites (array of strings), mutation_points (array of
strings), proof_gaps (array of strings), and evidence_ids (array of strings).
Do not add selectors, URLs, routes, request fields, identifiers, or evidence IDs
that are not present in the supplied evidence. If the evidence is insufficient,
leave the relevant field unchanged or add a proof gap."""


def _route(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    path = parsed.path or value.split("?", 1)[0]
    if not path.startswith("/"):
        path = f"/{path}"
    return path.rstrip("/") or "/"


def _request_method_path(value: dict) -> tuple[str, str]:
    for candidate in (value.get("request"), value.get("request_transition")):
        if not isinstance(candidate, dict):
            continue
        method = str(candidate.get("method") or "").upper()
        path = _route(str(candidate.get("path") or candidate.get("url") or ""))
        if method or path:
            return method, path

    # Cross-component paths use the frontend entrypoint itself as the request
    # description.  Older code only understood request_transition, so those
    # paths silently fell back to the first request in the crawl.
    frontend = value.get("frontend_entrypoint")
    if isinstance(frontend, dict):
        return (
            str(frontend.get("method") or "").upper(),
            _route(str(frontend.get("path") or frontend.get("url") or "")),
        )
    return "", ""


def _approved_entry(path: dict) -> str:
    entry = path.get("entry")
    if isinstance(entry, str):
        return _route(entry)
    frontend = path.get("frontend_entrypoint")
    if isinstance(frontend, dict):
        return _route(
            str(
                frontend.get("route")
                or frontend.get("route_template")
                or frontend.get("url")
                or frontend.get("path")
                or ""
            )
        )
    return ""


def is_frontend_path(path: object) -> bool:
    """Return whether a path contains an explicit frontend-rooted trace."""
    if not isinstance(path, dict):
        return False
    if path.get("perspective") == "frontend":
        return True
    if isinstance(path.get("live_frontend_context"), dict):
        return True
    frontend = path.get("frontend_entrypoint")
    if not isinstance(frontend, dict):
        return False
    return any(
        str(frontend.get(key) or "").strip()
        for key in (
            "route",
            "route_template",
            "url",
            "path",
            "method",
            "action",
            "trigger",
        )
    )


def _route_matches(observed: str, approved: str) -> bool:
    """Match literal routes and simple ``{parameter}`` route templates."""
    if observed == approved:
        return True
    approved_parts = approved.strip("/").split("/") if approved != "/" else []
    observed_parts = observed.strip("/").split("/") if observed != "/" else []
    if len(approved_parts) != len(observed_parts):
        return False
    return all(
        approved_part.startswith("{") and approved_part.endswith("}")
        or approved_part == observed_part
        for approved_part, observed_part in zip(approved_parts, observed_parts)
    )


def resolve_approved_path(approved_path: dict, live_context: dict) -> dict:
    """Return a frontend-oriented path using only supplied crawl evidence.

    This resolver is intentionally deterministic.  It never invents a selector,
    URL, request field, or page relationship that is absent from the persisted
    crawl artifacts.
    """

    path = deepcopy(approved_path or {})
    # A normal SAST lead can be imported into a web run without having a
    # frontend-rooted trace.  It must keep its original attack path; attaching
    # arbitrary crawl evidence would make an unrelated page/request appear to
    # be the lead's entrypoint.
    if not is_frontend_path(path):
        return path
    pages = [page for page in live_context.get("pages", []) if isinstance(page, dict)]
    requests = [
        item for item in live_context.get("requests", []) if isinstance(item, dict)
    ]
    actions = [
        item for item in live_context.get("actions", []) if isinstance(item, dict)
    ]
    entry = _approved_entry(path)
    method, request_path = _request_method_path(path)
    entrypoint = path.get("frontend_entrypoint")
    if not isinstance(entrypoint, dict):
        entrypoint = {}
    action_label = (
        str(entrypoint.get("action") or path.get("action") or "").strip().casefold()
    )
    action_kind = (
        str(entrypoint.get("trigger") or path.get("trigger") or "").strip().casefold()
    )
    approved_interaction_id = str(
        entrypoint.get("interaction_id")
        or path.get("interaction_id")
        or ""
    ).strip()

    page = next(
        (
            candidate
            for candidate in pages
            if entry
            and _route_matches(
                _route(str(candidate.get("route") or candidate.get("url") or "")),
                entry,
            )
        ),
        None,
    )
    request = next(
        (
            candidate
            for candidate in requests
            if (not method or str(candidate.get("method") or "").upper() == method)
            and (
                not request_path
                or _route_matches(
                    _route(str(candidate.get("url") or "")), request_path
                )
            )
            and (
                page is None
                or candidate.get("page_id") == page.get("id")
            )
            and (
                not approved_interaction_id
                or candidate.get("interaction_id") == approved_interaction_id
            )
        ),
        None,
    )
    if page is None and request is not None and request.get("page_id") is not None:
        page = next(
            (
                candidate
                for candidate in pages
                if candidate.get("id") == request.get("page_id")
            ),
            None,
        )
    action = None
    if action_label or action_kind or approved_interaction_id:
        action = next(
            (
                candidate
                for candidate in actions
                if (
                    not action_label
                    or action_label
                    in str(
                        candidate.get("label") or candidate.get("action_kind") or ""
                    ).casefold()
                )
                and (
                    not action_kind
                    or action_kind
                    == str(candidate.get("action_kind") or "").casefold()
                )
                and (page is None or candidate.get("page_id") == page.get("id"))
                and (
                    not approved_interaction_id
                    or str(candidate.get("interaction_id") or "").strip()
                    == approved_interaction_id
                )
            ),
            None,
        )

    # If the approved path names an action, it is not enough to find a page and
    # an unrelated request.  The action must exist and, when the crawler has a
    # causal interaction id, the request must carry the same id.
    if (action_label or action_kind or approved_interaction_id) and action is None:
        request = None
    if action is not None and request is not None:
        action_interaction_id = str(action.get("interaction_id") or "").strip()
        request_interaction_id = str(request.get("interaction_id") or "").strip()
        if action_interaction_id and request_interaction_id != action_interaction_id:
            request = None

    if page is None and request is None and action is None:
        resolution_status = "unavailable"
    elif page is None or request is None:
        resolution_status = "partial"
    else:
        resolution_status = "matched"

    approved_context = path.get("live_frontend_context")
    if not isinstance(approved_context, dict):
        approved_context = {}
    live = deepcopy(approved_context)
    live["resolution_status"] = resolution_status
    live["crawl_status"] = live_context.get("crawl_status", "unknown")
    if page is not None:
        live["url"] = page.get("url", "")
        live["route"] = _route(str(page.get("route") or page.get("url") or ""))
        steps = page.get("replay_steps")
        if isinstance(steps, list):
            live["replay_steps"] = steps[:20]
    if request is not None:
        live["request"] = {
            "method": str(request.get("method") or "").upper(),
            "path": _route(str(request.get("url") or "")),
            "evidence_id": f"traffic:{request['id']}"
            if request.get("id") is not None
            else None,
        }
        if request.get("interaction_id"):
            live["request"]["interaction_id"] = request["interaction_id"]
        if request.get("session_label"):
            live["request"]["session_label"] = request["session_label"]
        if isinstance(request.get("fields"), list):
            live["request"]["mutation_points"] = [
                str(field) for field in request["fields"][:30]
            ]
    if action is not None:
        live["action"] = action.get("label") or action.get("action_kind")
        live["trigger"] = action.get("action_kind")
        live["action_evidence_id"] = (
            f"action:{action['id']}" if action.get("id") is not None else None
        )
    live["evidence_ids"] = [
        value
        for value in (
            f"page:{page['id']}"
            if page is not None and page.get("id") is not None
            else None,
            f"traffic:{request['id']}"
            if request is not None and request.get("id") is not None
            else None,
            f"action:{action['id']}"
            if action is not None and action.get("id") is not None
            else None,
        )
        if value
    ]

    final = deepcopy(path)
    final["schema_version"] = 2
    final["perspective"] = "frontend"
    final["live_frontend_context"] = live
    final["approved_pre_crawl_path"] = deepcopy(
        path.get("approved_pre_crawl_path") or path
    )
    final["post_crawl_changes"] = [
        {
            "field": "live_frontend_context",
            "approved_value": approved_context,
            "final_value": live,
            "reason": f"Resolved from {resolution_status} crawl evidence.",
            "evidence_ids": live["evidence_ids"],
        }
    ]
    if resolution_status == "unavailable":
        final["dynamic_test"] = (
            "Use the approved frontend route/action path as guidance; verify the "
            "entry point and request before testing because crawl evidence is unavailable."
        )
    else:
        route = live.get("route") or entry or "the observed frontend route"
        request_label = ""
        if isinstance(live.get("request"), dict):
            request_label = " ".join(
                str(value)
                for value in (
                    live["request"].get("method"),
                    live["request"].get("path"),
                )
                if value
            )
        final["dynamic_test"] = (
            f"From {route}, reproduce the approved frontend action and verify the "
            f"vulnerability at {request_label or 'the observed request'}."
        )
        if isinstance(live.get("request"), dict) and live["request"].get(
            "mutation_points"
        ):
            final["mutation_points"] = live["request"]["mutation_points"]
    return final


def _path_tokens(value: object) -> set[str]:
    """Return URL/path-like tokens that a rewrite is allowed to repeat."""
    text = (
        json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    )
    return {
        token
        for token in re.findall(
            r"(?:https?://[^\s\"']+|/[A-Za-z0-9_{}.:?=&%/-]+)", text
        )
        if token
    }


def _validate_rewrite(
    rewrite: object, *, approved_path: dict, final_path: dict
) -> tuple[dict | None, str | None]:
    if not isinstance(rewrite, dict):
        return None, "Frontend path rewrite was not a JSON object."
    allowed_keys = {
        "dynamic_test",
        "prerequisites",
        "mutation_points",
        "proof_gaps",
        "evidence_ids",
    }
    unknown = set(rewrite) - allowed_keys
    if unknown:
        return None, "Frontend path rewrite returned unsupported fields."
    evidence_ids = rewrite.get("evidence_ids", [])
    if not isinstance(evidence_ids, list) or not all(
        isinstance(item, str) for item in evidence_ids
    ):
        return None, "Frontend path rewrite returned invalid evidence references."
    supplied_ids = {
        str(item)
        for item in (
            approved_path.get("live_frontend_context", {}).get("evidence_ids", [])
            if isinstance(approved_path.get("live_frontend_context"), dict)
            else []
        )
    }
    supplied_ids.update(
        str(item)
        for item in final_path.get("live_frontend_context", {}).get("evidence_ids", [])
        if isinstance(final_path.get("live_frontend_context"), dict)
    )
    if not set(evidence_ids) <= supplied_ids:
        return (
            None,
            "Frontend path rewrite cited evidence outside the supplied allow-list.",
        )
    allowed_tokens = _path_tokens(
        {
            "approved": approved_path,
            "final": final_path,
        }
    )
    result: dict = {"evidence_ids": evidence_ids}
    for key in ("dynamic_test",):
        value = rewrite.get(key)
        if value is not None:
            if not isinstance(value, str) or not value.strip() or len(value) > 2000:
                return None, f"Frontend path rewrite returned invalid {key}."
            result[key] = value.strip()
    for key in ("prerequisites", "mutation_points", "proof_gaps"):
        value = rewrite.get(key)
        if value is None:
            continue
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() and len(item) <= 400
            for item in value
        ):
            return None, f"Frontend path rewrite returned invalid {key}."
        result[key] = [item.strip() for item in value[:20]]
    generated_text = " ".join(
        str(rewrite.get(key) or "")
        for key in ("dynamic_test", "prerequisites", "mutation_points", "proof_gaps")
    )
    for token in _path_tokens(generated_text):
        if token not in allowed_tokens:
            return None, "Frontend path rewrite introduced an unsupported URL or route."
    if not evidence_ids:
        return None, "Frontend path rewrite did not cite supplied crawl evidence."
    return result, None


async def revise_path_with_llm(
    approved_path: dict,
    final_path: dict,
    llm_config,
) -> tuple[dict, str | None]:
    """Rewrite only evidence-bounded frontend wording after crawl resolution."""
    if (
        not is_frontend_path(approved_path)
        or not is_frontend_path(final_path)
        or not llm_config
        or final_path.get("live_frontend_context", {}).get("resolution_status")
        != "matched"
    ):
        return final_path, None
    prompt = (
        "Approved path and deterministic crawl resolution follow as JSON. "
        "Revise only the frontend test wording and cite the supplied evidence IDs.\n\n"
        + json.dumps(
            {"approved_path": approved_path, "resolved_path": final_path},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    try:
        raw = await llm_svc.plain_completion(
            llm_config,
            prompt,
            system_prompt=_REWRITE_SYSTEM_PROMPT,
        )
        decoded = llm_svc.extract_json_response(raw, expect=dict)
        rewrite, error = _validate_rewrite(
            decoded, approved_path=approved_path, final_path=final_path
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        rewrite, error = None, f"Frontend path rewrite returned invalid JSON: {exc}"
    except Exception as exc:
        rewrite, error = None, f"Frontend path rewrite failed: {exc}"
    if rewrite is None:
        return final_path, error
    revised = deepcopy(final_path)
    for key in ("dynamic_test", "prerequisites", "mutation_points", "proof_gaps"):
        if key in rewrite:
            revised[key] = rewrite[key]
    revised.setdefault("post_crawl_changes", []).append(
        {
            "field": "frontend_wording",
            "approved_value": approved_path.get("dynamic_test", ""),
            "final_value": revised.get("dynamic_test", ""),
            "reason": "Campaign LLM revised wording from allow-listed crawl evidence.",
            "evidence_ids": rewrite["evidence_ids"],
        }
    )
    return revised, None
