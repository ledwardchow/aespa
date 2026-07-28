"""Passive WAF / bot-mitigation fingerprinting.

Detects common edge WAF and bot-management products from ordinary response
headers and bodies observed during a scan — no active probing required. Every
signature here was chosen because vendors leak an identifiable marker even on
a blocking (403/406/429) response: a cookie name, a `Server` value, or a
fixed denial-page template.

Used from ``services/traffic.py`` (the single choke point for both httpx and
Playwright traffic) so detection happens passively as a side effect of normal
scanning, then surfaced via ``TestRun.waf_provider`` / the recon summary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_COOKIE_NAME_RE = re.compile(r"^\s*([^=;\s]+)=", re.MULTILINE)


@dataclass(frozen=True)
class WafSignature:
    provider: str  # short vendor/product label surfaced in the UI
    confidence: str  # "high" | "medium"
    cookie_names: tuple[str, ...] = ()
    header_markers: tuple[tuple[str, str], ...] = ()  # (header name, substring)
    body_markers: tuple[str, ...] = ()  # substrings/regex fragments, matched lowercase
    body_regex: re.Pattern | None = None


_SIGNATURES: list[WafSignature] = [
    WafSignature(
        provider="Akamai Bot Manager",
        confidence="high",
        cookie_names=("_abck", "bm_sz", "ak_bmsc"),
        header_markers=(("server", "akamaighost"),),
        body_regex=re.compile(
            r"reference\s*#\d+\.[0-9a-f.]+|errors\.edgesuite\.net|errors\.edgekey\.net",
            re.IGNORECASE,
        ),
    ),
    WafSignature(
        provider="Cloudflare",
        confidence="high",
        cookie_names=("__cf_bm", "cf_clearance"),
        header_markers=(("server", "cloudflare"), ("cf-ray", "")),
        body_markers=("attention required! | cloudflare", "checking your browser before accessing"),
    ),
    WafSignature(
        provider="Imperva / Incapsula",
        confidence="high",
        cookie_names=("incap_ses", "visid_incap"),
        body_markers=("incapsula incident id", "request unsuccessful. incapsula"),
    ),
    WafSignature(
        provider="AWS WAF",
        confidence="medium",
        header_markers=(("x-amzn-waf-action", ""), ("x-amzn-requestid", "")),
        body_markers=("the request could not be satisfied",),
    ),
    WafSignature(
        provider="F5 BIG-IP ASM",
        confidence="medium",
        body_markers=("the requested url was rejected. please consult with your administrator",),
    ),
    WafSignature(
        provider="Sucuri CloudProxy",
        confidence="high",
        header_markers=(("server", "sucuri/cloudproxy"), ("x-sucuri-id", "")),
        body_markers=("access denied - sucuri website firewall",),
    ),
]


def _cookie_names(response_headers: dict) -> set[str]:
    names: set[str] = set()
    for key, value in (response_headers or {}).items():
        if str(key).lower() != "set-cookie":
            continue
        names.update(m.group(1) for m in _COOKIE_NAME_RE.finditer(str(value)))
    return names


def detect_waf(response_headers: dict | None, response_body: str | None) -> dict | None:
    """Return ``{"provider", "confidence", "evidence"}`` for the first matching
    signature, or ``None`` if nothing recognisable is present.

    Cheap and side-effect free — safe to call on every response.
    """
    headers = response_headers or {}
    lowered_headers = {str(k).lower(): str(v).lower() for k, v in headers.items()}
    body = (response_body or "")[:4000]
    body_lower = body.lower()
    cookies = _cookie_names(headers)

    for sig in _SIGNATURES:
        hit_cookie = next((c for c in sig.cookie_names if c in cookies), None)
        if hit_cookie:
            return {
                "provider": sig.provider,
                "confidence": sig.confidence,
                "evidence": f"Set-Cookie: {hit_cookie}",
            }

        for header_name, substring in sig.header_markers:
            value = lowered_headers.get(header_name)
            if value is None:
                continue
            if not substring or substring in value:
                return {
                    "provider": sig.provider,
                    "confidence": sig.confidence,
                    "evidence": f"{header_name}: {value[:120]}",
                }

        if sig.body_regex and sig.body_regex.search(body):
            match = sig.body_regex.search(body)
            return {
                "provider": sig.provider,
                "confidence": sig.confidence,
                "evidence": f"response body matched {match.group(0)[:120]!r}",
            }

        for marker in sig.body_markers:
            if marker in body_lower:
                return {
                    "provider": sig.provider,
                    "confidence": sig.confidence,
                    "evidence": f"response body contains {marker!r}",
                }

    return None
