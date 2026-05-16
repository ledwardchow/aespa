"""Burp Suite REST API client for targeted active scanning.

Burp Suite Professional exposes a REST API (default: http://127.0.0.1:1337)
that allows external tools to launch active scans against specific endpoints
and retrieve the resulting issues.

Workflow
--------
1. ``launch_active_scan(url, ...)`` — POST /v0.1/scan → returns a numeric task_id.
2. ``wait_for_scan(task_id, ...)`` — polls GET /v0.1/scan/{task_id} with
   exponential back-off until status is "succeeded" or "failed" (or timeout).
3. ``get_scan_issues(task_id)`` — extracts normalised issue dicts from
   the ``issue_events`` in the scan response.

Reference: https://portswigger.net/burp/documentation/desktop/getting-started/rest-api
"""
from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

import httpx

from aespa.schemas import BurpRestApiConfigOut

log = logging.getLogger("aespa.burp_rest")

# Terminal scan statuses (Burp REST API v0.1)
_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}
# Statuses that mean the scan completed successfully enough to read issues
_SUCCESS_STATUSES = {"succeeded"}

# Polling schedule: [(up_to_elapsed_s, interval_s), ...]
_POLL_SCHEDULE = [
    (60,  5),    # first minute: every 5 s
    (180, 15),   # minutes 1-3: every 15 s
    (600, 30),   # minutes 3-10: every 30 s
]
_DEFAULT_TIMEOUT_S = 600.0  # 10 minutes


class BurpRestApiError(RuntimeError):
    pass


def _headers(config: BurpRestApiConfigOut) -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    if config.api_key:
        h["Authorization"] = f"Bearer {config.api_key}"
    return h


def _poll_interval(elapsed_s: float) -> float:
    for threshold, interval in _POLL_SCHEDULE:
        if elapsed_s < threshold:
            return interval
    return _POLL_SCHEDULE[-1][1]


def _build_scan_body(
    url: str,
    *,
    cookies: dict[str, str] | None,
    extra_headers: dict[str, str] | None,
    application_logins: list[dict] | None,
) -> dict:
    """Build the POST /v0.1/scan request body."""
    parsed = urlparse(url)
    # Tight scope: restrict scan to the exact URL path prefix so Burp doesn't
    # crawl the entire site.
    scope_rule = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    body: dict = {
        "urls": [url],
        "scope": {
            "advanced_mode": True,
            "include": [{"rule": scope_rule, "enabled": True}],
            "exclude": [],
        },
        "scan_configurations": [
            {
                "name": "Audit checks - all insertion points",
                "type": "NamedConfiguration",
            }
        ],
    }

    # Build custom headers for session-based auth (cookies + bearer tokens).
    custom_headers: list[dict] = []
    if extra_headers:
        for name, value in extra_headers.items():
            if name.lower() in {"content-length", "transfer-encoding"}:
                continue
            custom_headers.append({"name": name, "value": value})
    if cookies:
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        # Merge with existing Cookie header if present
        existing_cookie = next(
            (h for h in custom_headers if h["name"].lower() == "cookie"),
            None,
        )
        if existing_cookie:
            existing_cookie["value"] += f"; {cookie_str}"
        else:
            custom_headers.append({"name": "Cookie", "value": cookie_str})

    if custom_headers:
        body["crawl_configuration"] = {"custom_headers": custom_headers}

    if application_logins:
        body["application_logins"] = application_logins[:5]  # Burp limit

    return body


def _normalise_issue(event: dict) -> dict | None:
    """Convert a Burp issue_event dict into a normalised finding dict."""
    if not isinstance(event, dict):
        return None
    if event.get("type") != "issue_found":
        return None
    issue = event.get("issue")
    if not isinstance(issue, dict):
        return None

    name = str(issue.get("name") or "")
    severity = str(issue.get("severity") or "info").lower()
    confidence = str(issue.get("confidence") or "tentative").lower()
    origin = str(issue.get("origin") or "")
    path = str(issue.get("path") or "/")
    affected_url = f"{origin}{path}" if origin else path
    description = str(issue.get("issue_background") or issue.get("description") or "")
    remediation = str(issue.get("remediation_background") or issue.get("remediation") or "")

    # Extract request/response evidence if available
    request_evidence = ""
    response_evidence = ""
    rr = issue.get("request_response") or {}
    if isinstance(rr, dict):
        request_evidence = str(rr.get("request") or "")[:4096]
        response_evidence = str(rr.get("response") or "")[:4096]
    elif isinstance(issue.get("request_responses"), list):
        for rr_item in issue["request_responses"][:1]:
            if isinstance(rr_item, dict):
                request_evidence = str(rr_item.get("request") or "")[:4096]
                response_evidence = str(rr_item.get("response") or "")[:4096]
                break

    return {
        "source": "burp_active_scan",
        "name": name,
        "severity": severity,
        "confidence": confidence,
        "affected_url": affected_url,
        "description": description,
        "remediation": remediation,
        "request_evidence": request_evidence,
        "response_evidence": response_evidence,
    }


async def launch_active_scan(
    config: BurpRestApiConfigOut,
    url: str,
    *,
    cookies: dict[str, str] | None = None,
    extra_headers: dict[str, str] | None = None,
    application_logins: list[dict] | None = None,
) -> int:
    """Submit a new active scan to Burp Suite.  Returns the integer task_id."""
    body = _build_scan_body(
        url,
        cookies=cookies,
        extra_headers=extra_headers,
        application_logins=application_logins,
    )
    endpoint = f"{config.api_url}/v0.1/scan"
    log.info("burp_rest: launching active scan url=%s endpoint=%s", url, endpoint)
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        resp = await client.post(endpoint, json=body, headers=_headers(config))
        if resp.status_code not in {200, 201}:
            raise BurpRestApiError(
                f"Burp REST API error {resp.status_code} launching scan: {resp.text[:500]}"
            )
        data = resp.json()

    task_id = data.get("task_id") or data.get("id")
    if task_id is None:
        raise BurpRestApiError(
            f"Burp REST API did not return a task_id; response: {str(data)[:300]}"
        )
    log.info("burp_rest: scan launched task_id=%s url=%s", task_id, url)
    return int(task_id)


async def get_scan_status(config: BurpRestApiConfigOut, task_id: int) -> dict:
    """Fetch the current scan state from Burp Suite.

    Returns the full response dict which includes ``status`` and
    ``issue_events``.
    """
    endpoint = f"{config.api_url}/v0.1/scan/{task_id}"
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        resp = await client.get(endpoint, headers=_headers(config))
        if resp.status_code == 404:
            raise BurpRestApiError(f"Burp REST API: scan task {task_id} not found")
        resp.raise_for_status()
        return resp.json()


async def wait_for_scan(
    config: BurpRestApiConfigOut,
    task_id: int,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> list[dict]:
    """Poll until the scan finishes, then return normalised issue dicts.

    Raises ``BurpRestApiError`` on timeout or if the scan fails with no issues.
    """
    start = asyncio.get_event_loop().time()
    while True:
        elapsed = asyncio.get_event_loop().time() - start
        if elapsed >= timeout_s:
            raise BurpRestApiError(
                f"Burp active scan task {task_id} timed out after {timeout_s:.0f}s"
            )

        try:
            data = await get_scan_status(config, task_id)
        except BurpRestApiError:
            raise
        except Exception as exc:
            raise BurpRestApiError(f"Error polling Burp scan task {task_id}: {exc}") from exc

        status = str(data.get("status") or "").lower()
        log.debug("burp_rest: task_id=%s status=%s elapsed=%.0fs", task_id, status, elapsed)

        if status in _TERMINAL_STATUSES:
            issues = [
                n for e in (data.get("issue_events") or [])
                if (n := _normalise_issue(e)) is not None
            ]
            log.info(
                "burp_rest: task_id=%s finished status=%s issues=%d",
                task_id, status, len(issues),
            )
            return issues

        interval = _poll_interval(elapsed)
        await asyncio.sleep(interval)
