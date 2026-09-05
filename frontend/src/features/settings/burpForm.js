import { DEFAULT_BURP_REST_API_FORM } from "./burpDefaults.js";

export function burpRestApiToForm(cfg) {
  return cfg
    ? {
        enabled: cfg.enabled ?? false,
        api_url: cfg.api_url || DEFAULT_BURP_REST_API_FORM.api_url,
        api_key: "",
        has_api_key: cfg.has_api_key ?? false,
        clear_api_key: false,
        scan_configuration_name: cfg.scan_configuration_name || "",
        scan_sqli: cfg.scan_sqli ?? true,
        scan_xss: cfg.scan_xss ?? true,
        scan_command_injection: cfg.scan_command_injection ?? true,
        scan_path_traversal: cfg.scan_path_traversal ?? true,
        scan_ssrf: cfg.scan_ssrf ?? true,
        scan_xxe: cfg.scan_xxe ?? true,
        scan_ssti: cfg.scan_ssti ?? true,
      }
    : {
        ...DEFAULT_BURP_REST_API_FORM,
        has_api_key: false,
        clear_api_key: false,
      };
}

export function burpRestApiPayload(form) {
  let apiKeyPayload = null;
  if (form.clear_api_key) {
    apiKeyPayload = "";
  } else if (form.api_key.trim()) {
    apiKeyPayload = form.api_key.trim();
  } else {
    apiKeyPayload = null;
  }
  return {
    enabled: !!form.enabled,
    api_url: form.api_url.trim(),
    api_key: apiKeyPayload,
    scan_configuration_name: form.scan_configuration_name.trim() || null,
    scan_sqli: !!form.scan_sqli,
    scan_xss: !!form.scan_xss,
    scan_command_injection: !!form.scan_command_injection,
    scan_path_traversal: !!form.scan_path_traversal,
    scan_ssrf: !!form.scan_ssrf,
    scan_xxe: !!form.scan_xxe,
    scan_ssti: !!form.scan_ssti,
  };
}
