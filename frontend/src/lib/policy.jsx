
// ── Scanner policy helpers ──────────────────────────────────────────────────

export const SCAN_MODE_OPTIONS = [
  ["passive", "Passive"],
  ["safe_active", "Safe Active"],
  ["aggressive", "Aggressive"],
  ["destructive", "Destructive"],
];
export const SCAN_MODE_DEFINITIONS = {
  passive:"Passive checks only. Requests pages to inspect headers, cookies, and obvious access-control signals without running LLM-planned attack probes.",
  safe_active:"Bounded active testing. Allows non-destructive HTTP probes and common payloads for issues such as XSS, injection markers, IDOR, and auth checks.",
  aggressive:"Noisier active testing. Allows broader fuzzing, more HTTP methods, and higher-risk payloads that may trigger alerts or affect application state.",
  destructive:"Highest-risk testing. Allows potentially state-changing probes; use only with explicit authorization and approval controls.",
};
export const scanModeLabel = (mode) => (SCAN_MODE_OPTIONS.find(([v])=>v===mode)||[])[1] || mode;
export function ScanModeDefinitions({ selected }) {
  return (
    <div className="scan-mode-definitions">
      {SCAN_MODE_OPTIONS.map(([value, label]) => (
        <div key={value} className={"scan-mode-definition" + (selected === value ? " selected" : "")}>
          <span className={"scan-mode-badge mode-" + value}>{label}</span>
          <span>{SCAN_MODE_DEFINITIONS[value]}</span>
        </div>
      ))}
    </div>
  );
}
export const csv = (value, transform=(x)=>x) => String(value||"")
  .split(",").map(x=>transform(x.trim())).filter(Boolean);
export const defaultPolicyForm = () => ({
  scan_mode:"safe_active",
  max_probes_per_page:50,
  thinking_max_steps:120,
  request_timeout_s:10,
  min_delay_s:0.05,
  max_request_body_bytes:65536,
  response_body_read_limit_bytes:524288,
  allowed_schemes:"http, https",
  methods_passive:"GET, HEAD",
  methods_safe_active:"GET, POST, HEAD",
  methods_aggressive:"GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS",
  methods_destructive:"GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS",
  blocked_headers:"host, cookie",
  follow_redirects:true,
  allow_subdomains:true,
  require_approval_for_destructive:true,
});
export const policyToForm = (p) => {
  const f = defaultPolicyForm();
  if (!p) return f;
  const mbm = p.methods_by_mode || {};
  return {
    ...f,
    scan_mode:p.scan_mode || f.scan_mode,
    max_probes_per_page:p.max_probes_per_page ?? f.max_probes_per_page,
    thinking_max_steps:p.thinking_max_steps ?? f.thinking_max_steps,
    request_timeout_s:p.request_timeout_s ?? f.request_timeout_s,
    min_delay_s:p.min_delay_s ?? f.min_delay_s,
    max_request_body_bytes:p.max_request_body_bytes ?? f.max_request_body_bytes,
    response_body_read_limit_bytes:p.response_body_read_limit_bytes ?? f.response_body_read_limit_bytes,
    allowed_schemes:(p.allowed_schemes || ["http","https"]).join(", "),
    methods_passive:(mbm.passive || ["GET","HEAD"]).join(", "),
    methods_safe_active:(mbm.safe_active || ["GET","POST","HEAD"]).join(", "),
    methods_aggressive:(mbm.aggressive || ["GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"]).join(", "),
    methods_destructive:(mbm.destructive || ["GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"]).join(", "),
    blocked_headers:(p.blocked_headers || ["host","cookie"]).join(", "),
    follow_redirects:p.follow_redirects ?? true,
    allow_subdomains:p.allow_subdomains ?? true,
    require_approval_for_destructive:p.require_approval_for_destructive ?? true,
  };
};
export const policyPayload = (form) => ({
  scan_mode:form.scan_mode,
  max_probes_per_page:Number(form.max_probes_per_page),
  thinking_max_steps:Number(form.thinking_max_steps),
  request_timeout_s:Number(form.request_timeout_s),
  min_delay_s:Number(form.min_delay_s),
  max_request_body_bytes:Number(form.max_request_body_bytes),
  response_body_read_limit_bytes:Number(form.response_body_read_limit_bytes),
  allowed_schemes:csv(form.allowed_schemes, x=>x.toLowerCase()),
  methods_by_mode:{
    passive:csv(form.methods_passive, x=>x.toUpperCase()),
    safe_active:csv(form.methods_safe_active, x=>x.toUpperCase()),
    aggressive:csv(form.methods_aggressive, x=>x.toUpperCase()),
    destructive:csv(form.methods_destructive, x=>x.toUpperCase()),
  },
  blocked_headers:csv(form.blocked_headers, x=>x.toLowerCase()),
  follow_redirects:!!form.follow_redirects,
  allow_subdomains:!!form.allow_subdomains,
  require_approval_for_destructive:!!form.require_approval_for_destructive,
});

