"""Passive WAF / bot-mitigation fingerprinting and request strategies.

Detection is passive: signatures come from ordinary response headers, cookies,
and bodies observed during a scan.  Each provider also has an explicit request
strategy.  A browser is useful for products that issue client-side challenges;
it does not make a server-side WAF signature block disappear.

Used from ``services/traffic.py`` (the single choke point for httpx and
Playwright traffic), then surfaced through the run model and recon summary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_COOKIE_NAME_RE = re.compile(r"^\s*([^=;\s]+)=", re.MULTILINE)


@dataclass(frozen=True)
class WafStrategy:
    """How the scanner should handle traffic after a WAF is detected."""

    key: str
    label: str
    transport: str  # ``browser_page`` or ``direct_http``
    summary: str
    operator_note: str
    preserve_cookie_prefixes: tuple[str, ...] = ()
    challenge_markers: tuple[str, ...] = ()
    challenge_headers: tuple[tuple[str, str], ...] = ()
    warmup_ms: int = 0


@dataclass(frozen=True)
class WafSignature:
    provider: str  # short vendor/product label surfaced in the UI
    confidence: str  # "high" | "medium"
    cookie_names: tuple[str, ...] = ()
    header_markers: tuple[tuple[str, str], ...] = ()  # (header name, substring)
    body_markers: tuple[str, ...] = ()  # substrings/regex fragments, matched lowercase
    body_regex: re.Pattern | None = None
    strategy_key: str = "direct_http"


_STRATEGIES: dict[str, WafStrategy] = {
    "akamai_browser": WafStrategy(
        key="akamai_browser",
        label="Real browser page with Bot Manager state",
        transport="browser_page",
        summary=(
            "Run requests from the real browser page, keep Akamai Bot Manager "
            "cookies, and pace probes. A persistent deny is recorded as a WAF "
            "block rather than retried with payload mutations."
        ),
        operator_note=(
            "The browser page is warmed before probes and retains _abck, bm_sz, "
            "and ak_bmsc cookies."
        ),
        preserve_cookie_prefixes=("_abck", "bm_sz", "ak_bmsc"),
        challenge_markers=("challenge", "akamai"),
        warmup_ms=1500,
    ),
    "cloudflare_browser": WafStrategy(
        key="cloudflare_browser",
        label="Real browser page with Cloudflare clearance",
        transport="browser_page",
        summary=(
            "Use a real browser page so JavaScript or a managed challenge can "
            "run, then reuse the resulting clearance for same-origin probes."
        ),
        operator_note=(
            "The scanner retains __cf_bm and cf_clearance. Interactive CAPTCHA "
            "or a continuing challenge is reported as a blocker."
        ),
        preserve_cookie_prefixes=("__cf_bm", "cf_clearance"),
        challenge_markers=(
            "challenge-platform",
            "cf-chl-",
            "checking your browser",
            "just a moment",
        ),
        warmup_ms=1500,
    ),
    "imperva_browser": WafStrategy(
        key="imperva_browser",
        label="Real browser page with Imperva challenge state",
        transport="browser_page",
        summary=(
            "Run requests from the real page, allow the browser challenge to "
            "settle, and preserve the resulting Imperva session cookies."
        ),
        operator_note=(
            "The scanner retains incap_ses, visid_incap, and related challenge "
            "cookies. It does not blindly repeat a blocked request."
        ),
        preserve_cookie_prefixes=("incap_ses", "visid_incap", "reese84", "___utmvc"),
        challenge_markers=("incapsula", "imperva", "reese84"),
        warmup_ms=1500,
    ),
    "aws_browser_challenge": WafStrategy(
        key="aws_browser_challenge",
        label="Browser challenge token, then page fetch",
        transport="browser_page",
        summary=(
            "Use the real page to acquire an AWS WAF Challenge token before "
            "retrying the original request. A normal Block action remains a "
            "valid WAF block even when sent from a browser."
        ),
        operator_note=(
            "The x-amzn-waf-action header is treated as a challenge signal. "
            "CAPTCHA requires an operator; the scanner never attempts to solve it."
        ),
        preserve_cookie_prefixes=("aws-waf-token",),
        challenge_markers=("awswaf", "captcha", "challenge"),
        challenge_headers=(
            ("x-amzn-waf-action", "challenge"),
            ("x-amzn-waf-action", "captcha"),
        ),
        warmup_ms=1200,
    ),
    "f5_browser_challenge": WafStrategy(
        key="f5_browser_challenge",
        label="Browser client-integrity challenge when present",
        transport="browser_page",
        summary=(
            "Use a real browser page for F5 client-integrity challenges. A BIG-IP "
            "ASM signature block is not bypassed by browser routing and is kept as "
            "evidence."
        ),
        operator_note=(
            "The scanner waits for a JavaScript client-integrity response when one "
            "is present, then reports a persistent ASM blocking page."
        ),
        challenge_markers=("client side integrity", "javascript challenge"),
        warmup_ms=1000,
    ),
    "sucuri_direct": WafStrategy(
        key="sucuri_direct",
        label="Direct HTTP with controlled pacing",
        transport="direct_http",
        summary=(
            "Keep the original HTTP method and payload, use the configured pacing, "
            "and treat Sucuri's reverse-proxy/IPS response as the authoritative result."
        ),
        operator_note=(
            "Browser routing is not used because a browser does not remove a "
            "server-side Sucuri policy block."
        ),
    ),
}


def _strategy_payload(strategy: WafStrategy) -> dict[str, Any]:
    return {
        "key": strategy.key,
        "label": strategy.label,
        "transport": strategy.transport,
        "summary": strategy.summary,
        "operator_note": strategy.operator_note,
        "preserve_cookie_prefixes": list(strategy.preserve_cookie_prefixes),
        "challenge_markers": list(strategy.challenge_markers),
        "challenge_headers": [list(item) for item in strategy.challenge_headers],
        "warmup_ms": strategy.warmup_ms,
    }


def strategy_for_provider(provider: str | None) -> dict[str, Any]:
    """Return the stable, serializable strategy for a detected provider."""
    strategy_key = next(
        (
            signature.strategy_key
            for signature in _SIGNATURES
            if signature.provider == provider
        ),
        "direct_http",
    )
    strategy = _STRATEGIES.get(strategy_key)
    if strategy is None:
        strategy = WafStrategy(
            key="direct_http",
            label="Direct HTTP with controlled pacing",
            transport="direct_http",
            summary="Keep the original request and treat a persistent block as WAF evidence.",
            operator_note="No browser challenge strategy is known for this provider.",
        )
    return _strategy_payload(strategy)


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
        strategy_key="akamai_browser",
    ),
    WafSignature(
        provider="Cloudflare",
        confidence="high",
        cookie_names=("__cf_bm", "cf_clearance"),
        header_markers=(("server", "cloudflare"), ("cf-ray", "")),
        body_markers=(
            "attention required! | cloudflare",
            "checking your browser before accessing",
        ),
        strategy_key="cloudflare_browser",
    ),
    WafSignature(
        provider="Imperva / Incapsula",
        confidence="high",
        cookie_names=("incap_ses", "visid_incap"),
        body_markers=("incapsula incident id", "request unsuccessful. incapsula"),
        strategy_key="imperva_browser",
    ),
    WafSignature(
        provider="AWS WAF",
        confidence="medium",
        # x-amzn-requestid is common on ordinary AWS responses and is not WAF
        # evidence. The WAF action header is emitted for Challenge/CAPTCHA.
        header_markers=(("x-amzn-waf-action", ""),),
        strategy_key="aws_browser_challenge",
    ),
    WafSignature(
        provider="F5 BIG-IP ASM",
        confidence="medium",
        body_markers=(
            "the requested url was rejected. please consult with your administrator",
        ),
        strategy_key="f5_browser_challenge",
    ),
    WafSignature(
        provider="Sucuri CloudProxy",
        confidence="high",
        header_markers=(("server", "sucuri/cloudproxy"), ("x-sucuri-id", "")),
        body_markers=("access denied - sucuri website firewall",),
        strategy_key="sucuri_direct",
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
    """Return provider, evidence, and its request strategy for a response."""
    headers = response_headers or {}
    lowered_headers = {str(k).lower(): str(v).lower() for k, v in headers.items()}
    body = (response_body or "")[:4000]
    body_lower = body.lower()
    cookies = _cookie_names(headers)

    for sig in _SIGNATURES:
        strategy = _STRATEGIES[sig.strategy_key]
        hit_cookie = next((c for c in sig.cookie_names if c in cookies), None)
        if hit_cookie:
            return {
                "provider": sig.provider,
                "confidence": sig.confidence,
                "evidence": f"Set-Cookie: {hit_cookie}",
                "strategy": _strategy_payload(strategy),
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
                    "strategy": _strategy_payload(strategy),
                }

        if sig.body_regex and sig.body_regex.search(body):
            match = sig.body_regex.search(body)
            return {
                "provider": sig.provider,
                "confidence": sig.confidence,
                "evidence": f"response body matched {match.group(0)[:120]!r}",
                "strategy": _strategy_payload(strategy),
            }

        for marker in sig.body_markers:
            if marker in body_lower:
                return {
                    "provider": sig.provider,
                    "confidence": sig.confidence,
                    "evidence": f"response body contains {marker!r}",
                    "strategy": _strategy_payload(strategy),
                }

    return None
