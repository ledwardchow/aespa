"""Targeted Burp Suite active scans for web scan candidates."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from aespa.extensions import (
    ProviderAvailability,
    SourceProviderContext,
    SourceProviderField,
    WebScanCandidate,
    WebScanContext,
    WebScanIssue,
    WebScanResult,
)

from . import client

_DEFAULT_URL = "http://127.0.0.1:1337"
_DEFAULT_CONFIGURATION = "Audit checks - all except time-based detection methods"
_CLASSES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "SQL Injection",
        "scan_sqli",
        ("sql injection", "sql error", "blind sql", "sqli", "sql blind"),
        "sqli",
    ),
    (
        "XSS",
        "scan_xss",
        (
            "xss",
            "cross-site scripting",
            "cross site scripting",
            "reflected xss",
            "stored xss",
            "dom xss",
            "dom-based xss",
        ),
        "xss",
    ),
    (
        "Command Injection",
        "scan_command_injection",
        (
            "command injection",
            "os command",
            "shell injection",
            "shell command",
            "rce",
            "remote code execution",
        ),
        "sqli",
    ),
    (
        "Path Traversal",
        "scan_path_traversal",
        (
            "path traversal",
            "directory traversal",
            "file traversal",
            "local file inclusion",
            "remote file inclusion",
            "lfi",
            "rfi",
        ),
        "path_traversal",
    ),
    (
        "SSRF",
        "scan_ssrf",
        ("ssrf", "server-side request forgery", "server side request forgery"),
        "ssrf",
    ),
    ("XXE", "scan_xxe", ("xxe", "xml external entity", "external entity"), "sqli"),
    (
        "SSTI",
        "scan_ssti",
        (
            "ssti",
            "server-side template injection",
            "server side template injection",
            "template injection",
        ),
        "xss",
    ),
)


def _vulnerability_class(text: str) -> str | None:
    lowered = text.lower()
    for label, _key, keywords, _specialist in _CLASSES:
        if any(keyword in lowered for keyword in keywords):
            return label
    if "sql" in lowered and "inject" in lowered:
        return "SQL Injection"
    if "cross-site" in lowered:
        return "XSS"
    return None


def _enabled(settings: dict[str, Any], label: str) -> bool:
    return bool(
        settings.get(next(key for name, key, _, _ in _CLASSES if name == label), True)
    )


def _specialist(settings: dict[str, Any], label: str) -> str | None:
    if not settings.get("trigger_specialist", False):
        return None
    return next(attack for name, _, _, attack in _CLASSES if name == label)


def _config(context: SourceProviderContext) -> client.BurpConfig:
    url = str(context.settings.get("api_url") or _DEFAULT_URL).strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Burp REST API URL must be an http:// or https:// URL")
    name = context.settings.get("scan_configuration_name", _DEFAULT_CONFIGURATION)
    return client.BurpConfig(
        api_url=url,
        api_key=context.secrets.get("api_key") if context.secrets else None,
        scan_configuration_name=str(name).strip() or None if name is not None else None,
    )


class BurpScanner:
    id = "aespa.burpsuite"
    label = "Burp Suite active scanner"
    description = "Run targeted Burp Suite Professional active scans during a web scan."
    agent_role = "Burp"
    phase = "burp_active_scan"
    finding_source = "burp_active_scan"
    settings_schema_version = 1
    settings_fields = [
        SourceProviderField(
            "api_url",
            "REST API URL",
            default=_DEFAULT_URL,
            help="Burp Suite Professional REST API address.",
        ),
        SourceProviderField(
            "api_key",
            "API key",
            type="secret",
            help="Optional Bearer token for the Burp REST API.",
        ),
        SourceProviderField(
            "scan_configuration_name",
            "Scan configuration name",
            default=_DEFAULT_CONFIGURATION,
            help="Leave blank to use Burp's default audit configuration.",
        ),
        *[
            SourceProviderField(key, f"Scan {label}", type="boolean", default=True)
            for label, key, _, _ in _CLASSES
        ],
        SourceProviderField(
            "trigger_specialist",
            "Also run a specialist agent",
            type="boolean",
            default=False,
        ),
    ]

    def candidate_from_finding(
        self, finding: dict[str, Any], settings: dict[str, Any]
    ) -> WebScanCandidate | None:
        label = _vulnerability_class(
            " ".join(
                str(finding.get(key) or "")
                for key in ("title", "description", "owasp_category")
            )
        )
        if not label or not _enabled(settings, label):
            return None
        return WebScanCandidate(
            url=str(finding.get("affected_url") or ""),
            title=str(finding.get("title") or label),
            vulnerability_class=label,
            finding_id=finding.get("id"),
            page_id=finding.get("page_id"),
            specialist_attack_class=_specialist(settings, label),
        )

    def candidate_from_investigation(
        self, tool_input: dict[str, Any], note: str, settings: dict[str, Any]
    ) -> WebScanCandidate | None:
        text = " ".join(
            str(tool_input.get(key) or "")
            for key in ("hypothesis", "payload_purpose", "observation", "url")
        )
        label = _vulnerability_class(f"{note or ''} {text}")
        if not label or not _enabled(settings, label):
            return None
        title = str(
            tool_input.get("hypothesis")
            or tool_input.get("payload_purpose")
            or note
            or label
        )[:200]
        return WebScanCandidate(
            url=str(tool_input.get("url") or "").strip(),
            title=title,
            vulnerability_class=label,
            specialist_attack_class=_specialist(settings, label),
        )

    async def check_availability(
        self, context: SourceProviderContext
    ) -> ProviderAvailability:
        try:
            config = _config(context)
        except ValueError as exc:
            return ProviderAvailability(False, "setup_required", str(exc))
        return ProviderAvailability(
            True,
            "configured",
            f"Configured for {config.api_url}. Select Check to test the connection.",
        )

    async def check_connection(
        self, context: SourceProviderContext
    ) -> ProviderAvailability:
        try:
            ok, message = await client.test_connection(_config(context))
        except ValueError as exc:
            return ProviderAvailability(False, "setup_required", str(exc))
        return ProviderAvailability(ok, "ready" if ok else "unavailable", message)

    async def scan(
        self, candidate: WebScanCandidate, context: WebScanContext
    ) -> WebScanResult:
        config = _config(context)
        task_id = await client.launch_active_scan(
            config,
            candidate.url,
            cookies=context.cookies or None,
            extra_headers=context.extra_headers or None,
        )
        context.on_started(str(task_id))
        issues = await client.wait_for_scan(config, task_id)
        return WebScanResult(
            task_id=str(task_id),
            issues=[
                WebScanIssue(
                    title=f"[Burp] {issue.get('name') or 'Unknown issue'}",
                    affected_url=issue.get("affected_url") or candidate.url,
                    severity=issue.get("severity") or "medium",
                    description=issue.get("description") or "",
                    recommendation=issue.get("remediation") or "",
                    confidence=issue.get("confidence") or "unknown",
                    request_evidence=issue.get("request_evidence") or "",
                    response_evidence=issue.get("response_evidence") or "",
                )
                for issue in issues
            ],
        )


class BurpSuiteExtension:
    def register(self, registry) -> None:
        registry.register_web_active_scanner(BurpScanner())
