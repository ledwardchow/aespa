import { DEFAULT_SPECIALIST_AGENT_FORM } from "./specialistDefaults.js";

export function specialistAgentToForm(cfg) {
  return cfg
    ? {
        enabled: cfg.enabled ?? true,
        auto_dispatch_enabled: cfg.auto_dispatch_enabled ?? true,
        max_concurrent: cfg.max_concurrent ?? 5,
        max_queued: cfg.max_queued ?? 20,
        max_steps: cfg.max_steps ?? 30,
        min_priority: cfg.min_priority ?? 7,
        dispatch_idor: cfg.dispatch_idor ?? true,
        dispatch_auth_bypass: cfg.dispatch_auth_bypass ?? true,
        dispatch_sqli: cfg.dispatch_sqli ?? true,
        dispatch_xss: cfg.dispatch_xss ?? true,
        dispatch_business_logic: cfg.dispatch_business_logic ?? true,
        dispatch_ssrf: cfg.dispatch_ssrf ?? true,
        dispatch_path_traversal: cfg.dispatch_path_traversal ?? true,
        dispatch_cors: cfg.dispatch_cors ?? false,
        dispatch_crypto: cfg.dispatch_crypto ?? true,
        dispatch_config: cfg.dispatch_config ?? false,
        dispatch_file_upload: cfg.dispatch_file_upload ?? true,
        trigger_specialist_on_burp: cfg.trigger_specialist_on_burp ?? false,
      }
    : {
        ...DEFAULT_SPECIALIST_AGENT_FORM,
      };
}

export function specialistAgentPayload(form) {
  return {
    enabled: !!form.enabled,
    auto_dispatch_enabled: !!form.auto_dispatch_enabled,
    max_concurrent: Number(form.max_concurrent),
    max_queued: Number(form.max_queued),
    max_steps: Number(form.max_steps),
    min_priority: Number(form.min_priority),
    dispatch_idor: !!form.dispatch_idor,
    dispatch_auth_bypass: !!form.dispatch_auth_bypass,
    dispatch_sqli: !!form.dispatch_sqli,
    dispatch_xss: !!form.dispatch_xss,
    dispatch_business_logic: !!form.dispatch_business_logic,
    dispatch_ssrf: !!form.dispatch_ssrf,
    dispatch_path_traversal: !!form.dispatch_path_traversal,
    dispatch_cors: !!form.dispatch_cors,
    dispatch_crypto: !!form.dispatch_crypto,
    dispatch_config: !!form.dispatch_config,
    dispatch_file_upload: !!form.dispatch_file_upload,
    trigger_specialist_on_burp: !!form.trigger_specialist_on_burp,
  };
}
