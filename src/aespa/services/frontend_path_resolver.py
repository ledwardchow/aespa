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

    # A legacy frontend_entrypoint is usable as a request only when its shape
    # proves it came from UI code.  Cross-component paths historically stored a
    # server egress here, so a bare method/path must never be searched in
    # browser traffic.
    frontend = value.get("frontend_entrypoint")
    if isinstance(frontend, dict):
        role = str(frontend.get("request_role") or "").strip().casefold()
        if role in {"browser_request", "browser", "frontend"} or frontend.get(
            "frontend"
        ) or frontend.get("ui_route") or frontend.get("trigger"):
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
        (
            approved_part.startswith("{")
            and approved_part.endswith("}")
        )
        or approved_part.startswith(":")
        or approved_part == observed_part
        for approved_part, observed_part in zip(approved_parts, observed_parts)
    )


def _is_v3(path: dict) -> bool:
    return path.get("schema_version") == 3 and isinstance(
        path.get("frontend_surface"), dict
    )


def _surface_value(path: dict, key: str) -> dict:
    surface = path.get("frontend_surface")
    if isinstance(surface, dict) and isinstance(surface.get(key), dict):
        return surface[key]
    return {}


def candidate_pages(approved_path: dict, live_context: dict) -> list[dict]:
    """Return pages compatible with the UI route/state in a static path."""
    expected = _surface_value(approved_path, "ui_route")
    expected_route = _route(
        str(expected.get("path") or expected.get("route") or _approved_entry(approved_path))
    )
    state_key = str(expected.get("state_key") or "").strip().casefold()
    pages = [item for item in live_context.get("pages", []) if isinstance(item, dict)]
    result = []
    for page in pages:
        route = _route(str(page.get("route") or page.get("url") or ""))
        if expected_route and not _route_matches(route, expected_route):
            continue
        if state_key and state_key not in str(
            page.get("state_key") or page.get("state_label") or ""
        ).casefold():
            continue
        result.append(page)
    return result


def candidate_actions(
    approved_path: dict,
    live_context: dict,
    pages: list[dict] | None = None,
) -> list[dict]:
    """Return actions on candidate pages matching the reviewed UI action."""
    expected = _surface_value(approved_path, "ui_action")
    legacy = approved_path.get("frontend_entrypoint")
    if not expected and isinstance(legacy, dict):
        expected = legacy
    expected_detail = expected.get("detail") if isinstance(expected.get("detail"), dict) else {}
    label = str(
        expected.get("label") or expected.get("action") or expected_detail.get("label") or ""
    ).strip().casefold()
    kind = str(
        expected.get("action_kind")
        or expected.get("trigger")
        or expected_detail.get("action_kind")
        or expected_detail.get("trigger")
        or ""
    ).strip().casefold()
    interaction_id = str(expected.get("interaction_id") or "").strip()
    if not label and not kind and not interaction_id and _is_v3(approved_path):
        return []
    page_ids = {page.get("id") for page in pages or []}
    actions = [item for item in live_context.get("actions", []) if isinstance(item, dict)]
    result = []
    for action in actions:
        if page_ids and action.get("page_id") not in page_ids:
            continue
        observed_label = str(action.get("label") or "").strip().casefold()
        observed_kind = str(action.get("action_kind") or "").strip().casefold()
        if label and label != observed_label and label not in observed_label:
            continue
        if kind and kind != observed_kind:
            continue
        if interaction_id and str(action.get("interaction_id") or "").strip() != interaction_id:
            continue
        result.append(action)
    return result


def candidate_requests(
    approved_path: dict,
    live_context: dict,
    pages: list[dict] | None = None,
    actions: list[dict] | None = None,
) -> list[dict]:
    """Return browser traffic candidates using only the browser request hop."""
    expected = _surface_value(approved_path, "browser_request")
    method = str(expected.get("method") or "").upper()
    request_path = _route(str(expected.get("path") or expected.get("url") or ""))
    expected_session = str(expected.get("session_label") or "").strip()
    if not expected:
        method, request_path = _request_method_path(approved_path)
    if not method and not request_path:
        return []
    expected_detail = expected.get("detail") if isinstance(expected.get("detail"), dict) else {}
    fields = (
        expected.get("body_fields")
        or expected.get("query_fields")
        or expected_detail.get("body_fields")
        or expected_detail.get("query_fields")
    )
    if not isinstance(fields, list):
        transition = approved_path.get("request_transition")
        fields = transition.get("mutation_points", []) if isinstance(transition, dict) else []
    if not fields:
        assertion = approved_path.get("validation_assertion")
        fields = assertion.get("mutation_points", []) if isinstance(assertion, dict) else []
    expected_fields = {str(value).strip() for value in fields or [] if str(value).strip()}
    page_ids = {page.get("id") for page in pages or []}
    action_ids = {action.get("id") for action in actions or []}
    interaction_ids = {
        str(action.get("interaction_id") or "").strip()
        for action in actions or []
        if str(action.get("interaction_id") or "").strip()
    }
    requests = [item for item in live_context.get("requests", []) if isinstance(item, dict)]
    result = []
    for request in requests:
        observed_method = str(request.get("method") or "").upper()
        observed_path = _route(str(request.get("url") or request.get("path") or ""))
        if method and observed_method != method:
            continue
        if request_path and not _route_matches(observed_path, request_path):
            continue
        if page_ids and request.get("page_id") not in page_ids:
            continue
        if expected_session and str(request.get("session_label") or "").strip() != expected_session:
            continue
        request_interaction = str(request.get("interaction_id") or "").strip()
        if interaction_ids and request_interaction not in interaction_ids:
            continue
        observed_fields = {
            str(value).strip()
            for value in request.get("fields", [])
            if str(value).strip()
        }
        # When the assertion names request fields, require all of them in the
        # baseline.  A 4xx request missing one field is not proof of a related
        # validation behaviour.
        if expected_fields and not expected_fields.issubset(observed_fields):
            continue
        request = dict(request)
        request["_expected_field_overlap"] = len(expected_fields & observed_fields)
        request["_action_match"] = bool(
            not action_ids or request.get("interaction_id") in interaction_ids
        )
        result.append(request)
    return result


def rank_live_bindings(
    approved_path: dict,
    pages: list[dict],
    actions: list[dict],
    requests: list[dict],
) -> list[dict]:
    """Build and rank page/action/browser-request bindings deterministically."""
    expected_action = _surface_value(approved_path, "ui_action")
    has_action_claim = bool(expected_action)
    if not has_action_claim and isinstance(approved_path.get("frontend_entrypoint"), dict):
        entrypoint = approved_path["frontend_entrypoint"]
        has_action_claim = bool(
            entrypoint.get("action") or entrypoint.get("trigger") or entrypoint.get("interaction_id")
        )
    page_by_id = {page.get("id"): page for page in pages}
    action_candidates = {action.get("id"): action for action in actions}
    bindings: list[dict] = []
    for request in requests:
        page = page_by_id.get(request.get("page_id"))
        page_actions = [
            action
            for action in actions
            if action.get("page_id") == request.get("page_id")
            and (
                not str(request.get("interaction_id") or "").strip()
                or str(action.get("interaction_id") or "").strip()
                == str(request.get("interaction_id") or "").strip()
            )
        ]
        if has_action_claim:
            page_actions = [action for action in page_actions if action.get("id") in action_candidates]
            if not page_actions:
                continue
        elif not page_actions:
            page_actions = [None]
        for action in page_actions:
            interaction_match = bool(
                action
                and str(action.get("interaction_id") or "").strip()
                and str(action.get("interaction_id") or "").strip()
                == str(request.get("interaction_id") or "").strip()
            )
            score = (
                (100 if interaction_match else 0)
                + (20 if page is not None else 0)
                + int(request.get("_expected_field_overlap", 0))
            )
            bindings.append(
                {
                    "page": page,
                    "action": action,
                    "request": request,
                    "score": score,
                }
            )
    return sorted(
        bindings,
        key=lambda item: (
            -item["score"],
            str((item.get("page") or {}).get("id") or ""),
            str((item.get("action") or {}).get("id") or ""),
            str((item.get("request") or {}).get("id") or ""),
        ),
    )


def resolve_frontend_path(approved_path: dict, live_context: dict) -> dict:
    """Return a deterministic status and evidence-backed live binding."""
    path = approved_path or {}
    crawl_status = str(live_context.get("crawl_status") or "unknown")
    if crawl_status in {"failed", "unavailable", "not_started"}:
        return {"status": "crawl_failed", "candidate_count": 0, "candidates": []}
    if _is_v3(path):
        browser = _surface_value(path, "browser_request")
        if not browser.get("method") and not browser.get("path"):
            return {"status": "missing_frontend_hop", "candidate_count": 0, "candidates": []}
    elif not isinstance(path.get("request_transition"), dict) or not (
        path["request_transition"].get("method") or path["request_transition"].get("path")
    ):
        entrypoint = path.get("frontend_entrypoint")
        role = entrypoint.get("request_role") if isinstance(entrypoint, dict) else None
        if role not in {"browser_request", "browser", "frontend"}:
            return {"status": "legacy_unresolved", "candidate_count": 0, "candidates": []}
    pages = candidate_pages(path, live_context)
    if _is_v3(path) and _surface_value(path, "ui_route") and not pages:
        return {"status": "wrong_target", "candidate_count": 0, "candidates": []}
    actions = candidate_actions(path, live_context, pages)
    requests = candidate_requests(path, live_context, pages, actions)
    ranked = rank_live_bindings(path, pages, actions, requests)
    if not ranked:
        if path.get("schema_version") == 3 and path.get("static_trace", {}).get("status") == "complete":
            return {
                "status": "static_complete",
                "candidate_count": 0,
                "candidates": [],
            }
        return {"status": "unavailable", "candidate_count": 0, "candidates": []}
    top_score = ranked[0]["score"]
    top = [binding for binding in ranked if binding["score"] == top_score]
    if len(top) > 1:
        return {
            "status": "ambiguous",
            "candidate_count": len(top),
            "candidates": [
                {
                    "page_id": (item.get("page") or {}).get("id"),
                    "action_id": (item.get("action") or {}).get("id"),
                    "traffic_id": (item.get("request") or {}).get("id"),
                }
                for item in top[:8]
            ],
        }
    binding = top[0]
    return {"status": "resolved", "candidate_count": 1, "binding": binding}


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
    entry = _approved_entry(path)
    resolution = resolve_frontend_path(path, live_context)
    binding = resolution.get("binding")
    page = binding.get("page") if isinstance(binding, dict) else None
    action = binding.get("action") if isinstance(binding, dict) else None
    request = binding.get("request") if isinstance(binding, dict) else None
    resolution_status = str(resolution.get("status") or "unavailable")
    # Keep the old status vocabulary for version 1/2 paths while new paths use
    # the readiness states consumed by campaign validation cases.
    if not _is_v3(path):
        resolution_status = {
            "resolved": "matched",
            "static_complete": "partial",
            "ambiguous": "partial",
            "crawl_failed": "unavailable",
        }.get(resolution_status, resolution_status)

    approved_context = path.get("live_frontend_context")
    if not isinstance(approved_context, dict):
        approved_context = {}
    live = deepcopy(approved_context)
    live["resolution_status"] = resolution_status
    live["crawl_status"] = live_context.get("crawl_status", "unknown")
    live["candidate_count"] = int(resolution.get("candidate_count") or 0)
    if resolution.get("candidates"):
        live["candidates"] = deepcopy(resolution["candidates"][:8])
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
    if _is_v3(path):
        live_binding = {
            "status": resolution_status,
            "candidate_count": int(resolution.get("candidate_count") or 0),
            "evidence_ids": live["evidence_ids"],
        }
        if resolution.get("candidates"):
            live_binding["candidates"] = deepcopy(resolution["candidates"][:8])
        if page is not None:
            live_binding["page_id"] = page.get("id")
        if action is not None:
            live_binding["action_id"] = action.get("id")
        if request is not None:
            live_binding["traffic_id"] = request.get("id")
            live_binding["interaction_id"] = request.get("interaction_id")
            live_binding["session_label"] = request.get("session_label")
            live_binding["observed_request"] = {
                "method": str(request.get("method") or "").upper(),
                "path": _route(str(request.get("url") or request.get("path") or "")),
                "fields": [str(field) for field in request.get("fields", [])[:30]],
            }
        final_live_binding = live_binding
    else:
        final_live_binding = None

    final = deepcopy(path)
    final["schema_version"] = 3 if _is_v3(path) else 2
    final["perspective"] = "frontend"
    final["live_frontend_context"] = live
    if final_live_binding is not None:
        final["live_binding"] = final_live_binding
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
    if resolution_status in {"unavailable", "crawl_failed", "ambiguous", "static_complete"}:
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
        not in {"matched", "resolved"}
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
