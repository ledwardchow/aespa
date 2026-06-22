"""Slice 4: LLM-driven readiness assessment for API collections.

``assess_readiness(session, collection_id)`` loads the collection's endpoints,
credentials, and parsed security-scheme data, then asks the active LLM to
produce a structured gap analysis.  Results are persisted to
``ApiCollection.readiness_json`` and the three ``prereq_*`` fields on each
``ApiEndpoint``.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from sqlmodel import Session, select

from aespa.models import ApiCollection, ApiCredential, ApiEndpoint

# How many endpoints to include verbatim in the LLM prompt.
# Endpoints beyond this cap receive the overall assessment's auth/data gaps.
_MAX_ENDPOINTS_IN_PROMPT = 60


class ReadinessError(Exception):
    """Raised when the assessment cannot proceed (no LLM config, etc.)."""


# ── Public API ────────────────────────────────────────────────────────────────


async def assess_readiness(session: Session, collection_id: int) -> dict:
    """Run the LLM-driven readiness assessment and persist results.

    Returns the full readiness dict so the router can return it directly.
    """
    collection = session.get(ApiCollection, collection_id)
    if collection is None:
        raise ReadinessError(f"API collection {collection_id} not found")

    endpoints = session.exec(
        select(ApiEndpoint).where(ApiEndpoint.collection_id == collection_id)
    ).all()

    credentials = session.exec(
        select(ApiCredential).where(ApiCredential.collection_id == collection_id)
    ).all()

    # Security schemes — prefer the dedicated field set by the OpenAPI parser;
    # fall back to checking col.servers for data written by older code versions.
    security_schemes: dict = {}
    if collection.auth_summary_json:
        try:
            security_schemes = json.loads(collection.auth_summary_json).get(
                "securitySchemes", {}
            )
        except Exception:
            pass
    if not security_schemes and collection.servers:
        try:
            servers_data = json.loads(collection.servers)
            if isinstance(servers_data, dict):
                security_schemes = servers_data.get("securitySchemes", {})
        except Exception:
            pass

    # Credential summary (scheme + label + auth_endpoint only — never expose values)
    cred_summary = [
        {
            "scheme": c.scheme,
            "name": c.name,
            "label": c.label or c.name,
            **(({"auth_endpoint": c.auth_endpoint}) if c.auth_endpoint else {}),
        }
        for c in credentials
    ]

    # Endpoint summaries for the prompt
    ep_for_prompt = [_ep_summary(ep) for ep in endpoints[:_MAX_ENDPOINTS_IN_PROMPT]]

    try:
        from aespa.services import llm as llm_svc
        from aespa.services.settings import get_llm_config
    except ImportError as exc:
        raise ReadinessError("LLM services not available") from exc

    llm_cfg = get_llm_config(session)
    if llm_cfg is None:
        raise ReadinessError(
            "No active LLM config — configure an LLM profile in Settings first"
        )

    prompt = _build_prompt(
        collection=collection,
        endpoints=ep_for_prompt,
        credentials=cred_summary,
        security_schemes=security_schemes,
        total_endpoints=len(endpoints),
    )

    try:
        raw = await llm_svc.plain_completion(llm_cfg, prompt)
    except Exception as exc:
        raise ReadinessError(f"LLM call failed: {exc}") from exc

    result = _parse_llm_result(raw, endpoints, collection_id)

    # ── Persist ───────────────────────────────────────────────────────────────
    collection.readiness_json = json.dumps(result)
    session.add(collection)

    # Apply per-endpoint results; fall back to the overall assessment for
    # endpoints that were beyond the prompt cap.
    overall = result.get("overall", {})
    overall_can_test_auth = overall.get("has_credentials", True)

    ep_results_by_id: dict[int, dict] = {
        r["endpoint_id"]: r for r in result.get("endpoints", []) if "endpoint_id" in r
    }

    for ep in endpoints:
        ep_result = ep_results_by_id.get(ep.id)
        if ep_result:
            ep.prereq_can_test = ep_result.get("can_test", True)
            ep.prereq_can_test_auth = ep_result.get("can_test_auth", True)
            ep.prereq_notes = json.dumps(ep_result.get("notes", []))
        else:
            # Not included in the prompt — apply overall auth gap
            ep.prereq_can_test = True
            ep.prereq_can_test_auth = (not ep.auth_required) or overall_can_test_auth
            ep.prereq_notes = json.dumps(
                [] if ep.prereq_can_test_auth else ["No credentials for required auth"]
            )
        session.add(ep)

    session.commit()
    return result


def get_readiness(session: Session, collection_id: int) -> dict | None:
    """Return the stored readiness result, or None if not yet assessed."""
    collection = session.get(ApiCollection, collection_id)
    if collection is None or not collection.readiness_json:
        return None
    try:
        return json.loads(collection.readiness_json)
    except Exception:
        return None


# ── Internals ─────────────────────────────────────────────────────────────────


def _ep_summary(ep: ApiEndpoint) -> dict:
    params = json.loads(ep.parameters_json or "[]")
    sample = json.loads(ep.sample_request_json or "{}")
    body_schema = json.loads(ep.request_body_schema_json or "{}")
    security = json.loads(ep.security_json or "[]")
    tags = json.loads(ep.tags_json or "[]")
    return {
        "id": ep.id,
        "method": ep.method,
        "path": ep.path,
        "auth_required": ep.auth_required,
        "security_requirements": security,
        "has_parameters": len(params) > 0,
        "has_sample_request": bool(sample),
        "has_request_body_schema": bool(body_schema),
        "tags": tags,
        "summary": ep.summary,
    }


def _build_prompt(
    collection: ApiCollection,
    endpoints: list[dict],
    credentials: list[dict],
    security_schemes: dict,
    total_endpoints: int,
) -> str:
    shown = len(endpoints)
    extra_note = (
        f" (showing first {shown} of {total_endpoints}; assess the rest at the overall level)"
        if total_endpoints > shown
        else ""
    )

    schemes_str = json.dumps(security_schemes, indent=2) if security_schemes else "(none found)"
    creds_str = json.dumps(credentials, indent=2) if credentials else "(none)"
    eps_str = json.dumps(endpoints, indent=2) if endpoints else "(none)"

    return f"""You are a security pentester preparing to test a REST API. Your task is to assess
whether you have enough information and credentials to perform a thorough security test.

API Collection: {collection.name}
Base URL: {collection.base_url}

Security Schemes from specification:
{schemes_str}

Available credentials ({len(credentials)} total — values redacted):
{creds_str}

Credential scheme legend:
- bearer   : a pre-obtained bearer token; can be used directly as Authorization: Bearer <value>
- apikey   : a static API key for a header or query param
- basic    : HTTP Basic Authentication (Authorization: Basic <base64(user:pass)>)
- cookie   : a session cookie value
- header   : a custom header value
- login    : email/password (or username/password) that must first be POSTed to the
             auth_endpoint to OBTAIN a bearer token (JWT or session). These are NOT
             directly usable as auth headers — they represent test accounts whose JWTs
             can be obtained on demand. They are valuable for BOLA/IDOR testing (multiple
             distinct identities) but require a login step first.

Endpoints to assess ({total_endpoints} total{extra_note}):
{eps_str}

For EACH endpoint listed above, determine:
- can_test: true if there is enough information to send a meaningful security probe
  (e.g. method + path are known, no missing required parameters without any sample value)
- can_test_auth: true if we have the right credentials for this endpoint’s auth requirements.
  For endpoints that require a bearer token:
  • can_test_auth is true if there is at least one bearer credential directly, OR
  • at least one login credential (we can obtain a JWT on demand via the auth_endpoint)
  For unauthenticated endpoints: can_test_auth is always true.
- notes: a list of specific gaps

Also produce an overall assessment for the entire collection.

Important guidance on login-flow auth:
- If there are login credentials (scheme="login"), the tooling CAN obtain a JWT for each
  test account by POSTing to the auth_endpoint. Consider this as having bearer auth available.
- Count distinct login accounts as distinct test identities, which enables BOLA/IDOR testing.
- If the spec defines bearer auth and we have login credentials that produce JWTs, treat
  has_credentials as true.

Reply with ONLY this JSON object — no preamble, no markdown fences:
{{
  "overall": {{
    "ready_to_test": true,
    "score": 72,
    "summary": "One-line summary of readiness",
    "auth_method_understood": true,
    "has_credentials": false,
    "has_sufficient_test_data": true,
    "blocking_gaps": ["No bearer token provided for endpoints requiring BearerAuth"],
    "recommendations": ["Upload a credentials file containing a bearer token"]
  }},
  "endpoints": [
    {{
      "endpoint_id": <integer id from the endpoint list>,
      "can_test": true,
      "can_test_auth": false,
      "notes": ["No bearer token available for required BearerAuth"]
    }}
  ]
}}

Rules:
- Include ALL endpoints from the list above in the "endpoints" array.
- "score" is an integer 0–100 (100 = fully ready, 0 = cannot test at all).
- "blocking_gaps" are issues that prevent ANY meaningful testing.
- "recommendations" are actionable steps to improve readiness.
- Keep notes concise (one short sentence each).
- If there are no credentials at all and the spec requires auth, that is a blocking gap.
- If all endpoints are unauthenticated and we have enough param/sample info, score can be 90+.

JSON (ONLY the object, nothing else):"""


def _parse_llm_result(raw: str, endpoints: list, collection_id: int) -> dict:
    """Parse the LLM response into a validated readiness dict."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not m:
        raise ReadinessError(
            f"LLM did not return a JSON object. Response: {raw[:300]}"
        )
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise ReadinessError(
            f"Could not parse LLM JSON: {exc}. Snippet: {m.group(0)[:300]}"
        ) from exc

    # Validate / normalise overall block
    overall = data.get("overall", {})
    if not isinstance(overall, dict):
        overall = {}
    overall.setdefault("ready_to_test", False)
    overall.setdefault("score", 0)
    overall.setdefault("summary", "Assessment complete")
    overall.setdefault("auth_method_understood", False)
    overall.setdefault("has_credentials", False)
    overall.setdefault("has_sufficient_test_data", False)
    overall.setdefault("blocking_gaps", [])
    overall.setdefault("recommendations", [])
    data["overall"] = overall

    # Validate / normalise per-endpoint blocks
    known_ids = {ep.id for ep in endpoints}
    ep_list = []
    for item in data.get("endpoints") or []:
        if not isinstance(item, dict):
            continue
        eid = item.get("endpoint_id")
        if eid not in known_ids:
            continue
        ep_list.append({
            "endpoint_id": eid,
            "can_test": bool(item.get("can_test", True)),
            "can_test_auth": bool(item.get("can_test_auth", True)),
            "notes": [str(n) for n in (item.get("notes") or [])],
        })
    data["endpoints"] = ep_list
    data["collection_id"] = collection_id
    data["assessed_at"] = datetime.now(timezone.utc).isoformat()
    return data
