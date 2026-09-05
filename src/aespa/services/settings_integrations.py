"""Settings integrations."""

from __future__ import annotations

import json

from sqlmodel import Session

from aespa.models import (
    AdversarialValidatorConfig,
    BrowserDebugConfig,
    BurpRestApiConfig,
    CloudflareAccessConfig,
    CodeExecutionConfig,
    ComponentMapperConfig,
    CrawlerConfig,
    GlobalHttpHeaderConfig,
    ReportingDebugConfig,
    ScannerPolicy,
    SpecialistAgentConfig,
    TestRun,
    UpstreamProxyConfig,
)
from aespa.schemas import (
    BrowserDebugConfigIn,
    BrowserDebugConfigOut,
    BurpRestApiConfigIn,
    BurpRestApiConfigOut,
    CloudflareAccessConfigIn,
    CloudflareAccessConfigOut,
    CodeExecutionConfigIn,
    CodeExecutionConfigOut,
    ComponentMapperConfigIn,
    ComponentMapperConfigOut,
    CrawlerConfigIn,
    CrawlerConfigOut,
    GlobalHttpHeaderConfigIn,
    GlobalHttpHeaderConfigOut,
    ReportingDebugConfigIn,
    ReportingDebugConfigOut,
    RunScannerPolicyOut,
    ScannerPolicyIn,
    ScannerPolicyOut,
    SpecialistAgentConfigIn,
    SpecialistAgentConfigOut,
    UpstreamProxyConfigIn,
    UpstreamProxyConfigOut,
    ValidatorConfigIn,
    ValidatorConfigOut,
)
from aespa.services.settings_values import (
    _SINGLETON_ID,
    _json_dumps,
    _json_loads,
    _utcnow,
)


def _policy_from_model(cfg: ScannerPolicy) -> ScannerPolicyOut:
    return ScannerPolicyOut(
        execution_monitor_enabled=cfg.execution_monitor_enabled,
        disable_deterministic_checks=getattr(
            cfg, "disable_deterministic_checks", False
        ),
        max_consecutive_text_turns=getattr(cfg, "max_consecutive_text_turns", 0),
        enforce_full_coverage_obligations=getattr(
            cfg, "enforce_full_coverage_obligations", False
        ),
        standard_coverage_percent=getattr(cfg, "standard_coverage_percent", 60),
        scan_mode=cfg.scan_mode,
        max_probes_per_page=cfg.max_probes_per_page,
        thinking_max_steps=cfg.thinking_max_steps,
        request_timeout_s=cfg.request_timeout_s,
        min_delay_s=cfg.min_delay_s,
        max_request_body_bytes=cfg.max_request_body_bytes,
        response_body_read_limit_bytes=cfg.response_body_read_limit_bytes,
        allowed_schemes=_json_loads(cfg.allowed_schemes, ["http", "https"]),
        methods_by_mode=_json_loads(cfg.methods_by_mode, None),
        blocked_headers=_json_loads(cfg.blocked_headers, ["host", "cookie"]),
        follow_redirects=cfg.follow_redirects,
        allow_subdomains=cfg.allow_subdomains,
        require_approval_for_destructive=cfg.require_approval_for_destructive,
        strict_locator_enforcement=getattr(cfg, "strict_locator_enforcement", True),
        updated_at=cfg.updated_at,
    )


def get_scanner_policy(session: Session) -> ScannerPolicyOut:
    cfg = session.get(ScannerPolicy, _SINGLETON_ID)
    if cfg is None:
        return ScannerPolicyOut(**ScannerPolicyIn().model_dump(), updated_at=_utcnow())
    return _policy_from_model(cfg)


def get_code_execution_config(session: Session) -> CodeExecutionConfigOut:
    cfg = session.get(CodeExecutionConfig, _SINGLETON_ID)
    if cfg is None:
        return CodeExecutionConfigOut(
            **CodeExecutionConfigIn().model_dump(), updated_at=_utcnow()
        )
    return CodeExecutionConfigOut(
        enabled=cfg.enabled,
        backend=cfg.backend,
        image_ref=cfg.image_ref,
        allowed_roles=_json_loads(
            cfg.allowed_roles_json, ["alice", "specialist", "test_lead"]
        ),
        timeout_s=cfg.timeout_s,
        memory_mb=cfg.memory_mb,
        cpu_cores=cfg.cpu_cores,
        pids_limit=cfg.pids_limit,
        workspace_mb=cfg.workspace_mb,
        output_limit_bytes=cfg.output_limit_bytes,
        artifact_limit_bytes=cfg.artifact_limit_bytes,
        max_requests_per_execution=cfg.max_requests_per_execution,
        max_concurrent_requests=cfg.max_concurrent_requests,
        max_concurrent_executions=cfg.max_concurrent_executions,
        retain_redacted_source=cfg.retain_redacted_source,
        updated_at=cfg.updated_at,
    )


def upsert_code_execution_config(
    session: Session, payload: CodeExecutionConfigIn
) -> CodeExecutionConfigOut:
    cfg = session.get(CodeExecutionConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = CodeExecutionConfig(id=_SINGLETON_ID)
    for key, value in payload.model_dump(exclude={"allowed_roles"}).items():
        setattr(cfg, key, value)
    cfg.allowed_roles_json = _json_dumps(payload.allowed_roles)
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_code_execution_config(session)


def upsert_scanner_policy(
    session: Session, payload: ScannerPolicyIn
) -> ScannerPolicyOut:
    cfg = session.get(ScannerPolicy, _SINGLETON_ID)
    if cfg is None:
        cfg = ScannerPolicy(id=_SINGLETON_ID)

    cfg.execution_monitor_enabled = payload.execution_monitor_enabled
    cfg.disable_deterministic_checks = payload.disable_deterministic_checks
    cfg.max_consecutive_text_turns = payload.max_consecutive_text_turns
    cfg.enforce_full_coverage_obligations = payload.enforce_full_coverage_obligations
    cfg.standard_coverage_percent = payload.standard_coverage_percent
    cfg.scan_mode = payload.scan_mode
    cfg.max_probes_per_page = payload.max_probes_per_page
    cfg.thinking_max_steps = payload.thinking_max_steps
    cfg.request_timeout_s = payload.request_timeout_s
    cfg.min_delay_s = payload.min_delay_s
    cfg.max_request_body_bytes = payload.max_request_body_bytes
    cfg.response_body_read_limit_bytes = payload.response_body_read_limit_bytes
    cfg.allowed_schemes = _json_dumps(payload.allowed_schemes)
    cfg.methods_by_mode = _json_dumps(payload.methods_by_mode)
    cfg.blocked_headers = _json_dumps(payload.blocked_headers)
    cfg.follow_redirects = payload.follow_redirects
    cfg.allow_subdomains = payload.allow_subdomains
    cfg.require_approval_for_destructive = payload.require_approval_for_destructive
    cfg.strict_locator_enforcement = payload.strict_locator_enforcement
    cfg.updated_at = _utcnow()

    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return _policy_from_model(cfg)


def get_crawler_config(session: Session) -> CrawlerConfigOut:
    cfg = session.get(CrawlerConfig, _SINGLETON_ID)
    if cfg is None:
        return CrawlerConfigOut(
            **CrawlerConfigIn().model_dump(),
            updated_at=_utcnow(),
        )
    return CrawlerConfigOut(
        js_endpoint_discovery_enabled=cfg.js_endpoint_discovery_enabled,
        skip_dangerous_actions=cfg.skip_dangerous_actions,
        suppress_form_submit_actions=cfg.suppress_form_submit_actions,
        block_non_idempotent_interactive_replay=cfg.block_non_idempotent_interactive_replay,
        enable_access_reconciliation=cfg.enable_access_reconciliation,
        llm_max_concurrency=cfg.llm_max_concurrency,
        updated_at=cfg.updated_at,
    )


def upsert_crawler_config(
    session: Session, payload: CrawlerConfigIn
) -> CrawlerConfigOut:
    cfg = session.get(CrawlerConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = CrawlerConfig(id=_SINGLETON_ID)
    cfg.js_endpoint_discovery_enabled = payload.js_endpoint_discovery_enabled
    cfg.skip_dangerous_actions = payload.skip_dangerous_actions
    cfg.suppress_form_submit_actions = payload.suppress_form_submit_actions
    cfg.block_non_idempotent_interactive_replay = (
        payload.block_non_idempotent_interactive_replay
    )
    cfg.enable_access_reconciliation = payload.enable_access_reconciliation
    cfg.llm_max_concurrency = payload.llm_max_concurrency
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_crawler_config(session)


def get_component_mapper_config(session: Session) -> ComponentMapperConfigOut:
    cfg = session.get(ComponentMapperConfig, _SINGLETON_ID)
    if cfg is None:
        return ComponentMapperConfigOut(
            **ComponentMapperConfigIn().model_dump(),
            updated_at=_utcnow(),
        )
    return ComponentMapperConfigOut(
        max_tool_calls=cfg.max_tool_calls,
        max_source_files=cfg.max_source_files,
        max_source_bytes=cfg.max_source_bytes,
        max_facts=cfg.max_facts,
        max_concurrent=cfg.max_concurrent,
        max_trace_edges=cfg.max_trace_edges,
        max_trace_components=cfg.max_trace_components,
        max_paths_per_lead=cfg.max_paths_per_lead,
        min_trace_confidence=cfg.min_trace_confidence,
        updated_at=cfg.updated_at,
    )


def upsert_component_mapper_config(
    session: Session, payload: ComponentMapperConfigIn
) -> ComponentMapperConfigOut:
    cfg = session.get(ComponentMapperConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = ComponentMapperConfig(id=_SINGLETON_ID)
    cfg.max_tool_calls = payload.max_tool_calls
    cfg.max_source_files = payload.max_source_files
    cfg.max_source_bytes = payload.max_source_bytes
    cfg.max_facts = payload.max_facts
    cfg.max_concurrent = payload.max_concurrent
    cfg.max_trace_edges = payload.max_trace_edges
    cfg.max_trace_components = payload.max_trace_components
    cfg.max_paths_per_lead = payload.max_paths_per_lead
    cfg.min_trace_confidence = payload.min_trace_confidence
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_component_mapper_config(session)


def get_run_scanner_policy(session: Session, run: TestRun) -> RunScannerPolicyOut:
    policy = get_scanner_policy(session)
    return RunScannerPolicyOut(
        **policy.model_dump(exclude={"updated_at"}),
        source="global_default",
        updated_at=policy.updated_at,
    )


def get_upstream_proxy_config(session: Session) -> UpstreamProxyConfigOut:
    cfg = session.get(UpstreamProxyConfig, _SINGLETON_ID)
    if cfg is None:
        return UpstreamProxyConfigOut(
            **UpstreamProxyConfigIn().model_dump(), updated_at=_utcnow()
        )
    return UpstreamProxyConfigOut(
        proxy_url=cfg.proxy_url,
        proxy_scanner=cfg.proxy_scanner,
        proxy_llm=cfg.proxy_llm,
        updated_at=cfg.updated_at,
    )


def upsert_upstream_proxy_config(
    session: Session, payload: UpstreamProxyConfigIn
) -> UpstreamProxyConfigOut:
    cfg = session.get(UpstreamProxyConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = UpstreamProxyConfig(id=_SINGLETON_ID)
    cfg.proxy_url = payload.proxy_url
    cfg.proxy_scanner = payload.proxy_scanner
    cfg.proxy_llm = payload.proxy_llm
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_upstream_proxy_config(session)


def _burp_rest_api_config_from_model(cfg: BurpRestApiConfig) -> BurpRestApiConfigOut:
    return BurpRestApiConfigOut(
        enabled=cfg.enabled,
        api_url=cfg.api_url,
        has_api_key=bool(cfg.api_key and cfg.api_key.strip()),
        api_key=None,
        scan_configuration_name=cfg.scan_configuration_name,
        scan_sqli=cfg.scan_sqli,
        scan_xss=cfg.scan_xss,
        scan_command_injection=cfg.scan_command_injection,
        scan_path_traversal=cfg.scan_path_traversal,
        scan_ssrf=cfg.scan_ssrf,
        scan_xxe=cfg.scan_xxe,
        scan_ssti=cfg.scan_ssti,
        updated_at=cfg.updated_at,
    )


def get_burp_rest_api_config_model(session: Session) -> BurpRestApiConfig:
    cfg = session.get(BurpRestApiConfig, _SINGLETON_ID)
    if cfg is None:
        return BurpRestApiConfig(id=_SINGLETON_ID)
    return cfg


def get_burp_rest_api_config(session: Session) -> BurpRestApiConfigOut:
    cfg = session.get(BurpRestApiConfig, _SINGLETON_ID)
    if cfg is None:
        return BurpRestApiConfigOut(
            **BurpRestApiConfigIn().model_dump(), updated_at=_utcnow()
        )
    return _burp_rest_api_config_from_model(cfg)


def get_specialist_agent_config(session: Session) -> SpecialistAgentConfigOut:
    cfg = session.get(SpecialistAgentConfig, _SINGLETON_ID)
    if cfg is None:
        return SpecialistAgentConfigOut(
            **SpecialistAgentConfigIn().model_dump(), updated_at=_utcnow()
        )
    return SpecialistAgentConfigOut(
        enabled=cfg.enabled,
        auto_dispatch_enabled=cfg.auto_dispatch_enabled,
        max_concurrent=cfg.max_concurrent,
        max_queued=cfg.max_queued,
        max_steps=cfg.max_steps,
        min_priority=cfg.min_priority,
        dispatch_idor=cfg.dispatch_idor,
        dispatch_auth_bypass=cfg.dispatch_auth_bypass,
        dispatch_sqli=cfg.dispatch_sqli,
        dispatch_xss=cfg.dispatch_xss,
        dispatch_business_logic=cfg.dispatch_business_logic,
        dispatch_ssrf=cfg.dispatch_ssrf,
        dispatch_path_traversal=cfg.dispatch_path_traversal,
        dispatch_cors=cfg.dispatch_cors,
        dispatch_crypto=cfg.dispatch_crypto,
        dispatch_config=cfg.dispatch_config,
        dispatch_file_upload=cfg.dispatch_file_upload,
        trigger_specialist_on_burp=cfg.trigger_specialist_on_burp,
        updated_at=cfg.updated_at,
    )


def upsert_specialist_agent_config(
    session: Session, payload: SpecialistAgentConfigIn
) -> SpecialistAgentConfigOut:
    cfg = session.get(SpecialistAgentConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = SpecialistAgentConfig(id=_SINGLETON_ID)
    cfg.enabled = payload.enabled
    cfg.auto_dispatch_enabled = payload.auto_dispatch_enabled
    cfg.max_concurrent = payload.max_concurrent
    cfg.max_queued = payload.max_queued
    cfg.max_steps = payload.max_steps
    cfg.min_priority = payload.min_priority
    cfg.dispatch_idor = payload.dispatch_idor
    cfg.dispatch_auth_bypass = payload.dispatch_auth_bypass
    cfg.dispatch_sqli = payload.dispatch_sqli
    cfg.dispatch_xss = payload.dispatch_xss
    cfg.dispatch_business_logic = payload.dispatch_business_logic
    cfg.dispatch_ssrf = payload.dispatch_ssrf
    cfg.dispatch_path_traversal = payload.dispatch_path_traversal
    cfg.dispatch_cors = payload.dispatch_cors
    cfg.dispatch_crypto = payload.dispatch_crypto
    cfg.dispatch_config = payload.dispatch_config
    cfg.dispatch_file_upload = payload.dispatch_file_upload
    cfg.trigger_specialist_on_burp = payload.trigger_specialist_on_burp
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_specialist_agent_config(session)


def upsert_burp_rest_api_config(
    session: Session, payload: BurpRestApiConfigIn
) -> BurpRestApiConfigOut:
    cfg = session.get(BurpRestApiConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = BurpRestApiConfig(id=_SINGLETON_ID)

    cfg.enabled = payload.enabled
    cfg.api_url = payload.api_url
    if payload.api_key is not None:
        key_str = payload.api_key.strip()
        cfg.api_key = key_str if key_str else None
    cfg.scan_configuration_name = payload.scan_configuration_name
    cfg.scan_sqli = payload.scan_sqli
    cfg.scan_xss = payload.scan_xss
    cfg.scan_command_injection = payload.scan_command_injection
    cfg.scan_path_traversal = payload.scan_path_traversal
    cfg.scan_ssrf = payload.scan_ssrf
    cfg.scan_xxe = payload.scan_xxe
    cfg.scan_ssti = payload.scan_ssti
    cfg.updated_at = _utcnow()

    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return _burp_rest_api_config_from_model(cfg)


def get_adversarial_validator_config(session: Session) -> ValidatorConfigOut:
    cfg = session.get(AdversarialValidatorConfig, _SINGLETON_ID)
    if cfg is None:
        return ValidatorConfigOut(
            **ValidatorConfigIn().model_dump(), updated_at=_utcnow()
        )
    return ValidatorConfigOut(
        enabled=cfg.enabled,
        max_steps=cfg.max_steps,
        min_severity=cfg.min_severity,
        end_scan_max_concurrent=cfg.end_scan_max_concurrent,
        auto_validate_inline=cfg.auto_validate_inline,
        require_concrete_disproof=cfg.require_concrete_disproof,
        updated_at=cfg.updated_at,
    )


def upsert_adversarial_validator_config(
    session: Session, payload: ValidatorConfigIn
) -> ValidatorConfigOut:
    cfg = session.get(AdversarialValidatorConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = AdversarialValidatorConfig(id=_SINGLETON_ID)
    cfg.enabled = payload.enabled
    cfg.max_steps = payload.max_steps
    cfg.min_severity = payload.min_severity
    cfg.end_scan_max_concurrent = payload.end_scan_max_concurrent
    cfg.auto_validate_inline = payload.auto_validate_inline
    cfg.require_concrete_disproof = payload.require_concrete_disproof
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_adversarial_validator_config(session)


def get_global_http_header_config(session: Session) -> GlobalHttpHeaderConfigOut:
    cfg = session.get(GlobalHttpHeaderConfig, _SINGLETON_ID)
    if cfg is None:
        return GlobalHttpHeaderConfigOut(
            **GlobalHttpHeaderConfigIn().model_dump(), updated_at=_utcnow()
        )
    try:
        parsed_headers = json.loads(cfg.headers_json or "[]")
        headers = parsed_headers if isinstance(parsed_headers, list) else []
    except (TypeError, json.JSONDecodeError):
        headers = []
    # Databases created before multi-header support have values only in these
    # legacy fields. Return that value until the user saves the new table.
    if not headers and cfg.header_name and cfg.header_value:
        headers = [{"header_name": cfg.header_name, "header_value": cfg.header_value}]
    return GlobalHttpHeaderConfigOut(
        headers=headers,
        updated_at=cfg.updated_at,
    )


def upsert_global_http_header_config(
    session: Session, payload: GlobalHttpHeaderConfigIn
) -> GlobalHttpHeaderConfigOut:
    cfg = session.get(GlobalHttpHeaderConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = GlobalHttpHeaderConfig(id=_SINGLETON_ID)
    cfg.headers_json = json.dumps(
        [header.model_dump() for header in payload.headers], separators=(",", ":")
    )
    # Keep the old columns in sync with the first header for a graceful rollback
    # to an earlier AESPA version.
    first_header = payload.headers[0] if payload.headers else None
    cfg.header_name = first_header.header_name if first_header else None
    cfg.header_value = first_header.header_value if first_header else None
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_global_http_header_config(session)


def get_reporting_debug_config(session: Session) -> ReportingDebugConfigOut:
    cfg = session.get(ReportingDebugConfig, _SINGLETON_ID)
    if cfg is None:
        return ReportingDebugConfigOut(
            **ReportingDebugConfigIn().model_dump(),
            updated_at=_utcnow(),
        )
    return ReportingDebugConfigOut(
        capture_enabled=cfg.capture_enabled,
        panel_enabled=cfg.panel_enabled,
        batch_max_concurrent=cfg.batch_max_concurrent,
        updated_at=cfg.updated_at,
    )


def upsert_reporting_debug_config(
    session: Session, payload: ReportingDebugConfigIn
) -> ReportingDebugConfigOut:
    cfg = session.get(ReportingDebugConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = ReportingDebugConfig(id=_SINGLETON_ID)
    cfg.capture_enabled = payload.capture_enabled
    cfg.panel_enabled = payload.panel_enabled
    cfg.batch_max_concurrent = payload.batch_max_concurrent
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_reporting_debug_config(session)


def get_browser_debug_config(session: Session) -> BrowserDebugConfigOut:
    cfg = session.get(BrowserDebugConfig, _SINGLETON_ID)
    if cfg is None:
        return BrowserDebugConfigOut(
            **BrowserDebugConfigIn().model_dump(),
            updated_at=_utcnow(),
        )
    return BrowserDebugConfigOut(
        browser_engine=cfg.browser_engine,
        browser_visible=cfg.browser_visible,
        updated_at=cfg.updated_at,
    )


def upsert_browser_debug_config(
    session: Session, payload: BrowserDebugConfigIn
) -> BrowserDebugConfigOut:
    cfg = session.get(BrowserDebugConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = BrowserDebugConfig(id=_SINGLETON_ID)
    cfg.browser_engine = payload.browser_engine
    cfg.browser_visible = payload.browser_visible
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_browser_debug_config(session)


def get_cloudflare_access_config(session: Session) -> CloudflareAccessConfigOut:
    cfg = session.get(CloudflareAccessConfig, _SINGLETON_ID)
    if cfg is None:
        return CloudflareAccessConfigOut(audience=None, updated_at=_utcnow())
    return CloudflareAccessConfigOut(audience=cfg.audience, updated_at=cfg.updated_at)


def upsert_cloudflare_access_config(
    session: Session, payload: CloudflareAccessConfigIn
) -> CloudflareAccessConfigOut:
    cfg = session.get(CloudflareAccessConfig, _SINGLETON_ID)
    if cfg is None:
        cfg = CloudflareAccessConfig(id=_SINGLETON_ID)
    # Normalise blank → None so the verifier cleanly falls back to "no audience".
    audience = (payload.audience or "").strip()
    cfg.audience = audience or None
    cfg.updated_at = _utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return get_cloudflare_access_config(session)
