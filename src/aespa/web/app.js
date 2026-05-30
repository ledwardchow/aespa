import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import htm from "htm";
import * as d3 from "d3";

const html = htm.bind(React.createElement);

// ── API client ────────────────────────────────────────────────────────────────

const api = {
  listSites:        ()            => req("/api/sites"),
  getSite:          (id)          => req(`/api/sites/${id}`),
  createSite:       (b)           => req("/api/sites",         { method:"POST",   body:b }),
  updateSite:       (id,b)        => req(`/api/sites/${id}`,   { method:"PUT",    body:b }),
  deleteSite:       (id)          => req(`/api/sites/${id}`,   { method:"DELETE" }),
  importSite:       (text)        => fetch("/api/sites/import", { method:"POST", headers:{"Content-Type":"application/json"}, body:text }).then(async r => { const d = r.ok ? await r.json() : (() => { throw new Error(`Import failed: ${r.status}`); })(); return d; }),
  getLLMConfig:     ()            => req("/api/settings/llm"),
  upsertLLMConfig:  (b)           => req("/api/settings/llm",  { method:"PUT",    body:b }),
  listLLMProfiles:  ()            => req("/api/settings/llm/profiles"),
  createLLMProfile: (b)           => req("/api/settings/llm/profiles", { method:"POST", body:b }),
  updateLLMProfile: (id,b)        => req(`/api/settings/llm/profiles/${id}`, { method:"PUT", body:b }),
  activateLLMProfile: (id)        => req(`/api/settings/llm/profiles/${id}/activate`, { method:"POST" }),
  deleteLLMProfile: (id)          => req(`/api/settings/llm/profiles/${id}`, { method:"DELETE" }),
  listLLMProviders: ()            => req("/api/settings/llm/providers"),
  createLLMProvider: (b)          => req("/api/settings/llm/providers", { method:"POST", body:b }),
  updateLLMProvider: (id,b)       => req(`/api/settings/llm/providers/${id}`, { method:"PUT", body:b }),
  deleteLLMProvider: (id)         => req(`/api/settings/llm/providers/${id}`, { method:"DELETE" }),
  exportLLMConfig:  ()            => req("/api/settings/llm/export"),
  importLLMConfig:  (b)           => req("/api/settings/llm/import", { method:"POST", body:b }),
  getDefaultModels: ()            => req("/api/settings/llm/models"),
  getScannerPolicy: ()            => req("/api/settings/scanner-policy"),
  upsertScannerPolicy: (b)        => req("/api/settings/scanner-policy", { method:"PUT", body:b }),
  getBurpRestApiConfig: ()        => req("/api/settings/burp-rest-api"),
  upsertBurpRestApiConfig: (b)    => req("/api/settings/burp-rest-api", { method:"PUT", body:b }),
  testBurpConnection: ()          => req("/api/settings/burp-rest-api/test-connection", { method:"POST" }),
  getUpstreamProxy: ()            => req("/api/settings/upstream-proxy"),
  upsertUpstreamProxy: (b)        => req("/api/settings/upstream-proxy", { method:"PUT", body:b }),
  getSpecialistAgentConfig: ()    => req("/api/settings/specialist-agent-config"),
  upsertSpecialistAgentConfig:(b) => req("/api/settings/specialist-agent-config", { method:"PUT", body:b }),
  getAdversarialValidatorConfig: ()    => req("/api/settings/adversarial-validator-config"),
  upsertAdversarialValidatorConfig:(b) => req("/api/settings/adversarial-validator-config", { method:"PUT", body:b }),
  getGlobalHttpHeader: ()         => req("/api/settings/global-http-header"),
  upsertGlobalHttpHeader: (b)     => req("/api/settings/global-http-header", { method:"PUT", body:b }),
  getReportingDebugConfig: ()     => req("/api/settings/reporting-debug"),
  upsertReportingDebugConfig:(b)  => req("/api/settings/reporting-debug", { method:"PUT", body:b }),
  getReportingDebugPrompt: (key)  => req(`/api/reporting-debug/prompt${key?`?key=${encodeURIComponent(key)}`:""}`),
  listReportingDebugPrompts:()    => req("/api/reporting-debug/prompts"),
  saveReportingDebugPrompt:(key,b)=> req(`/api/reporting-debug/prompt?key=${encodeURIComponent(key)}`, { method:"PUT", body:b }),
  resetReportingDebugPrompt:(key) => req(`/api/reporting-debug/prompt/reset?key=${encodeURIComponent(key)}`, { method:"POST" }),
  listReportingPromptVersions:(key)=> req(`/api/reporting-debug/prompt-versions?key=${encodeURIComponent(key)}`),
  createReportingPromptVersion:(b)=> req("/api/reporting-debug/prompt-versions", { method:"POST", body:b }),
  updateReportingPromptVersion:(id,b)=> req(`/api/reporting-debug/prompt-versions/${id}`, { method:"PUT", body:b }),
  deleteReportingPromptVersion:(id)=> req(`/api/reporting-debug/prompt-versions/${id}`, { method:"DELETE" }),
  listReportingCaptures: ()       => req("/api/reporting-debug/captures"),
  getReportingCapture:(id)         => req(`/api/reporting-debug/captures/${id}`),
  replayReportingCapture:(id,b={})=> req(`/api/reporting-debug/captures/${id}/replay`, { method:"POST", body:b }),
  getReportingReplay:(id)         => req(`/api/reporting-debug/replays/${id}`),
  listReportingReplays:()         => req("/api/reporting-debug/replays"),
  listActiveJobs:    ()            => req("/api/test-runs/active"),
  listRuns:         (siteId)      => req(`/api/sites/${siteId}/test-runs`),
  createRun:        (siteId,b)    => req(`/api/sites/${siteId}/test-runs`, { method:"POST", body:b }),
  getRun:           (id)          => req(`/api/test-runs/${id}`),
  deleteRun:        (id)          => req(`/api/test-runs/${id}`,  { method:"DELETE" }),
  startRun:         (id)          => req(`/api/test-runs/${id}/start`,   { method:"POST" }),
  stopRun:          (id)          => req(`/api/test-runs/${id}/stop`,    { method:"POST" }),
  restartRun:       (id)          => req(`/api/test-runs/${id}/restart`, { method:"POST" }),
  clearCrawl:       (id)          => req(`/api/test-runs/${id}/crawl/clear`, { method:"POST" }),
  getGraph:         (id)          => req(`/api/test-runs/${id}/graph`),
  listPages:        (id)          => req(`/api/test-runs/${id}/pages`),
  getPage:          (runId,pgId)  => req(`/api/test-runs/${runId}/pages/${pgId}`),
  getPageViews:     (runId,pgId)  => req(`/api/test-runs/${runId}/pages/${pgId}/views`),
  getTargetIntelligence: (id,kind="") => req(`/api/test-runs/${id}/target-intelligence${kind?`?kind=${encodeURIComponent(kind)}`:""}`),
  getScannerSessions: (id, includeInactive=true) => req(`/api/test-runs/${id}/scanner-sessions${includeInactive?"?include_inactive=true":""}`),
  updateScannerSession: (runId, sessionId, b) => req(`/api/test-runs/${runId}/scanner-sessions/${sessionId}`, { method:"PATCH", body:b }),
  getTaskGraph:     (id)          => req(`/api/test-runs/${id}/task-graph`),
  seedTaskGraph:    (id)          => req(`/api/test-runs/${id}/task-graph/seed`, { method:"POST" }),
  getReconSummary:  (id)          => req(`/api/test-runs/${id}/recon-summary`),
  setPageScope:     (runId,pgId,b)=> req(`/api/test-runs/${runId}/pages/${pgId}/scope`, { method:"PATCH", body:b }),
  updateScopeHosts: (siteId, hosts) => req(`/api/sites/${siteId}/scope-hosts`, { method:"PUT", body:{scope_hosts:hosts} }),
  deletePage:       (runId,pgId,cascade) => req(`/api/test-runs/${runId}/pages/${pgId}?cascade=${cascade}`, { method:"DELETE" }),
  updateRun:        (id,b)        => req(`/api/test-runs/${id}`,                         { method:"PATCH", body:b }),
  startThinkingScan:(id)          => req(`/api/test-runs/${id}/thinking-scan/start`,      { method:"POST" }),
  resumeThinkingScan:(id)         => req(`/api/test-runs/${id}/thinking-scan/resume`,     { method:"POST" }),
  stopThinkingScan: (id)          => req(`/api/test-runs/${id}/thinking-scan/stop`,       { method:"POST" }),
  getThinkingStatus:(id)          => req(`/api/test-runs/${id}/thinking-scan/status`),
  getCheckpointStatus:(id)        => req(`/api/test-runs/${id}/thinking-scan/checkpoint`),
  getScanLog:        (id)          => req(`/api/test-runs/${id}/scan-log`),
  getAgentLog:       (id)          => req(`/api/test-runs/${id}/agent-log`),
  getTokenUsage:     (id)          => req(`/api/test-runs/${id}/token-usage`),
  getAliceSessions:  (id)          => req(`/api/test-runs/${id}/alice/sessions`),
  saveAliceSessions: (id, b)       => req(`/api/test-runs/${id}/alice/sessions`, { method:"PUT", body:b }),
  getAliceStatus:    (id)          => req(`/api/test-runs/${id}/alice/status`),
  startAliceRun:     (id, b)       => req(`/api/test-runs/${id}/alice/run`,      { method:"POST", body:b }),
  stopAliceRun:      (id)          => req(`/api/test-runs/${id}/alice/run`,      { method:"DELETE" }),
  getFindings:           (id)       => req(`/api/test-runs/${id}/findings`),
  deleteFinding:         (id,fid)   => req(`/api/test-runs/${id}/findings/${fid}`, { method:"DELETE" }),
  deleteFindingGroup:    (id,title) => req(`/api/test-runs/${id}/findings?title=${encodeURIComponent(title)}`, { method:"DELETE" }),
  importFindings:        (id,b)     => req(`/api/test-runs/${id}/findings/import`, { method:"POST", body:b }),
  deduplicateFindings:   (id)       => req(`/api/test-runs/${id}/findings/deduplicate`, { method:"POST" }),
  validateAllFindings:   (id)       => req(`/api/test-runs/${id}/validate`, { method:"POST" }),
  validateFinding:       (id,fid)   => req(`/api/test-runs/${id}/findings/${fid}/validate`, { method:"POST" }),
  stopValidation:        (id)       => req(`/api/test-runs/${id}/validate/stop`, { method:"POST" }),
  getValidateStatus:     (id)       => req(`/api/test-runs/${id}/validate/status`),
  getTraffic:       (id,since)    => req(`/api/test-runs/${id}/traffic?since_id=${since||0}`),
  getTrafficCount:  (id)          => req(`/api/test-runs/${id}/traffic/count`),
  clearFindings:        (id)       => req(`/api/test-runs/${id}/findings`,              { method:"DELETE" }),
  clearScanLog:         (id)       => req(`/api/test-runs/${id}/scan-log`,              { method:"DELETE" }),
  clearTargetIntel:     (id)       => req(`/api/test-runs/${id}/target-intelligence`,   { method:"DELETE" }),
  clearTaskGraph:       (id)       => req(`/api/test-runs/${id}/task-graph`,            { method:"DELETE" }),
  getVersion:       ()            => req("/api/version"),
};

async function req(url, opts = {}) {
  const init = { method: opts.method || "GET", headers: { "Content-Type": "application/json" } };
  if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
  const res  = await fetch(url, init);
  if (res.status === 204) return null;
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const msg = formatError(data) || `${res.status} ${res.statusText}`;
    const err = new Error(msg); err.status = res.status; throw err;
  }
  return data;
}

function formatError(d) {
  if (!d) return null;
  if (typeof d.detail === "string") return d.detail;
  if (Array.isArray(d.detail)) return d.detail.map(x => `${(x.loc||[]).join(".")}: ${x.msg}`).join("\n");
  return JSON.stringify(d);
}

// ── Hash router ───────────────────────────────────────────────────────────────

function useRoute() {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const cb = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", cb);
    return () => window.removeEventListener("hashchange", cb);
  }, []);

  if (!hash || hash === "#/" || hash === "#") return { name: "list" };

  let m;
  if ((m = hash.match(/^#\/sites\/new$/)))               return { name: "site-new" };
  if ((m = hash.match(/^#\/sites\/(\d+)\/edit$/)))       return { name: "site-edit",   id: +m[1] };
  if ((m = hash.match(/^#\/sites\/(\d+)\/runs\/new$/)))  return { name: "run-new",     siteId: +m[1] };
  if ((m = hash.match(/^#\/sites\/(\d+)$/)))             return { name: "site-detail", id: +m[1] };
  if ((m = hash.match(/^#\/runs\/(\d+)\/([a-z]+)$/)))   return { name: "run-detail",  id: +m[1], tab: m[2] };
  if ((m = hash.match(/^#\/runs\/(\d+)$/)))              return { name: "run-detail",  id: +m[1] };
  if (hash === "#/active-jobs")                          return { name: "active-jobs" };
  if (hash === "#/settings")                             return { name: "settings" };
  if (hash === "#/scan-policy")                          return { name: "scan-policy" };
  if (hash === "#/external-integrations")                return { name: "external-integrations" };
  if (hash === "#/debug")                                return { name: "debug" };
  if (hash === "#/reporting-debug")                      return { name: "reporting-debug" };

  return { name: "list" };
}

const nav = (to) => { window.location.hash = to; };

// ── Scanner policy helpers ──────────────────────────────────────────────────

const SCAN_MODE_OPTIONS = [
  ["passive", "Passive"],
  ["safe_active", "Safe Active"],
  ["aggressive", "Aggressive"],
  ["destructive", "Destructive"],
];
const SCAN_MODE_DEFINITIONS = {
  passive:"Passive checks only. Requests pages to inspect headers, cookies, and obvious access-control signals without running LLM-planned attack probes.",
  safe_active:"Bounded active testing. Allows non-destructive HTTP probes and common payloads for issues such as XSS, injection markers, IDOR, and auth checks.",
  aggressive:"Noisier active testing. Allows broader fuzzing, more HTTP methods, and higher-risk payloads that may trigger alerts or affect application state.",
  destructive:"Highest-risk testing. Allows potentially state-changing probes; use only with explicit authorization and approval controls.",
};
const scanModeLabel = (mode) => (SCAN_MODE_OPTIONS.find(([v])=>v===mode)||[])[1] || mode;
function ScanModeDefinitions({ selected }) {
  return html`<div className="scan-mode-definitions">
    ${SCAN_MODE_OPTIONS.map(([value,label])=>html`
      <div key=${value} className=${"scan-mode-definition"+(selected===value?" selected":"")}>
        <span className=${"scan-mode-badge mode-"+value}>${label}</span>
        <span>${SCAN_MODE_DEFINITIONS[value]}</span>
      </div>`)}
  </div>`;
}
const csv = (value, transform=(x)=>x) => String(value||"")
  .split(",").map(x=>transform(x.trim())).filter(Boolean);
const defaultPolicyForm = () => ({
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
const policyToForm = (p) => {
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
const policyPayload = (form) => ({
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

// ── Icons ─────────────────────────────────────────────────────────────────────

const IconSites = () => html`<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
  <rect x="1" y="1" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
  <rect x="9" y="1" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
  <rect x="1" y="9" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
  <rect x="9" y="9" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
</svg>`;

const IconSettings = () => html`<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
  <circle cx="8" cy="8" r="2.2" stroke="currentColor" stroke-width="1.4"/>
  <path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M2.93 2.93l1.06 1.06M12.01 12.01l1.06 1.06M2.93 13.07l1.06-1.06M12.01 3.99l1.06-1.06"
    stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
</svg>`;

const IconPlus = () => html`<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
  <path d="M7 1v12M1 7h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
</svg>`;

const IconCheck = () => html`<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
  <path d="M2 7l4 4 6-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;

const IconPlay = () => html`<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
  <path d="M3 2l9 5-9 5V2z" fill="currentColor"/>
</svg>`;

const IconStop = () => html`<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
  <rect x="2" y="2" width="10" height="10" rx="1.5" fill="currentColor"/>
</svg>`;

const IconShield = () => html`<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
  <path d="M8 1.5L2 4v4c0 3 2.5 5.5 6 6 3.5-.5 6-3 6-6V4L8 1.5z"
    stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
</svg>`;
const IconChevronLeft = () => html`<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
  <path d="M9 2L4 7l5 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;
const IconChevronRight = () => html`<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
  <path d="M5 2l5 5-5 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;
const IconBug = () => html`<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
  <circle cx="8" cy="9" r="4" stroke="currentColor" stroke-width="1.4"/>
  <path d="M6 5.5C6 4.4 6.9 3.5 8 3.5s2 .9 2 2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
  <path d="M4 7H2M12 7h2M4 10H2M12 10h2M5 13l-1.5 1.5M11 13l1.5 1.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
</svg>`;

const IconMessageSquare = () => html`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
</svg>`;
const IconSend = () => html`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="22" y1="2" x2="11" y2="13"></line>
  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
</svg>`;
const IconBrain = () => html`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.44 2.5 2.5 0 0 1 0-3.12 3 3 0 0 1 0-3.88 2.5 2.5 0 0 1 0-3.12A2.5 2.5 0 0 1 9.5 2Z"/>
  <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.44 2.5 2.5 0 0 0 0-3.12 3 3 0 0 0 0-3.88 2.5 2.5 0 0 0 0-3.12A2.5 2.5 0 0 0 14.5 2Z"/>
</svg>`;



// ── A.L.I.C.E. Session Manager ─────────────────────────────────────────────
// Module-level singleton: keeps the stream reader loop alive even when the
// TestRunDetail component unmounts (user navigates away). Subscribers
// (React setState callbacks) are registered/deregistered as the component
// mounts and unmounts. On re-mount, the component can re-subscribe and
// immediately get the current live state.
const aliceSessionStore = {};

function getAliceSession(runId, tabId) {
  const key = `${runId}:${tabId}`;
  if (!aliceSessionStore[key]) {
    aliceSessionStore[key] = {
      active: false,
      abortController: null,
      thinkMsgId: null,
      replyMsgId: null,
      accumulatedThought: "",
      accumulatedMessage: "",
      subscribers: new Set(),
    };
  }
  return aliceSessionStore[key];
}

function aliceSessionSubscribe(runId, tabId, handlers) {
  const session = getAliceSession(runId, tabId);
  session.subscribers.add(handlers);
  return () => session.subscribers.delete(handlers);
}

function aliceSessionAbort(runId, tabId) {
  const key = `${runId}:${tabId}`;
  const session = aliceSessionStore[key];
  if (session?.abortController) {
    session.abortController.abort();
  }
}

const _aliceFlushRecovery = (runId, tabId, thinkMsgId, replyMsgId, thought, message) => {
  try {
    localStorage.setItem(
      `alice_recover_${runId}:${tabId}`,
      JSON.stringify({ thinkMsgId, replyMsgId, thought, message })
    );
  } catch (_) {}
};

// Connect to /alice/stream?cursor=N and pump events through the session.
// Called both for fresh sessions (cursor=0) and reconnects after a page refresh.
async function aliceSessionConnect(runId, tabId, { thinkMsgId, replyMsgId, cursor = 0, onFinish, onFail }) {
  const session = getAliceSession(runId, tabId);
  if (session.active) return;
  session.active = true;
  session.thinkMsgId = thinkMsgId;
  session.replyMsgId = replyMsgId;
  // Re-accumulate from cursor 0 on every connect so the totals are always correct.
  session.accumulatedThought = "";
  session.accumulatedMessage = "";

  const controller = new AbortController();
  session.abortController = controller;

  try {
    const response = await fetch(
      `/api/test-runs/${runId}/alice/stream?cursor=${cursor}`,
      { signal: controller.signal }
    );
    if (!response.ok) throw new Error(`HTTP error ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data: ")) continue;
        try {
          const event = JSON.parse(trimmed.slice(6));
          if (event.type === "thinking_chunk" && event.delta)
            session.accumulatedThought += event.delta;
          else if (event.type === "message_chunk" && event.delta)
            session.accumulatedMessage += event.delta;
          else if (event.type === "done") {
            if (event.thought) session.accumulatedThought = event.thought;
            if (event.message) session.accumulatedMessage = event.message;
          }
          _aliceFlushRecovery(runId, tabId, thinkMsgId, replyMsgId,
            session.accumulatedThought, session.accumulatedMessage);
          session.subscribers.forEach(h => h.onChunk && h.onChunk(event));
        } catch (_) {}
      }
    }

    session.subscribers.forEach(h => h.onDone && h.onDone());
    if (onFinish) onFinish();
  } catch (err) {
    session.subscribers.forEach(h => h.onError && h.onError(err));
    if (onFail) onFail(err);
  } finally {
    session.active = false;
    session.abortController = null;
  }
}

// Start a new ALICE turn: POST to /alice/run (starts background task on server),
// then open the event stream so the client receives events in real time.
async function aliceSessionStart(runId, tabId, { userText, historyPayload, thinkMsgId, replyMsgId, onFinish, onFail }) {
  // Seed recovery immediately so a fast refresh can find the message IDs.
  _aliceFlushRecovery(runId, tabId, thinkMsgId, replyMsgId, "", "");

  try {
    const resp = await fetch(`/api/test-runs/${runId}/alice/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: userText,
        history: historyPayload,
        tab_id: tabId,
        think_msg_id: thinkMsgId,
        reply_msg_id: replyMsgId,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP error ${resp.status}`);
  } catch (err) {
    if (onFail) onFail(err);
    return;
  }

  await aliceSessionConnect(runId, tabId, { thinkMsgId, replyMsgId, cursor: 0, onFinish, onFail });
}

const parseToolArgs = (text) => {

  const args = {};
  const jsonMatch = text.match(/\{.*\}/s);
  if (jsonMatch) {
    try {
      return JSON.parse(jsonMatch[0]);
    } catch (_) {}
  }
  
  // Extract key-value parameter pairs (e.g. url='http://...')
  const kvRegex = /([a-zA-Z0-9_]+)\s*=\s*(['"][^'"]*['"]|[^,)]+)/g;
  let match;
  while ((match = kvRegex.exec(text)) !== null) {
    let key = match[1];
    let val = match[2].trim();
    if ((val.startsWith("'") && val.endsWith("'")) || (val.startsWith('"') && val.endsWith('"'))) {
      val = val.slice(1, -1);
    }
    args[key] = val;
  }
  return Object.keys(args).length > 0 ? args : null;
};


const parseAliceThinking = (text) => {
  if (!text) return [];
  
  const blocks = [];
  const lines = text.split("\n");
  let currentParagraph = [];
  let inCodeBlock = false;
  let codeLang = "";
  let codeContent = [];
  
  let inToolCall = false;
  let toolCallContent = [];
  let inToolResponse = false;
  let toolResponseContent = [];

  for (let line of lines) {
    const trimmed = line.trim();
    
    // Code block transition
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        // End of code block
        blocks.push({
          type: "code",
          lang: codeLang,
          text: codeContent.join("\n")
        });
        inCodeBlock = false;
        codeContent = [];
      } else {
        // Start of code block
        // Flush existing paragraph first
        if (currentParagraph.length > 0) {
          blocks.push({ type: "thought", text: currentParagraph.join("\n") });
          currentParagraph = [];
        }
        inCodeBlock = true;
        codeLang = line.slice(3).trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeContent.push(line);
      continue;
    }

    // Tool Call tag handling (multi-line)
    if (inToolCall) {
      if (trimmed.includes("</tool_call>")) {
        const parts = line.split("</tool_call>");
        if (parts[0]) toolCallContent.push(parts[0]);
        inToolCall = false;
        
        const rawText = toolCallContent.join("\n");
        let toolName = "unknown";
        let toolArgsText = rawText;
        try {
          const parsed = JSON.parse(rawText.trim());
          if (parsed && parsed.name) {
            toolName = parsed.name;
            if (parsed.arguments) {
              toolArgsText = JSON.stringify(parsed.arguments);
            }
          }
        } catch (_) {
          const nameMatch = rawText.match(/"name"\s*:\s*"([^"]+)"/);
          if (nameMatch) toolName = nameMatch[1];
        }
        
        blocks.push({
          type: "tool_call",
          tool: toolName,
          text: toolArgsText
        });
        toolCallContent = [];
      } else {
        toolCallContent.push(line);
      }
      continue;
    }

    // Tool Response tag handling (multi-line)
    if (inToolResponse) {
      if (trimmed.includes("</tool_response>")) {
        const parts = line.split("</tool_response>");
        if (parts[0]) toolResponseContent.push(parts[0]);
        inToolResponse = false;
        
        blocks.push({
          type: "tool_response",
          text: toolResponseContent.join("\n")
        });
        toolResponseContent = [];
      } else {
        toolResponseContent.push(line);
      }
      continue;
    }

    // Start of Tool Call block
    if (trimmed.includes("<tool_call>")) {
      if (currentParagraph.length > 0) {
        blocks.push({ type: "thought", text: currentParagraph.join("\n") });
        currentParagraph = [];
      }
      
      if (trimmed.includes("</tool_call>")) {
        const startIndex = line.indexOf("<tool_call>");
        const endIndex = line.indexOf("</tool_call>");
        const content = line.substring(startIndex + 11, endIndex);
        
        let toolName = "unknown";
        let toolArgsText = content;
        try {
          const parsed = JSON.parse(content.trim());
          if (parsed && parsed.name) {
            toolName = parsed.name;
            if (parsed.arguments) {
              toolArgsText = JSON.stringify(parsed.arguments);
            }
          }
        } catch (_) {
          const nameMatch = content.match(/"name"\s*:\s*"([^"]+)"/);
          if (nameMatch) toolName = nameMatch[1];
        }
        
        blocks.push({
          type: "tool_call",
          tool: toolName,
          text: toolArgsText
        });
      } else {
        inToolCall = true;
        const parts = line.split("<tool_call>");
        if (parts[1]) toolCallContent.push(parts[1]);
      }
      continue;
    }

    // Start of Tool Response block
    if (trimmed.includes("<tool_response>")) {
      if (currentParagraph.length > 0) {
        blocks.push({ type: "thought", text: currentParagraph.join("\n") });
        currentParagraph = [];
      }
      
      if (trimmed.includes("</tool_response>")) {
        const startIndex = line.indexOf("<tool_response>");
        const endIndex = line.indexOf("</tool_response>");
        const content = line.substring(startIndex + 15, endIndex);
        
        blocks.push({
          type: "tool_response",
          text: content
        });
      } else {
        inToolResponse = true;
        const parts = line.split("<tool_response>");
        if (parts[1]) toolResponseContent.push(parts[1]);
      }
      continue;
    }

    // Step/Status logs
    if (trimmed.startsWith("[A.L.I.C.E. Initializing]") || trimmed.includes("Mapped target sitemap")) {
      if (currentParagraph.length > 0) {
        blocks.push({ type: "thought", text: currentParagraph.join("\n") });
        currentParagraph = [];
      }
      blocks.push({ type: "status", status: "initializing", text: trimmed });
      continue;
    }

    if (trimmed.startsWith("Evaluating prompt scope compliance:") || trimmed.includes("In-Scope verified")) {
      if (currentParagraph.length > 0) {
        blocks.push({ type: "thought", text: currentParagraph.join("\n") });
        currentParagraph = [];
      }
      blocks.push({ type: "status", status: "scope_check", text: trimmed });
      continue;
    }

    if (trimmed.startsWith("Scope compliance verified") || trimmed.includes("Starting agentic assessment loop")) {
      if (currentParagraph.length > 0) {
        blocks.push({ type: "thought", text: currentParagraph.join("\n") });
        currentParagraph = [];
      }
      blocks.push({ type: "status", status: "scope_check", text: trimmed });
      continue;
    }

    if (trimmed.startsWith("Routing directives to the LLM agent model:") || trimmed.includes("Routing directives")) {
      if (currentParagraph.length > 0) {
        blocks.push({ type: "thought", text: currentParagraph.join("\n") });
        currentParagraph = [];
      }
      blocks.push({ type: "status", status: "routing", text: trimmed });
      continue;
    }

    // [Step N] Calling LLM... / [Step N] Tool result (N chars)
    if (/^\[Step \d+\] (Calling LLM|Tool result)/.test(trimmed)) {
      if (currentParagraph.length > 0) {
        blocks.push({ type: "thought", text: currentParagraph.join("\n") });
        currentParagraph = [];
      }
      blocks.push({ type: "status", status: "routing", text: trimmed });
      continue;
    }

    if (trimmed.startsWith("[A.L.I.C.E. Boundary Violation Alert]")) {
      if (currentParagraph.length > 0) {
        blocks.push({ type: "thought", text: currentParagraph.join("\n") });
        currentParagraph = [];
      }
      blocks.push({ type: "alert", level: "danger", title: "Boundary Violation", text: trimmed });
      continue;
    }

    if (trimmed.startsWith("[ALICE Error]")) {
      if (currentParagraph.length > 0) {
        blocks.push({ type: "thought", text: currentParagraph.join("\n") });
        currentParagraph = [];
      }
      blocks.push({ type: "alert", level: "error", title: "Error", text: trimmed });
      continue;
    }

    // Step-level tool execution detection (e.g. "[Step 1] Executing tool: http_request")
    const toolCallRegex = /(?:Calling|Invoking|Executing)\s+tool:?\s+([a-zA-Z0-9_]+)|(?:tool_call|toolCall):\s*([a-zA-Z0-9_]+)/i;
    const match = trimmed.match(toolCallRegex);
    if (match) {
      if (currentParagraph.length > 0) {
        blocks.push({ type: "thought", text: currentParagraph.join("\n") });
        currentParagraph = [];
      }
      const toolName = match[1] || match[2];
      blocks.push({ type: "tool_call", tool: toolName, text: trimmed });
      continue;
    }

    // Standard text line
    if (trimmed !== "") {
      currentParagraph.push(line);
    } else if (currentParagraph.length > 0) {
      blocks.push({ type: "thought", text: currentParagraph.join("\n") });
      currentParagraph = [];
    }
  }

  // Flush remaining paragraphs or code blocks
  if (inCodeBlock && codeContent.length > 0) {
    blocks.push({ type: "code", lang: codeLang, text: codeContent.join("\n") });
  } else if (inToolCall && toolCallContent.length > 0) {
    blocks.push({ type: "tool_call", tool: "unknown", text: toolCallContent.join("\n") });
  } else if (inToolResponse && toolResponseContent.length > 0) {
    blocks.push({ type: "tool_response", text: toolResponseContent.join("\n") });
  } else if (currentParagraph.length > 0) {
    blocks.push({ type: "thought", text: currentParagraph.join("\n") });
  }

  return blocks;
};


const renderMarkdown = (text) => {
  if (!text) return "";
  
  const lines = text.split("\n");
  const elements = [];
  let inList = false;
  let listItems = [];
  let codeBlockContent = [];
  let inCodeBlock = false;
  let codeBlockLang = "";

  const renderTextWithFormatting = (txt) => {
    const inlineRegex = /(`[^`]+`|\*\*[^*]+\*\*)/g;
    const segments = txt.split(inlineRegex);
    
    return segments.map((seg, idx) => {
      if (seg.startsWith("`") && seg.endsWith("`")) {
        return html`<code className="alice-inline-code">${seg.slice(1, -1)}</code>`;
      }
      if (seg.startsWith("**") && seg.endsWith("**")) {
        return html`<strong className="alice-bold-text">${seg.slice(2, -2)}</strong>`;
      }
      return seg;
    });
  };

  const parseTableRow = (rowText) => {
    const cells = rowText.split("|").map(c => c.trim());
    if (cells[0] === "") cells.shift();
    if (cells[cells.length - 1] === "") cells.pop();
    return cells;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Code blocks
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        inCodeBlock = false;
        elements.push(html`
          <div className="alice-code-block-wrapper">
            <div className="alice-code-block-header">
              <span className="alice-code-block-lang">${codeBlockLang || "text"}</span>
            </div>
            <pre className="alice-code-block"><code>${codeBlockContent.join("\n")}</code></pre>
          </div>
        `);
        codeBlockContent = [];
      } else {
        if (inList) {
          elements.push(html`<ul className="alice-markdown-list">${listItems.map(item => html`<li>${renderTextWithFormatting(item)}</li>`)}</ul>`);
          inList = false;
          listItems = [];
        }
        inCodeBlock = true;
        codeBlockLang = line.slice(3).trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockContent.push(line);
      continue;
    }

    // Tables
    if (trimmed.startsWith("|")) {
      if (inList) {
        elements.push(html`<ul className="alice-markdown-list">${listItems.map(item => html`<li>${renderTextWithFormatting(item)}</li>`)}</ul>`);
        inList = false;
        listItems = [];
      }

      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i].trim());
        i++;
      }
      i--; // Adjust loop counter

      if (tableLines.length >= 2) {
        const headers = parseTableRow(tableLines[0]);
        const rows = [];
        const bodyLines = tableLines.slice(2);
        for (const rLine of bodyLines) {
          if (rLine.includes("---")) continue;
          rows.push(parseTableRow(rLine));
        }

        elements.push(html`
          <div className="alice-table-wrapper">
            <table className="alice-table">
              <thead>
                <tr>
                  ${headers.map(h => html`<th>${renderTextWithFormatting(h)}</th>`)}
                </tr>
              </thead>
              <tbody>
                ${rows.map(row => html`
                  <tr>
                    ${row.map(cell => html`<td>${renderTextWithFormatting(cell)}</td>`)}
                  </tr>
                `)}
              </tbody>
            </table>
          </div>
        `);
        continue;
      }
    }

    // Headers
    if (trimmed.startsWith("### ")) {
      if (inList) {
        elements.push(html`<ul className="alice-markdown-list">${listItems.map(item => html`<li>${renderTextWithFormatting(item)}</li>`)}</ul>`);
        inList = false;
        listItems = [];
      }
      elements.push(html`<h4 className="alice-md-h3">${renderTextWithFormatting(trimmed.slice(4))}</h4>`);
      continue;
    }
    if (trimmed.startsWith("## ")) {
      if (inList) {
        elements.push(html`<ul className="alice-markdown-list">${listItems.map(item => html`<li>${renderTextWithFormatting(item)}</li>`)}</ul>`);
        inList = false;
        listItems = [];
      }
      elements.push(html`<h3 className="alice-md-h2">${renderTextWithFormatting(trimmed.slice(3))}</h3>`);
      continue;
    }

    // Lists
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      inList = true;
      listItems.push(trimmed.slice(2));
      continue;
    }

    // Paragraph
    if (trimmed === "") {
      if (inList) {
        elements.push(html`<ul className="alice-markdown-list">${listItems.map(item => html`<li>${renderTextWithFormatting(item)}</li>`)}</ul>`);
        inList = false;
        listItems = [];
      }
      elements.push(html`<div className="alice-md-space"></div>`);
    } else {
      if (inList) {
        elements.push(html`<ul className="alice-markdown-list">${listItems.map(item => html`<li>${renderTextWithFormatting(item)}</li>`)}</ul>`);
        inList = false;
        listItems = [];
      }
      elements.push(html`<p className="alice-md-p">${renderTextWithFormatting(line)}</p>`);
    }
  }

  if (inList) {
    elements.push(html`<ul className="alice-markdown-list">${listItems.map(item => html`<li>${renderTextWithFormatting(item)}</li>`)}</ul>`);
  }
  if (inCodeBlock && codeBlockContent.length > 0) {
    elements.push(html`
      <div className="alice-code-block-wrapper">
        <div className="alice-code-block-header">
          <span className="alice-code-block-lang">${codeBlockLang || "text"}</span>
        </div>
        <pre className="alice-code-block"><code>${codeBlockContent.join("\n")}</code></pre>
      </div>
    `);
  }

  return elements;
};


const renderAliceBlocks = (text, isThinking) => {
  const blocks = parseAliceThinking(text);
  return blocks.map((block, idx) => {
    if (block.type === "status") {
      let icon = html`<span className="alice-status-dot"></span>`;
      if (block.status === "initializing") {
        icon = html`<span className="alice-status-icon alice-status-icon--init">⚙️</span>`;
      } else if (block.status === "scope_check") {
        icon = html`<span className="alice-status-icon alice-status-icon--success">🛡️</span>`;
      } else if (block.status === "routing") {
        icon = html`<span className="alice-status-icon alice-status-icon--routing">⚡</span>`;
      }
      return html`
        <div key=${idx} className=${"alice-thinking-status-row alice-thinking-status-row--" + block.status} style=${isThinking ? {} : { margin: "6px 0" }}>
          ${icon}
          <span className="alice-status-text">${block.text}</span>
        </div>
      `;
    }
    if (block.type === "alert") {
      return html`
        <div key=${idx} className=${"alice-thinking-alert alice-thinking-alert--" + block.level} style=${isThinking ? {} : { margin: "6px 0" }}>
          <span className="alice-alert-icon">⚠️</span>
          <div className="alice-alert-content">
            <div className="alice-alert-title">${block.title}</div>
            <div className="alice-alert-text">${block.text}</div>
          </div>
        </div>
      `;
    }
    if (block.type === "tool_call") {
      const parsedArgs = parseToolArgs(block.text);
      return html`
        <div key=${idx} className="alice-thinking-tool-call" style=${{ width: "100%", margin: "6px 0" }}>
          <div className="alice-tool-header-row">
            <span className="alice-tool-prompt">$</span>
            <span className="alice-tool-badge">CALL TOOL</span>
            <span className="alice-tool-name">${block.tool}</span>
          </div>
          ${parsedArgs ? html`
            <div className="alice-tool-args-card">
              ${Object.entries(parsedArgs).map(([key, val]) => html`
                <div key=${key} className="alice-tool-arg-row">
                  <span className="alice-tool-arg-key">${key}:</span>
                  <span className="alice-tool-arg-val">${String(val)}</span>
                </div>
              `)}
            </div>
          ` : html`
            <div className="alice-tool-text">${block.text}</div>
          `}
        </div>
      `;
    }
    if (block.type === "tool_response") {
      let isJson = false;
      let formattedResponse = block.text;
      try {
        const parsed = JSON.parse(block.text.trim());
        formattedResponse = JSON.stringify(parsed, null, 2);
        isJson = true;
      } catch (_) {}
      return html`
        <div key=${idx} className="alice-thinking-tool-response" style=${{ width: "100%", margin: "6px 0" }}>
          <div className="alice-tool-header-row" style=${{ borderLeft: "3px solid #10b981", paddingLeft: "10px" }}>
            <span className="alice-tool-prompt" style=${{ color: "#10b981" }}>←</span>
            <span className="alice-tool-badge" style=${{ background: "rgba(16, 185, 129, 0.15)", color: "#34d399" }}>RESPONSE</span>
          </div>
          <div className="alice-code-block-wrapper" style=${{ marginTop: "4px" }}>
            <div className="alice-code-block-header">
              <span className="alice-code-block-lang">${isJson ? "json" : "text"}</span>
            </div>
            <pre className="alice-code-block"><code style=${{ fontSize: "10.5px" }}>${formattedResponse}</code></pre>
          </div>
        </div>
      `;
    }
    if (block.type === "code") {
      return html`
        <div key=${idx} className="alice-code-block-wrapper">
          <div className="alice-code-block-header">
            <span className="alice-code-block-lang">${block.lang || "json"}</span>
          </div>
          <pre className="alice-code-block"><code>${block.text}</code></pre>
        </div>
      `;
    }
    if (isThinking) {
      return html`
        <p key=${idx} className="alice-thinking-paragraph">${block.text}</p>
      `;
    } else {
      return html`
        <div key=${idx} className="alice-reply-paragraph-wrapper">${renderMarkdown(block.text)}</div>
      `;
    }
  });
};


// ── Shell ──────────────────────────────────────────────────────────────────────

function App() {
  const route = useRoute();
  const onSites      = ["list","site-new","site-edit","site-detail","run-new","run-detail"].includes(route.name);
  const onActiveJobs = route.name === "active-jobs";
  const onSettings   = route.name === "settings";
  const onScanPolicy = route.name === "scan-policy";
  const onExternalIntegrations = route.name === "external-integrations";
  const onDebug      = route.name === "debug";
  const onReportingDebug = route.name === "reporting-debug";
  const [appVersion, setAppVersion] = useState("");
  const [username, setUsername] = useState("");
  const [showUsername, setShowUsername] = useState(() => {
    try {
      const val = localStorage.getItem("aespa_show_username");
      return val === null ? true : val === "true";
    } catch (_) { return true; }
  });
  const [collapsed, setCollapsed] = useState(false);
  const [reportingDebugCfg, setReportingDebugCfg] = useState(null);
  useEffect(() => {
    api.getVersion()
      .then(d => {
        setAppVersion(d.version);
        setUsername(d.username || "");
      })
      .catch(()=>{});
    api.getReportingDebugConfig().then(setReportingDebugCfg).catch(()=>{});
  }, []);

  return html`
    <div className=${"shell"+(collapsed?" sidebar-collapsed":"")}>
      <aside className=${"sidebar"+(collapsed?" sidebar--collapsed":"")}>
        <div className="sidebar-brand">
          <div className="logo">
            ${!collapsed && html`<div className="logo-codename"><span>CODE</span><span>NAME</span></div>`}
            <img src="/icon-sm.png" className="logo-icon" alt="AESPA" />
            ${!collapsed && html`<span className="logo-text">ESPA</span>`}
          </div>
          ${!collapsed && html`<div className="logo-sub">AI-Enabled Security Pentesting Agent</div>`}
        </div>
        <div className="sidebar-meta">
          <button className="sidebar-toggle" onClick=${()=>setCollapsed(c=>!c)} title=${collapsed?"Expand sidebar":"Collapse sidebar"}>
            ${collapsed ? html`<${IconChevronRight}/>` : html`<${IconChevronLeft}/>`}
          </button>
          ${!collapsed && html`
            <div style=${{display: "flex", flexDirection: "column", gap: "2px", overflow: "hidden", minWidth: 0, lineHeight: 1.2}}>
              ${showUsername && username ? html`
                <span className="sidebar-username" style=${{color: "var(--text-2)", fontWeight: "500", fontSize: "11px", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap"}} title=${username}>
                  ${username}
                </span>
                ${appVersion && html`<span style=${{color: "var(--muted)", fontSize: "9.5px"}}>v${appVersion}</span>`}
              ` : html`
                ${appVersion && html`<span>v${appVersion}</span>`}
              `}
            </div>
          `}
        </div>
        <nav className="sidebar-nav">
          ${!collapsed && html`<div className="nav-section-label">Targets</div>`}
          <a href="#/" className=${"nav-item"+(onSites?" active":"")} title="Sites">
            <span className="nav-icon"><${IconSites}/></span>${!collapsed && " Sites"}
          </a>
          <a href="#/active-jobs" className=${"nav-item"+(onActiveJobs?" active":"")} title="Active Jobs">
            <span className="nav-icon"><${IconPlay}/></span>${!collapsed && " Active Jobs"}
          </a>
          ${!collapsed && html`<div className="nav-section-label" style=${{marginTop:8}}>Configuration</div>`}
          <a href="#/settings" className=${"nav-item"+(onSettings?" active":"")} title="LLM Settings">
            <span className="nav-icon"><${IconSettings}/></span>${!collapsed && " LLM Settings"}
          </a>
          <a href="#/scan-policy" className=${"nav-item"+(onScanPolicy?" active":"")} title="Agent Settings">
            <span className="nav-icon"><${IconShield}/></span>${!collapsed && " Agent Settings"}
          </a>
          <a href="#/external-integrations" className=${"nav-item"+(onExternalIntegrations?" active":"")} title="External Integrations">
            <span className="nav-icon"><${IconShield}/></span>${!collapsed && " External Integrations"}
          </a>
          <a href="#/debug" className=${"nav-item"+(onDebug?" active":"")} title="Debug">
            <span className="nav-icon"><${IconBug}/></span>${!collapsed && " Debug"}
          </a>
          ${reportingDebugCfg?.panel_enabled && html`
            ${!collapsed && html`<div className="nav-section-label" style=${{marginTop:8}}>Testing Features</div>`}
            <a href="#/reporting-debug" className=${"nav-item"+(onReportingDebug?" active":"")} title="Reporting Lab">
              <span className="nav-icon"><${IconBug}/></span>${!collapsed && " Reporting Lab"}
            </a>`}
        </nav>
      </aside>


      <div className="main">
        ${route.name==="list"        && html`<${SitesList}/>`}
        ${route.name==="site-new"    && html`<${SiteForm} key="new"/>`}
        ${route.name==="site-edit"   && html`<${SiteForm} key=${route.id} siteId=${route.id}/>`}
        ${route.name==="site-detail" && html`<${SiteDetail} key=${route.id} siteId=${route.id}/>`}
        ${route.name==="active-jobs" && html`<${ActiveJobsPage}/>`}
        ${route.name==="run-new"     && html`<${TestRunForm} key=${route.siteId} siteId=${route.siteId}/>`}
        ${route.name==="run-detail"  && html`<${TestRunDetail} key=${route.id} runId=${route.id} initialTab=${route.tab}/>`}
        ${route.name==="settings"    && html`<${SettingsPage}/>`}
        ${route.name==="scan-policy" && html`<${ScanPolicyPage}/>`}
        ${route.name==="external-integrations" && html`<${ExternalIntegrationsPage}/>`}
        ${route.name==="debug"       && html`<${DebugPage} showUsername=${showUsername} setShowUsername=${setShowUsername} username=${username} reportingDebugCfg=${reportingDebugCfg} setReportingDebugCfg=${setReportingDebugCfg}/>`}
        ${route.name==="reporting-debug" && html`<${ReportingDebugPage}/>`}
      </div>
    </div>
  `;
}

// ── Sites list ────────────────────────────────────────────────────────────────

function SitesList() {
  const [sites, setSites] = useState(null);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
  const importRef = useRef(null);
  const load = useCallback(async () => {
    try { setSites(await api.listSites()); } catch(e) { setError(e.message); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const onDelete = async (s) => {
    if (!confirm(`Delete "${s.name}"? This also removes all test runs and credentials.`)) return;
    try { await api.deleteSite(s.id); await load(); } catch(e) { setError(e.message); }
  };
  const onExport = (s) => { window.location.href = `/api/sites/${s.id}/export`; };
  const onImportFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    e.target.value = "";
    setImporting(true); setError(null);
    try {
      const text = await file.text();
      await api.importSite(text);
      await load();
    } catch(err) { setError(err.message); }
    finally { setImporting(false); }
  };
  return html`
    <div className="topbar">
      <div className="topbar-title">Sites</div>
      <div className="topbar-actions">
        <input ref=${importRef} type="file" accept=".json" style=${{display:"none"}} onChange=${onImportFile}/>
        <button className="btn secondary" onClick=${()=>importRef.current.click()} disabled=${importing}>${importing?"Importing…":"Import site"}</button>
        <button className="btn" onClick=${()=>nav("#/sites/new")}><${IconPlus}/> New site</button>
      </div>
    </div>
    <div className="content scroll-content">
      ${error && html`<div className="alert error" style=${{marginBottom:16}}>${error}</div>`}
      ${sites===null && html`<div className="subtle">Loading…</div>`}
      ${sites!==null&&sites.length===0 && html`
        <div className="empty-state">
          <div className="empty-icon">⬡</div>
          <div className="empty-msg">No sites configured</div>
          <div className="empty-sub">Add a target site to begin setting up your pentest scope.</div>
          <button className="btn" onClick=${()=>nav("#/sites/new")}><${IconPlus}/> New site</button>
        </div>`}
      ${sites&&sites.length>0 && html`
        <div className="table-wrap">
          <table>
            <colgroup>
              <col style=${{width:"18%"}}/><col style=${{width:"42%"}}/><col style=${{width:"10%"}}/><col style=${{width:"10%"}}/><col style=${{width:"20%"}}/>
            </colgroup>
            <thead><tr><th>Name</th><th>Base URL</th><th>Auth</th><th>Credentials</th><th></th></tr></thead>
            <tbody>${sites.map(s=>html`
              <tr key=${s.id}>
                <td><a href=${`#/sites/${s.id}`} style=${{fontWeight:600}}>${s.name}</a></td>
                <td className="url">${s.base_url}</td>
                <td>${s.requires_auth?html`<span className="badge ok">required</span>`:html`<span className="badge neutral">none</span>`}</td>
                <td>${s.credential_count>0?s.credential_count:html`<span className="subtle">—</span>`}</td>
                <td>
                  <div className="row" style=${{justifyContent:"flex-end"}}>
                    <button className="btn secondary sm" onClick=${()=>nav(`#/sites/${s.id}`)}>Open</button>
                    <button className="btn secondary sm" onClick=${()=>onExport(s)}>Export</button>
                    <button className="btn danger-outline sm" onClick=${()=>onDelete(s)}>Delete</button>
                  </div>
                </td>
              </tr>`)}
            </tbody>
          </table>
        </div>`}
    </div>
  `;
}

// ── Active jobs ───────────────────────────────────────────────────────────────

function activeJobBadge(job) {
  const status = job.status || "running";
  const key = status === "failed" ? "danger"
    : status === "stopping" ? "stopping"
    : status === "complete" ? "ok"
    : ["running", "analysing"].includes(status) ? "running"
    : "neutral";
  return html`<span className=${"badge " + key}>${status}</span>`;
}

function activeJobProgress(job) {
  if (job.total_pages !== null && job.total_pages !== undefined) {
    return `${job.pages_done || 0} / ${job.total_pages}`;
  }
  if (job.pages_done !== null && job.pages_done !== undefined) return job.pages_done;
  return "—";
}

function ActiveJobsPage() {
  const [jobs, setJobs] = useState(null);
  const [error, setError] = useState(null);
  const load = useCallback(async () => {
    try {
      setError(null);
      setJobs(await api.listActiveJobs());
    } catch(e) {
      setError(e.message);
    }
  }, []);
  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  return html`
    <div className="topbar">
      <div className="topbar-title">Active Jobs</div>
      <div className="topbar-actions">
        <button className="btn secondary" onClick=${load}>Refresh</button>
      </div>
    </div>
    <div className="content scroll-content">
      ${error && html`<div className="alert error" style=${{marginBottom:16}}>${error}</div>`}
      ${jobs===null && html`<div className="subtle">Loading…</div>`}
      ${jobs!==null&&jobs.length===0 && html`
        <div className="empty-state">
          <div className="empty-icon">▶</div>
          <div className="empty-msg">No active jobs</div>
          <div className="empty-sub">Running crawls and scans will appear here.</div>
        </div>`}
      ${jobs&&jobs.length>0 && html`
        <div className="table-wrap">
          <table>
            <colgroup>
              <col style=${{width:"18%"}}/><col style=${{width:"14%"}}/><col style=${{width:"14%"}}/><col style=${{width:"10%"}}/><col style=${{width:"10%"}}/><col style=${{width:"7%"}}/><col style=${{width:"13%"}}/><col style=${{width:"14%"}}/>
            </colgroup>
            <thead><tr><th>Run</th><th>Site</th><th>Job</th><th>Status</th><th>Progress</th><th>Findings</th><th>Started</th><th></th></tr></thead>
            <tbody>${jobs.map(j=>html`
              <tr key=${`${j.job_type}-${j.run_id}`}>
                <td>
                  <a href=${`#/runs/${j.run_id}`} style=${{fontWeight:600}}>${j.run_name}</a>
                  ${j.current_url && html`<div className="url" style=${{marginTop:3}}>${truncUrl(j.current_url, 54)}</div>`}
                </td>
                <td><a href=${`#/sites/${j.site_id}`}>${j.site_name}</a></td>
                <td>${j.job_type}</td>
                <td>${activeJobBadge(j)}</td>
                <td>${activeJobProgress(j)}</td>
                <td>${j.findings_count ?? html`<span className="subtle">—</span>`}</td>
                <td className="subtle">${fmtDate(j.started_at || j.created_at)}</td>
                <td>
                  <div className="row" style=${{justifyContent:"flex-end"}}>
                    <button className="btn secondary sm" onClick=${()=>nav(`#/runs/${j.run_id}`)}>Open</button>
                  </div>
                </td>
              </tr>`)}
            </tbody>
          </table>
        </div>`}
    </div>
  `;
}

// ── Site detail ───────────────────────────────────────────────────────────────

function SiteDetail({ siteId }) {
  const [site, setSite]   = useState(null);
  const [runs, setRuns]   = useState(null);
  const [error, setError] = useState(null);
  const [editingRun, setEditingRun]   = useState(null);   // run object being edited
  const [editForm, setEditForm]       = useState({});
  const [editProfiles, setEditProfiles] = useState([]);
  const [editSaving, setEditSaving]   = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, r, p] = await Promise.all([api.getSite(siteId), api.listRuns(siteId), api.listLLMProfiles()]);
      setSite(s); setRuns(r); setEditProfiles(p || []);
    } catch(e) { setError(e.message); }
  }, [siteId]);
  useEffect(() => { load(); }, [load]);

  const openEdit = (run) => {
    setEditForm({ max_depth: run.max_depth, max_pages: run.max_pages, llm_config_id: run.llm_config_id || "" });
    setEditingRun(run);
  };
  const saveEdit = async () => {
    setEditSaving(true);
    try {
      const updated = await api.updateRun(editingRun.id, {
        max_depth: Number(editForm.max_depth),
        max_pages: Number(editForm.max_pages),
        llm_config_id: editForm.llm_config_id ? Number(editForm.llm_config_id) : null,
      });
      setRuns(rs => rs.map(r => r.id === updated.id ? updated : r));
      setEditingRun(null);
    } catch(e) { setError(e.message); } finally { setEditSaving(false); }
  };

  const deleteRun = async (run) => {
    if (!confirm(`Delete run "${run.name}"?`)) return;
    try { await api.deleteRun(run.id); setRuns(r=>r.filter(x=>x.id!==run.id)); }
    catch(e) { setError(e.message); }
  };

  return html`
    <div className="topbar">
      <div className="topbar-title">
        <a href="#/" style=${{color:"var(--muted)",fontWeight:400}}>Sites</a>
        <span className="breadcrumb-sep"> / </span>
        ${site ? site.name : "…"}
      </div>
      <div className="topbar-actions">
        ${site && html`<button className="btn secondary" onClick=${()=>nav(`#/sites/${siteId}/edit`)}>Edit site</button>`}
        <button className="btn" onClick=${()=>nav(`#/sites/${siteId}/runs/new`)}><${IconPlus}/> New run</button>
      </div>
    </div>
    <div className="content scroll-content stack">
      ${error && html`<div className="alert error">${error}</div>`}

      ${editingRun && html`
        <div className="card" style=${{padding:"20px 24px", border:"1px solid var(--accent)", marginBottom:8}}>
          <div style=${{fontWeight:700, marginBottom:14}}>Edit run: ${editingRun.name}</div>
          <div className="two-col" style=${{gap:12, marginBottom:12}}>
            <div className="field" style=${{margin:0}}>
              <label>Max depth</label>
              <input type="number" min="1" max="10" value=${editForm.max_depth}
                onInput=${e=>setEditForm(f=>({...f, max_depth:e.target.value}))} style=${{width:80}}/>
            </div>
            <div className="field" style=${{margin:0}}>
              <label>Max pages</label>
              <input type="number" min="5" max="500" value=${editForm.max_pages}
                onInput=${e=>setEditForm(f=>({...f, max_pages:e.target.value}))} style=${{width:90}}/>
            </div>
          </div>
          <div className="field" style=${{marginBottom:14}}>
            <label>LLM profile <span className="field-optional">(leave blank to use the globally active profile)</span></label>
            <select className="select" value=${editForm.llm_config_id||""} onChange=${e=>setEditForm(f=>({...f, llm_config_id:e.target.value}))}>
              <option value="">— Use global active profile —</option>
              ${editProfiles.map(p=>html`<option key=${p.id} value=${p.id}>${p.name} (${p.provider} / ${p.model})</option>`)}
            </select>
          </div>
          <div className="row" style=${{gap:8}}>
            <button className="btn sm" onClick=${saveEdit} disabled=${editSaving}>${editSaving?"Saving…":"Save"}</button>
            <button className="btn ghost sm" onClick=${()=>setEditingRun(null)}>Cancel</button>
          </div>
        </div>`}

      ${site && html`
        <div className="card" style=${{padding:"16px 20px"}}>
          <div className="row spread">
            <div className="stack" style=${{gap:4}}>
              <div style=${{fontSize:13,color:"var(--muted)"}}>Base URL</div>
              <div className="mono" style=${{fontSize:13}}>${site.base_url}</div>
            </div>
            <div className="row" style=${{gap:16}}>
              ${site.requires_auth
                ? html`<span className="badge ok">auth required</span>`
                : html`<span className="badge neutral">no auth</span>`}
              <span className="subtle">${site.credentials.length} credential${site.credentials.length!==1?"s":""}</span>
            </div>
          </div>
          ${site.notes && html`<div style=${{marginTop:10,fontSize:13,color:"var(--muted)"}}>${site.notes}</div>`}
          ${site.requires_auth && site.credentials.length > 0 && html`
            <div className="site-credentials-list">
              ${site.credentials.map(c => html`
                <div key=${c.id} className="site-credential-row">
                  <div>
                    <div className="site-credential-name">${c.label || c.username}</div>
                    ${c.label && html`<div className="site-credential-user">${c.username}</div>`}
                  </div>
                  <div className="site-credential-login mono">
                    ${c.login_url || site.login_url || "No login URL"}
                  </div>
                </div>`)}
            </div>`}
        </div>`}

      <div>
        <div className="row spread" style=${{marginBottom:12}}>
          <div style=${{fontSize:13,fontWeight:700,color:"var(--muted)",textTransform:"uppercase",letterSpacing:"0.6px"}}>Test Runs</div>
        </div>
        ${runs===null && html`<div className="subtle">Loading…</div>`}
        ${runs!==null&&runs.length===0 && html`
          <div className="empty-state" style=${{padding:"32px"}}>
            <div className="empty-msg">No test runs yet</div>
            <div className="empty-sub">Create a new run to start crawling this site.</div>
            <button className="btn" onClick=${()=>nav(`#/sites/${siteId}/runs/new`)}><${IconPlus}/> New run</button>
          </div>`}
        ${runs&&runs.length>0 && html`
          <div className="table-wrap">
            <table>
              <colgroup>
                <col style=${{width:"35%"}}/><col style=${{width:"18%"}}/><col style=${{width:"10%"}}/><col style=${{width:"16%"}}/><col style=${{width:"21%"}}/>
              </colgroup>
              <thead><tr><th>Name</th><th>Status</th><th>Pages</th><th>Created</th><th></th></tr></thead>
              <tbody>${runs.map(r=>html`
                <tr key=${r.id}>
                  <td>
                    <strong>${r.name}</strong>
                    ${r.llm_config_id && html`<div style=${{fontSize:11,color:"var(--muted)",marginTop:2}}>${(editProfiles.find(p=>p.id===r.llm_config_id)||{name:"LLM #"+r.llm_config_id}).name}</div>`}
                  </td>
                  <td>${workflowBadge(r)}</td>
                  <td>${r.pages_discovered}</td>
                  <td className="subtle">${fmtDate(r.created_at)}</td>
                  <td>
                    <div className="row" style=${{justifyContent:"flex-end"}}>
                      <button className="btn secondary sm" onClick=${()=>nav(`#/runs/${r.id}`)}>Open</button>
                      <button className="btn secondary sm" onClick=${()=>openEdit(r)}>Edit</button>
                      <button className="btn danger-outline sm" onClick=${()=>deleteRun(r)}>Delete</button>
                    </div>
                  </td>
                </tr>`)}
              </tbody>
            </table>
          </div>`}
      </div>
    </div>
  `;
}

// ── Site form (create/edit) ───────────────────────────────────────────────────

function SiteForm({ siteId }) {
  const isEdit = typeof siteId === "number";
  const [form, setForm]       = useState({ name:"", base_url:"", requires_auth:false, login_url:"", notes:"", credentials:[] });
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState(null);

  useEffect(() => {
    if (!isEdit) return;
    (async () => {
      try {
        const d = await api.getSite(siteId);
        setForm({ name:d.name, base_url:d.base_url, requires_auth:d.requires_auth,
          login_url:d.login_url||"", notes:d.notes||"",
          credentials:d.credentials.map(c=>({username:c.username,password:c.password,label:c.label||"",login_url:c.login_url||""})) });
      } catch(e) { setError(e.message); } finally { setLoading(false); }
    })();
  }, [isEdit, siteId]);

  const upd = p => { setForm(f=>({...f,...p})); };
  const updC = (i,p) => setForm(f=>({...f,credentials:f.credentials.map((c,j)=>j===i?{...c,...p}:c)}));
  const addC = () => upd({ credentials:[...form.credentials,{username:"",password:"",label:"",login_url:""}] });
  const rmC  = i  => upd({ credentials:form.credentials.filter((_,j)=>j!==i) });

  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true);
    const payload = { name:form.name.trim(), base_url:form.base_url.trim(), requires_auth:form.requires_auth,
      login_url:form.requires_auth?(form.login_url.trim()||null):null, notes:form.notes.trim()||null,
      credentials:form.requires_auth?form.credentials.map(c=>({
        username:c.username,
        password:c.password,
        label:c.label||null,
        login_url:c.login_url?.trim()||null,
      })):[] };
    try {
      if (isEdit) { await api.updateSite(siteId,payload); nav(`#/sites/${siteId}`); }
      else        { const s = await api.createSite(payload); nav(`#/sites/${s.id}`); }
    } catch(e) { setError(e.message); } finally { setSaving(false); }
  };

  const bc = isEdit
    ? html`<a href=${`#/sites/${siteId}`} style=${{color:"var(--muted)",fontWeight:400}}>${form.name||"Site"}</a><span className="breadcrumb-sep"> / </span>Edit`
    : "New site";

  return html`
    <div className="topbar"><div className="topbar-title">${bc}</div></div>
    <div className="content scroll-content">
      ${loading && html`<div className="subtle">Loading…</div>`}
      ${!loading && html`
        <form className="card" onSubmit=${onSubmit}>
          ${error && html`<div className="alert error">${error}</div>`}
          <div className="form-section-title">Site</div>
          <div className="field"><label>Name</label>
            <input type="text" required value=${form.name} placeholder="e.g. Juice Shop" onChange=${e=>upd({name:e.target.value})}/></div>
          <div className="field"><label>Base URL</label>
            <input type="url" required value=${form.base_url} placeholder="https://target.example.com" onChange=${e=>upd({base_url:e.target.value})}/></div>
          <div className="field"><label>Notes (optional)</label>
            <textarea value=${form.notes} placeholder="Scope, contacts…" onChange=${e=>upd({notes:e.target.value})}/></div>
          <div className="divider"/>
          <div className="form-section-title">Authentication</div>
          <label className="toggle-row">
            <input type="checkbox" checked=${form.requires_auth} onChange=${e=>upd({requires_auth:e.target.checked})}/>
            <span>This site requires authentication</span>
          </label>
          ${form.requires_auth && html`
            <div className="field"><label>Default login page URL</label>
              <input type="url" value=${form.login_url} placeholder="https://target.example.com/login" onChange=${e=>upd({login_url:e.target.value})}/></div>
            <fieldset><legend>Credentials</legend>
              ${form.credentials.length===0&&html`<div className="subtle">No credentials yet.</div>`}
              ${form.credentials.map((c,i)=>html`
                <div className="cred-row" key=${i}>
                  <div className="field"><label>Username</label><input type="text" required value=${c.username} onChange=${e=>updC(i,{username:e.target.value})}/></div>
                  <div className="field"><label>Password</label><input type="text" required value=${c.password} onChange=${e=>updC(i,{password:e.target.value})}/></div>
                  <div className="field credential-login-field"><label>Login URL <span className="field-optional">(optional override)</span></label><input type="url" value=${c.login_url||""} placeholder=${form.login_url?`Uses default: ${form.login_url}`:"Required if no default login URL"} onChange=${e=>updC(i,{login_url:e.target.value})}/></div>
                  <div className="field"><label>Label</label><input type="text" value=${c.label} placeholder="admin" onChange=${e=>updC(i,{label:e.target.value})}/></div>
                  <div className="credential-remove-cell"><button type="button" className="btn ghost sm" onClick=${()=>rmC(i)}>Remove</button></div>
                </div>`)}
              <button type="button" className="btn secondary sm" onClick=${addC}><${IconPlus}/> Add credential</button>
            </fieldset>`}
          <div className="divider"/>
          <div className="row spread">
            <button type="button" className="btn ghost" onClick=${()=>isEdit?nav(`#/sites/${siteId}`):nav("#/")}>Cancel</button>
            <button type="submit" className="btn" disabled=${saving}>${saving?"Saving…":isEdit?"Save changes":"Create site"}</button>
          </div>
        </form>`}
    </div>`;
}

// ── Test run form ─────────────────────────────────────────────────────────────

function TestRunForm({ siteId }) {
  const [form, setForm] = useState({ name:"", max_depth:3, max_pages:50, llm_config_id:null });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const upd = p => setForm(f=>({...f,...p}));

  useEffect(() => {
    (async () => {
      try {
        const profs = await api.listLLMProfiles();
        setProfiles(profs || []);
      } catch(e) { setError(e.message); }
    })();
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true);
    try {
      const run = await api.createRun(siteId, {
        name: form.name.trim()||null,
        max_depth: Number(form.max_depth),
        max_pages: Number(form.max_pages),
        llm_config_id: form.llm_config_id || null,
      });
      nav(`#/runs/${run.id}`);
    } catch(e) { setError(e.message); setSaving(false); }
  };

  return html`
    <div className="topbar">
      <div className="topbar-title">
        <a href=${`#/sites/${siteId}`} style=${{color:"var(--muted)",fontWeight:400}}>Site</a>
        <span className="breadcrumb-sep"> / </span>New test run
      </div>
    </div>
    <div className="content scroll-content">
      <form className="card" onSubmit=${onSubmit}>
        ${error && html`<div className="alert error">${error}</div>`}
        <div className="form-section-title">Run Configuration</div>
        <div className="field">
          <label>Name <span className="field-optional">(optional — auto-generated if blank)</span></label>
          <input type="text" value=${form.name} placeholder="e.g. Initial crawl" onChange=${e=>upd({name:e.target.value})}/>
        </div>
        <div className="two-col">
          <div className="field">
            <label>Max depth <span className="field-hint-inline">(1–10)</span></label>
            <input type="number" required min="1" max="10" value=${form.max_depth} onChange=${e=>upd({max_depth:e.target.value})}/>
          </div>
          <div className="field">
            <label>Max pages <span className="field-hint-inline">(5–500)</span></label>
            <input type="number" required min="5" max="500" value=${form.max_pages} onChange=${e=>upd({max_pages:e.target.value})}/>
          </div>
        </div>
        <div className="alert" style=${{marginTop:12}}>
          This run will use the global scan policy from Settings.
        </div>
        <div className="divider"/>
        <div className="form-section-title">LLM Profile</div>
        <div className="field">
          <label>LLM profile <span className="field-optional">(optional — uses the globally active profile if not set)</span></label>
          <select className="select" value=${form.llm_config_id||""} onChange=${e=>upd({llm_config_id:e.target.value?Number(e.target.value):null})}>
            <option value="">— Use global active profile —</option>
            ${profiles.map(p=>html`<option key=${p.id} value=${p.id}>${p.name} (${p.provider} / ${p.model})</option>`)}
          </select>
        </div>
        <div className="row spread">
          <button type="button" className="btn ghost" onClick=${()=>nav(`#/sites/${siteId}`)}>Cancel</button>
          <button type="submit" className="btn" disabled=${saving}>${saving?"Creating…":"Create run"}</button>
        </div>
      </form>
    </div>`;
}

// ── Test run detail + D3 graph ────────────────────────────────────────────────

const SCOPE_IN_COLOR  = "#3b82f6";
const SCOPE_OUT_COLOR = "#ef4444";
const scopeColor = (d) => d.in_scope === false ? SCOPE_OUT_COLOR : SCOPE_IN_COLOR;

const DYNAMIC_SCAN_ACTIVE_STATUSES = ["running", "analysing", "stopping"];
const isDynamicScanActive = (status) => DYNAMIC_SCAN_ACTIVE_STATUSES.includes(status);

// Per-user palette (index into credentials array)
const USER_PALETTE = ["#f97316","#06b6d4","#a855f7","#f59e0b","#10b981","#ec4899"];
const USER_BOTH_COLOR = "#6366f1";   // accessible to all users
const USER_NONE_COLOR = "#6b7691";   // not tagged (pre-multi-user crawl)
const userColor = (d, credentials) => {
  const ab = d.accessible_by || [];
  if (!credentials || credentials.length === 0 || ab.length === 0) return USER_NONE_COLOR;
  if (ab.length >= credentials.length) return USER_BOTH_COLOR;
  const idx = credentials.findIndex(c => ab.includes(c.id));
  return idx >= 0 ? USER_PALETTE[idx % USER_PALETTE.length] : USER_NONE_COLOR;
};

function runWorkflowStatus(run, opts = {}) {
  if (!run) return { key:"pending", label:"pending" };
  const thinkingStatus = opts.thinkingStatus || run.thinking_status || "idle";
  if (opts.crawlStopping) return { key:"stopping", label:"stopping crawl" };
  if (opts.thinkingStopping || thinkingStatus === "stopping") return { key:"stopping", label:"stopping Dynamic Scan" };
  if (run.status === "running") return { key:"running", label:"crawling" };
  if (run.status === "failed") return { key:"danger", label:"crawl failed" };
  if (thinkingStatus === "running") return { key:"running", label:"Dynamic Scan" };
  if (thinkingStatus === "analysing") return { key:"running", label:"analysing Dynamic Scan" };
  if (thinkingStatus === "failed") return { key:"danger", label:"Dynamic Scan failed" };
  if (run.status === "stopped") return { key:"neutral", label:"crawl stopped" };
  if (thinkingStatus === "stopped") return { key:"neutral", label:"Dynamic Scan stopped" };
  if (thinkingStatus === "complete") return { key:"ok", label:"Dynamic Scan complete" };
  if (run.status === "complete") return { key:"ok", label:"complete" };
  return { key:"neutral", label:run.status || "pending" };
}

const workflowBadge = (run, opts = {}) => {
  const st = runWorkflowStatus(run, opts);
  return html`<span className=${"badge " + st.key}>${st.label}</span>`;
};

// ── Column resize hook ────────────────────────────────────────────────────────
function useColResize(storageKey, defaults) {
  const [widths, setWidths] = useState(() => {
    try { const s = localStorage.getItem(storageKey); if (s) return JSON.parse(s); } catch (_) {}
    return defaults;
  });
  const startResize = useCallback((idx, e) => {
    e.preventDefault(); e.stopPropagation();
    const startX = e.clientX;
    const th = e.currentTarget.closest("th");
    const startW = widths[idx] ?? (th ? th.offsetWidth : 100);
    const onMove = ev => {
      const newW = Math.max(36, startW + ev.clientX - startX);
      setWidths(prev => { const n = [...prev]; n[idx] = newW; return n; });
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      setWidths(prev => { try { localStorage.setItem(storageKey, JSON.stringify(prev)); } catch (_) {} return prev; });
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [storageKey, widths]);
  return [widths, startResize];
}

function TestRunDetail({ runId, initialTab }) {
  const [run, setRun]           = useState(null);
  const [siteName, setSiteName] = useState(null);
  const [graph, setGraph]       = useState(null);
  const [selectedNode, setSelNode] = useState(null);
  const [pageDetail, setPageDetail] = useState(null);
  const [pageViews, setPageViews]   = useState([]);
  const [cascade, setCascade]     = useState(false);
  const [scopeBusy, setScopeBusy] = useState(false);
  const [activeTab, setActiveTab] = useState(initialTab || "activity");
  const [scopeHosts, setScopeHosts] = useState([]);
  const [graphView, setGraphView]           = useState("scope");  // "scope" | "user"
  const [targetIntel, setTargetIntel]       = useState(null);
  const [targetIntelKind, setTargetIntelKind] = useState("");
  const [taskGraph, setTaskGraph]           = useState(null);
  const [reconSummary, setReconSummary]     = useState(null);
  const [tasksSubTab, setTasksSubTab]       = useState("attack-surface"); // "attack-surface" | "task-queue"
  const [scannerSessions, setScannerSessions] = useState(null);
  const [crawlUsername, setCrawlUsername]   = useState(null);
  const [clearBusy, setClearBusy]           = useState(""); // which section is clearing
  const [clearError, setClearError]         = useState(null);
  // per-user crawl progress is read directly from run.per_user_progress (kept in sync
  // by the periodic poll + SSE run_update events) — no separate state needed.
  const [editingSettings, setEditingSettings] = useState(false);
  const [editDepth, setEditDepth] = useState("");
  const [editPages, setEditPages] = useState("");
  const [editLlmProfileId, setEditLlmProfileId] = useState(null);
  const [runProfiles, setRunProfiles] = useState([]);

  // Load LLM profiles once so the read-only display and edit dropdown both work.
  useEffect(() => { api.listLLMProfiles().then(setRunProfiles).catch(()=>{}); }, []);
  const [activityLog, setActivityLog]       = useState([]);
  const [expandedLogIds, setExpandedLogIds]  = useState(new Set());
  const toggleLogId = (id) => setExpandedLogIds(prev => {
    const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next;
  });
  const [activitySubTab, setActivitySubTab] = useState("agents");
  const [agents, setAgents]                = useState([]);
  const [collapsedAgentIds, setCollapsedAgentIds] = useState(new Set());
  const toggleAgentId = (aid) => setCollapsedAgentIds(prev => {
    const next = new Set(prev); next.has(aid) ? next.delete(aid) : next.add(aid); return next;
  });

  const _aliceDefaultChats = () => [{
    id: "tab-default",
    title: "Session 1",
    messages: [{
      id: "welcome",
      sender: "alice",
      type: "message",
      text: "Hello! I am A.L.I.C.E., your interactive pentesting partner. How can I assist you with this scan?",
      ts: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
    }]
  }];

  const [aliceChats, setAliceChats] = useState(() => {
    // Seed from localStorage for instant display; server load will overwrite below.
    try {
      const saved = localStorage.getItem(`alice_chats_${runId}`);
      if (saved) return JSON.parse(saved);
    } catch (_) {}
    return _aliceDefaultChats();
  });
  const [activeAliceTabId, setActiveAliceTabId] = useState(() => {
    try {
      const saved = localStorage.getItem(`alice_active_tab_${runId}`);
      if (saved) return saved;
    } catch (_) {}
    return "tab-default";
  });

  // Load sessions from the server on mount.
  // Strategy: use whichever source is more recent.
  //   - Local is newer  → page-refresh by the same user; keep local (it has the
  //     latest streaming content) and apply the recovery key on top.
  //   - Server is newer → a different user opened the scan, or another browser
  //     tab saved after this one last wrote; accept the server state.
  useEffect(() => {
    api.getAliceSessions(runId).then(data => {
      if (!data.chats || data.chats.length === 0) return;

      const serverUpdatedAt = data.updated_at ? new Date(data.updated_at).getTime() : 0;
      const localSavedAt = parseInt(
        localStorage.getItem(`alice_chats_${runId}_savedAt`) || "0", 10
      );
      const activeTabId = data.active_tab_id || "tab-default";

      // Helper: patch messages with the latest recovery-key text.
      const applyRecovery = (chats, tabId) => {
        try {
          const rec = JSON.parse(
            localStorage.getItem(`alice_recover_${runId}:${tabId}`) || "null"
          );
          if (!rec || !rec.thinkMsgId) return chats;
          return chats.map(tab => {
            if (tab.id !== tabId) return tab;
            return {
              ...tab,
              messages: tab.messages.map(m => {
                if (m.id === rec.thinkMsgId && rec.thought) return { ...m, text: rec.thought };
                if (m.id === rec.replyMsgId && rec.message) return { ...m, text: rec.message };
                return m;
              }),
            };
          });
        } catch (_) { return chats; }
      };

      if (serverUpdatedAt > localSavedAt) {
        // Server has newer state (another user/tab made changes).
        const merged = applyRecovery(data.chats, activeTabId);
        setAliceChats(merged);
        setActiveAliceTabId(activeTabId);
        try {
          localStorage.setItem(`alice_chats_${runId}`, JSON.stringify(merged));
          localStorage.setItem(`alice_active_tab_${runId}`, activeTabId);
          localStorage.setItem(`alice_chats_${runId}_savedAt`, serverUpdatedAt.toString());
        } catch (_) {}
      }
      // else: local is fresher (page refresh mid-stream) — keep it as-is;
      // the recovery useEffect below will patch the latest text.
    }).catch(() => {});
  }, [runId]);

  const [aliceInputText, setAliceInputText] = useState("");
  const [aliceChatHeight, setAliceChatHeight] = useState(300);
  const [aliceIsThinking, setAliceIsThinking] = useState(false);
  const [aliceGlobalRunning, setAliceGlobalRunning] = useState(false);
  const [aliceExpandedThinkIds, setAliceExpandedThinkIds] = useState(new Set());

  // On mount: check whether a background ALICE task is already running (e.g.
  // after a page refresh) and reconnect to its event stream if so.
  useEffect(() => {
    let cancelled = false;
    api.getAliceStatus(runId).then(st => {
      if (cancelled || !st.running) return;
      const { tab_id, think_msg_id, reply_msg_id } = st;
      setAliceGlobalRunning(true);
      setAliceIsThinking(true);
      setAliceExpandedThinkIds(prev => { const s = new Set(prev); s.add(think_msg_id); return s; });
      // Pre-populate session so the subscriber can find the right messages.
      const sess = getAliceSession(runId, tab_id);
      sess.thinkMsgId = think_msg_id;
      sess.replyMsgId = reply_msg_id;
      const done = () => { setAliceIsThinking(false); setAliceGlobalRunning(false); };
      aliceSessionConnect(runId, tab_id, {
        thinkMsgId: think_msg_id,
        replyMsgId: reply_msg_id,
        cursor: 0,
        onFinish: done,
        onFail: done,
      });
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [runId]);
  // Subscribe to in-flight stream on mount/tab-switch so navigating back
  // shows the spinner and receives live chunks from the singleton reader loop.
  useEffect(() => {
    const session = getAliceSession(runId, activeAliceTabId);
    if (session.active) {
      setAliceIsThinking(true);
    }

    // Resolve the best available accumulated text: prefer the in-memory session
    // (same page load), fall back to the localStorage recovery key written
    // directly by aliceSessionStart (survives navigation + module resets).
    let recThinkId = session.thinkMsgId;
    let recReplyId = session.replyMsgId;
    let recThought = session.accumulatedThought;
    let recMessage = session.accumulatedMessage;

    if (!recThinkId || (!recThought && !recMessage)) {
      try {
        const saved = JSON.parse(
          localStorage.getItem(`alice_recover_${runId}:${activeAliceTabId}`) || "null"
        );
        if (saved && saved.thinkMsgId) {
          recThinkId  = recThinkId  || saved.thinkMsgId;
          recReplyId  = recReplyId  || saved.replyMsgId;
          recThought  = recThought  || saved.thought;
          recMessage  = recMessage  || saved.message;
        }
      } catch (_) {}
    }

    if (recThinkId && (recThought || recMessage)) {
      setAliceChats(prev => prev.map(tab => {
        if (tab.id !== activeAliceTabId) return tab;
        return {
          ...tab,
          messages: tab.messages.map(m => {
            if (m.id === recThinkId && recThought) return { ...m, text: recThought };
            if (m.id === recReplyId && recMessage)  return { ...m, text: recMessage };
            return m;
          })
        };
      }));
      // Auto-expand the thinking bubble so recovered progress is visible
      if (recThinkId) {
        setAliceExpandedThinkIds(prev => { const s = new Set(prev); s.add(recThinkId); return s; });
      }
    }

    const unsub = aliceSessionSubscribe(runId, activeAliceTabId, {
      onChunk: (event) => {
        const { thinkMsgId, replyMsgId } = session;
        // Use session's running totals (not m.text + delta) so every render
        // sees the complete accumulated text — identical to the catch-up sync
        // on navigation-back, which ensures blocks parse and render graphically
        // rather than as an in-progress incremental string.
        setAliceChats(prev => prev.map(tab => {
          if (tab.id !== activeAliceTabId) return tab;
          return {
            ...tab,
            messages: tab.messages.map(m => {
              if (event.type === "thinking_chunk" && m.id === thinkMsgId)
                return { ...m, text: session.accumulatedThought };
              if (event.type === "message_chunk" && m.id === replyMsgId)
                return { ...m, text: session.accumulatedMessage };
              if (event.type === "warning" && m.id === replyMsgId)
                return { ...m, text: event.message };
              if (event.type === "done") {
                if (m.id === thinkMsgId && event.thought) return { ...m, text: event.thought };
                if (m.id === replyMsgId && event.message) return { ...m, text: event.message };
              }
              return m;
            })
          };
        }));
      },
      onDone: () => { setAliceIsThinking(false); setAliceGlobalRunning(false); },
      onError: () => { setAliceIsThinking(false); setAliceGlobalRunning(false); },
    });
    return unsub;
  }, [runId, activeAliceTabId]);

  const _aliceSaveTimer = useRef(null);
  useEffect(() => {
    // Keep localStorage in sync for fast initial render on next mount.
    // savedAt lets the server-load effect decide which source is fresher.
    const now = Date.now();
    try {
      localStorage.setItem(`alice_chats_${runId}`, JSON.stringify(aliceChats));
      localStorage.setItem(`alice_active_tab_${runId}`, activeAliceTabId);
      localStorage.setItem(`alice_chats_${runId}_savedAt`, now.toString());
    } catch (_) {}
    // Debounce server save so rapid streaming chunks don't hammer the API.
    if (_aliceSaveTimer.current) clearTimeout(_aliceSaveTimer.current);
    _aliceSaveTimer.current = setTimeout(() => {
      api.saveAliceSessions(runId, { chats: aliceChats, active_tab_id: activeAliceTabId })
        .catch(() => {});
    }, 800);
  }, [aliceChats, activeAliceTabId, runId]);

  const activeAliceTab = aliceChats.find(t => t.id === activeAliceTabId) || aliceChats[0];
  const aliceMessages = activeAliceTab ? activeAliceTab.messages : [];

  const createAliceTab = () => {
    const newTabId = "tab-" + Date.now().toString();
    const newTab = {
      id: newTabId,
      title: `Session ${aliceChats.length + 1}`,
      messages: [
        {
          id: "welcome-" + newTabId,
          sender: "alice",
          type: "message",
          text: "Hello! I am A.L.I.C.E., your interactive pentesting partner. How can I assist you with this scan?",
          ts: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
        }
      ]
    };
    setAliceChats(prev => [...prev, newTab]);
    setActiveAliceTabId(newTabId);
  };

  const deleteAliceTab = (tabId, e) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    if (aliceChats.length <= 1) {
      const resetTab = {
        id: "tab-default",
        title: "Session 1",
        messages: [
          {
            id: "welcome-reset",
            sender: "alice",
            type: "message",
            text: "Hello! I am A.L.I.C.E., your interactive pentesting partner. How can I assist you with this scan?",
            ts: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
          }
        ]
      };
      setAliceChats([resetTab]);
      setActiveAliceTabId("tab-default");
      return;
    }

    const index = aliceChats.findIndex(t => t.id === tabId);
    if (index === -1) return;

    const remainingChats = aliceChats.filter(t => t.id !== tabId);
    setAliceChats(remainingChats);

    if (activeAliceTabId === tabId) {
      const nextActiveIndex = Math.max(0, index - 1);
      setActiveAliceTabId(remainingChats[nextActiveIndex].id);
    }
  };

  const startAliceResize = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    const startY = e.clientY;
    const startH = aliceChatHeight;
    const onMove = ev => {
      const newH = Math.max(150, Math.min(800, startH + (ev.clientY - startY)));
      setAliceChatHeight(newH);
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [aliceChatHeight]);

  const handleAliceStop = () => {
    aliceSessionAbort(runId, activeAliceTabId);
    api.stopAliceRun(runId).catch(() => {});
    setAliceIsThinking(false);
    setAliceGlobalRunning(false);
  };

  const handleAliceSend = async () => {
    if (!aliceInputText.trim() || aliceIsThinking) return;
    const userText = aliceInputText;
    setAliceInputText("");
    const currentTabId = activeAliceTabId;

    const userMsg = {
      id: Date.now().toString(),
      sender: "user",
      type: "message",
      text: userText,
      ts: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
    };

    const thinkMsgId = (Date.now() + 1).toString();
    const replyMsgId = (Date.now() + 2).toString();

    const thinkMsg = {
      id: thinkMsgId,
      sender: "alice",
      type: "thinking",
      text: "",
      ts: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
    };

    const replyMsg = {
      id: replyMsgId,
      sender: "alice",
      type: "message",
      text: "",
      ts: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
    };

    setAliceChats(prev => prev.map(tab => {
      if (tab.id === activeAliceTabId) {
        const isFirstPrompt = tab.messages.length <= 1;
        let newTitle = tab.title;
        if (isFirstPrompt) {
          const truncated = userText.trim().slice(0, 16);
          newTitle = truncated + (userText.trim().length > 16 ? "..." : "");
        }
        return {
          ...tab,
          title: newTitle,
          messages: [...tab.messages, userMsg, thinkMsg, replyMsg]
        };
      }
      return tab;
    }));
    setAliceIsThinking(true);
    setAliceGlobalRunning(true);

    setAliceExpandedThinkIds(prev => {
      const next = new Set(prev);
      next.add(thinkMsgId);
      return next;
    });

    const historyPayload = aliceMessages.map(m => ({
      sender: m.sender,
      text: m.text
    }));

    // Delegate all I/O to the module-level singleton so the stream survives
    // component unmounts caused by hash navigation.
    // State updates are handled by the useEffect subscriber above.
    aliceSessionStart(runId, currentTabId, {
      userText,
      historyPayload,
      thinkMsgId,
      replyMsgId,
      onFinish: () => { setAliceIsThinking(false); setAliceGlobalRunning(false); },
      onFail: (err) => {
        if (err.name === "AbortError") {
          setAliceChats(prev => prev.map(tab => {
            if (tab.id !== currentTabId) return tab;
            return {
              ...tab,
              messages: tab.messages.map(m => {
                if (m.id === thinkMsgId && !m.text) return { ...m, text: "[Generation Aborted]" };
                if (m.id === replyMsgId && !m.text) return { ...m, text: "Generation stopped by user." };
                return m;
              })
            };
          }));
        } else {
          setAliceChats(prev => prev.map(tab => {
            if (tab.id !== currentTabId) return tab;
            return {
              ...tab,
              messages: tab.messages.map(m =>
                m.id === replyMsgId
                  ? { ...m, text: `I encountered an error connecting to the agent: ${err.message}` }
                  : m
              )
            };
          }));
        }
        setAliceIsThinking(false);
        setAliceGlobalRunning(false);
      },
    });
  };


  const [tokenUsage, setTokenUsage] = useState(null);   // {total_input, total_output, by_model}
  const [tokenExpanded, setTokenExpanded] = useState(false);
  const [sitePlanData, setSitePlanData]     = useState(null);
  const activityFeedRef                     = useRef(null);
  const [crawlStopRequested, setCrawlStopRequested] = useState(false);
  const [thinkingStatus, setThinkingStatus]         = useState(null);
  const [thinkingStopRequested, setThinkingStopReq] = useState(false);
  const [checkpointStatus, setCheckpointStatus]     = useState(null);
  const [validateStatus, setValidateStatus] = useState(null);
  const [validateBusy, setValidateBusy]     = useState(false);
  const [dedupeBusy, setDedupeBusy]         = useState(false);
  const [findings, setFindings]             = useState([]);
  const [expandedFinding, setExpandedFinding] = useState(null);
  const [expandedGroups, setExpandedGroups]   = useState(new Set(["__unconfirmed__"]));
  const toggleGroup = (title) => setExpandedGroups(prev => {
    const next = new Set(prev);
    next.has(title) ? next.delete(title) : next.add(title);
    return next;
  });
  const [traffic, setTraffic]               = useState([]);
  const [selectedTraffic, setSelectedTraffic] = useState(null);
  const [trafficFilter, setTrafficFilter]   = useState("");
  const [autoScroll, setAutoScroll]         = useState(true);
  const [trafficTotal, setTrafficTotal]     = useState(0);
  const [trafficSort, setTrafficSort]       = useState({ field: "_seq", dir: "asc" });
  const lastTrafficIdRef                    = useRef(0);
  const trafficTableRef                     = useRef(null);
  const issueImportInputRef                 = useRef(null);
  const [error, setError]       = useState(null);
  const svgRef                  = useRef(null);
  const simRef                  = useRef(null);
  const prevGraphKeyRef                     = useRef("");
  const lastRunPollOkRef                    = useRef(Date.now());

  const [findColW,    startFindResize]    = useColResize("colw:findings", [80, 52, null, 28, 60]);
  const [trafficColW, startTrafficResize] = useColResize("colw:traffic",  [40, 70, 80, 90, 60, 54, null, 70]);

  // Initial load
  const loadAll = useCallback(async () => {
    try {
      const [r, g] = await Promise.all([api.getRun(runId), api.getGraph(runId)]);
      setRun(r); setGraph(g);
      if (r?.scope_hosts) setScopeHosts(r.scope_hosts);
      api.getThinkingStatus(runId).then(setThinkingStatus).catch(()=>{});
      api.getCheckpointStatus(runId).then(setCheckpointStatus).catch(()=>{});
      api.getSite(r.site_id).then(s => setSiteName(s.name)).catch(()=>{});
    } catch(e) { setError(e.message); }
  }, [runId]);
  useEffect(() => { loadAll(); }, [loadAll]);

  const agentRoleLabel = (agent) => {
    if (agent?.id === "crawler") return "Crawler";
    if (agent?.id === "scanner") return "Test Lead";
    if (agent?.id === "alice") return "A.L.I.C.E";
    return agent?.role || "Agent";
  };
  const normalizeAgentForRun = (agent) => {
    if (agent?.id !== "crawler") return agent;
    if (run?.status === "running") return { ...agent, status: "active" };
    if (Date.now() - lastRunPollOkRef.current > 10000) {
      return { ...agent, status: "idle", currentTask: "Crawler connection stale" };
    }
    return {
      ...agent,
      status: agent.status === "failed" ? "failed" : "idle",
      currentTask: agent.currentTask || "Crawl is not running",
    };
  };
  const defaultAgentRoster = () => [
    {
      id: "alice",
      role: "A.L.I.C.E",
      status: aliceIsThinking ? "active" : "idle",
      currentTask: aliceIsThinking ? "Processing directive..." : "Waiting for instruction",
    },
    {
      id: "crawler",
      role: "Crawler",
      status: run?.status === "running" ? "active" : "idle",
      currentTask: run?.status === "running" ? "" : "Waiting for crawl",
    },
    {
      id: "scanner",
      role: "Test Lead",
      status: isDynamicScanActive(thinkingStatus?.status) ? "active" : "idle",
      currentTask: isDynamicScanActive(thinkingStatus?.status) ? "Coordinating pentest" : "Standing by",
    },
    { id: "specialist", role: "Specialist", status: "idle", currentTask: "No specialist dispatched" },
    { id: "burp", role: "Burp", status: "idle", currentTask: "No active scan dispatched" },
    { id: "validator", role: "Validator", status: "idle", currentTask: "No validation running" },
    {
      id: "reporting",
      role: "Reporting",
      status: thinkingStatus?.status === "analysing" ? "active" : "idle",
      currentTask: thinkingStatus?.status === "analysing" ? "Analysing probe results…" : "Standing by",
    },
  ];

  const representsAgent = (agent, placeholder) => {
    if (agent.id === placeholder.id) return true;
    if (placeholder.id === "burp") return agent.role === "Burp" || agent.id?.startsWith("burp-");
    if (placeholder.id === "validator") return agent.role === "Validator" || agent.id?.startsWith("validator-");
    if (placeholder.id === "specialist") return agent.role === "Specialist" || agent.id?.startsWith("specialist-");
    if (placeholder.id === "reporting") return agent.role === "Reporting" || agent.id === "reporting";
    return false;
  };
  const fmtEventTime = (value) => {
    if (!value) return "--:--:--";
    try {
      return parseDate(value).toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return "--:--:--";
    }
  };
  const crawlEventsFromRun = () => {
    const progress = run?.per_user_progress || {};
    const labelByUsername = new Map((run?.credentials || []).map(c => [c.username, c.label || c.username]));
    return Object.entries(progress)
      .filter(([, p]) => p && (p.current_url || p.done || p.pages_visited))
      .map(([username, p]) => ({
        ts: fmtEventTime(p.updated_at),
        username: labelByUsername.get(username) || username || "anonymous",
        url: p.current_url || "",
        pagesVisited: p.pages_visited || 0,
        done: !!p.done,
      }));
  };
  const mergeCrawlEvents = (liveEvents, threadEvents) => {
    const seen = new Set();
    return [...(liveEvents || []), ...threadEvents]
      .filter((event) => {
        const key = `${event.username || ""}:${event.url || ""}:${event.pagesVisited || 0}:${event.done ? 1 : 0}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
  };
  const agentCrawlEvents = (agent) => (
    agent?.id === "crawler"
      ? mergeCrawlEvents(agent.crawlEvents || [], crawlEventsFromRun())
      : []
  );
  const compactAgentText = (value, max=180) => {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    return text.length > max ? text.slice(0, max - 1) + "…" : text;
  };
  const thinkingStepTitle = (entry) => {
    const step = entry.data?.step;
    const prefix = step ? `Step ${step}` : "Step";
    const message = String(entry.message || "").replace(/^Step\s+\d+:\s*/i, "").trim();
    const isDuplicateStep = (value) => (
      !value || /^Step\s+\d+$/i.test(String(value).trim())
    );
    let detail = (
      entry.data?.payload_purpose ||
      entry.data?.hypothesis ||
      entry.data?.observation ||
      entry.data?.payload_summary ||
      message
    );
    if (isDuplicateStep(detail)) {
      if (entry.data?.tool) {
        detail = `Context tool: ${entry.data.tool}`;
      } else if (entry.data?.method && entry.data?.url) {
        detail = `${entry.data.method} ${truncUrl(entry.data.url, 110)}${entry.data.status !== undefined ? ` → ${entry.data.status}` : ""}`;
      } else if (message && !isDuplicateStep(message)) {
        detail = message;
      } else if (entry.status === "deciding") {
        detail = "LLM deciding next action";
      } else {
        detail = "Reviewing scan state";
      }
    }
    const cleaned = compactAgentText(detail || "Reviewing next action");
    return `${prefix}: ${cleaned}`;
  };
  const thinkingStepOutcome = (entry) => {
    const parts = [];
    if (entry.data?.tool) parts.push(`Tool: ${entry.data.tool}`);
    if (entry.data?.method && entry.data?.url) parts.push(`${entry.data.method}: ${truncUrl(entry.data.url, 120)}`);
    if (entry.data?.observation) parts.push(`Observed: ${compactAgentText(entry.data.observation, 140)}`);
    if (entry.data?.hypothesis) parts.push(`Hypothesis: ${compactAgentText(entry.data.hypothesis, 140)}`);
    if (entry.data?.payload_purpose) parts.push(`Purpose: ${compactAgentText(entry.data.payload_purpose, 140)}`);
    if (entry.data?.payload_summary) parts.push(`Payload: ${compactAgentText(entry.data.payload_summary, 120)}`);
    if (entry.data?.status !== undefined) parts.push(`Status: ${entry.data.status}`);
    return parts.join(" · ");
  };
  const testLeadHistory = () => activityLog
    .filter(entry => entry.phase === "thinking_step")
    .map(entry => ({
      ts: entry._ts || "--:--:--",
      task: thinkingStepTitle(entry),
      outcome: thinkingStepOutcome(entry),
    }));
  const agentTaskHistory = (agent) => (
    agent?.id === "scanner" && testLeadHistory().length
      ? testLeadHistory()
      : (agent?.taskHistory || [])
  );
  const agentCurrentTask = (agent) => {
    agent = normalizeAgentForRun(agent);
    const crawlEvents = agentCrawlEvents(agent);
    if (agent?.id === "crawler" && crawlEvents.length) {
      if (agent.status !== "active") {
        const label = run?.status === "failed" ? "Crawl failed" :
          run?.status === "stopped" ? "Crawl stopped" :
          run?.status === "complete" ? "Crawl complete" :
          "Crawl is not running";
        return agent.outcome ? `${label} · ${agent.outcome}` : label;
      }
      const active = [...crawlEvents].reverse().find(h => !h.done && h.url);
      const latest = active || crawlEvents[crawlEvents.length - 1];
      if (latest.done) return `Completed crawl as ${latest.username || "anonymous"} (${latest.pagesVisited || 0} pg)`;
      return `Crawling ${truncUrl(latest.url || "", 88)} as ${latest.username || "anonymous"}`;
    }
    if (agent?.id === "scanner" && testLeadHistory().length) {
      if (agent.status !== "active") return "Standing by";
      return testLeadHistory()[testLeadHistory().length - 1].task;
    }
    return agent?.currentTask || "Waiting for work";
  };
  const agentStatusLabel = (agent) => {
    if (agent?.status === "active") return "ACTIVE";
    if (agent?.status === "idle") return "IDLE";
    if (agent?.status === "failed") return "FAILED";
    return "COMPLETE";
  };
  const upsertAgent = (items, patch, histEntry = null) => {
    const normalized = {
      ...patch,
      role: patch.id === "crawler" ? "Crawler" : patch.id === "scanner" ? "Test Lead" : patch.role,
    };
    const idx = items.findIndex(a => a.id === normalized.id);
    if (idx === -1) {
      return [...items, {
        ...normalized,
        taskHistory: histEntry ? [histEntry] : [],
        crawlEvents: normalized.crawlEvents || [],
      }];
    }
    const updated = [...items];
    const prev = updated[idx];
    updated[idx] = {
      ...prev,
      ...normalized,
      taskHistory: histEntry ? [...(prev.taskHistory || []), histEntry].slice(-200) : (prev.taskHistory || []),
      crawlEvents: normalized.crawlEvents || prev.crawlEvents || [],
    };
    return updated;
  };

  // Seed activity log from persisted DB entries on mount so it survives navigation.
  useEffect(() => {
    api.getScanLog(runId).then(entries => {
      if (!entries || entries.length === 0) return;
      setActivityLog(
        entries.map(e => {
          const ts = e._persisted_at
            ? parseDate(e._persisted_at).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })
            : "--:--:--";
          return { ...e, _ts: ts, _id: "db-" + e._persisted_at + "-" + e.phase + "-" + e.status };
        })
      );
      // Restore site plan data from persisted log.
      const planComplete = entries.find(e => e.phase === "site_plan" && e.status === "complete" && e.data);
      if (planComplete) setSitePlanData(planComplete.data);
    }).catch(() => {});
  }, [runId]);

  // Seed agents panel from persisted DB entries on mount.
  // Also fetches the live scan status so stale "active" agents left by a
  // force-killed process are reconciled back to "idle" immediately.
  useEffect(() => {
    Promise.all([api.getAgentLog(runId), api.getThinkingStatus(runId)])
      .then(([entries, scanStatus]) => {
        if (!entries || entries.length === 0) return;
        const scanRunning = isDynamicScanActive(scanStatus?.status);
        const agentsMap = new Map();
        for (const e of entries) {
          const entryTs = e.created_at
            ? parseDate(e.created_at).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })
            : "--:--:--";
          const role = e.agent_id === "crawler" ? "Crawler" : e.agent_id === "scanner" ? "Test Lead" : e.role;
          const existing = agentsMap.get(e.agent_id) || { id: e.agent_id, role, status: e.status, currentTask: e.current_task, taskHistory: [], crawlEvents: [] };
          existing.status = e.status;
          existing.role = role;
          existing.currentTask = e.current_task;
          existing.taskHistory.push({ ts: entryTs, task: e.current_task, outcome: e.outcome });
          agentsMap.set(e.agent_id, existing);
        }
        // If no scan is running, reset any stale "active" agents to "idle".
        if (!scanRunning) {
          for (const [id, agent] of agentsMap) {
            if (agent.status === "active" && id !== "crawler") {
              agentsMap.set(id, { ...agent, status: "idle" });
            }
          }
        }
        setAgents([...agentsMap.values()]);
      }).catch(() => {});
  }, [runId]);

  // Load token usage from the API on mount (in-process memory, best effort).
  useEffect(() => {
    api.getTokenUsage(runId).then(d => { if (d) setTokenUsage(d); }).catch(() => {});
  }, [runId]);

  // SSE: receive incremental graph + status updates — no graph polling needed
  useEffect(() => {
    const es = new EventSource(`/api/test-runs/${runId}/events`);
    es.onmessage = (msg) => {
      let evt;
      try { evt = JSON.parse(msg.data); } catch { return; }

      if (evt.type === "page_added") {
        setGraph(prev => {
          if (!prev) return prev;
          const exists = prev.nodes.some(n => n.id === evt.node.id);
          if (exists) return prev;
          const node = { ...evt.node, accessible_by: evt.node.accessible_by || [] };
          const newLinks = evt.link ? [...prev.links, evt.link] : prev.links;
          return { nodes: [...prev.nodes, node], links: newLinks };
        });
      } else if (evt.type === "crawl_phase") {
        setCrawlUsername(evt.username || null);
      } else if (evt.type === "node_accessible_by") {
        api.getGraph(runId).then(setGraph).catch(()=>{});
      } else if (evt.type === "run_update") {
        setRun(prev => prev ? { ...prev, status: evt.status ?? prev.status, pages_discovered: evt.pages_discovered ?? prev.pages_discovered } : prev);
        if (evt.status && evt.status !== "running") setCrawlStopRequested(false);
        if (evt.username !== undefined) setCrawlUsername(evt.username || null);
      } else if (evt.type === "crawl_progress") {
        const ts = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
        setAgents(prev => {
          const username = evt.username || "anonymous";
          const crawlEvent = {
            ts,
            username,
            url: evt.current_url || "",
            pagesVisited: evt.pages_visited || 0,
            done: !!evt.done,
          };
          const idx = prev.findIndex(a => a.id === "crawler");
          const existingEvents = idx >= 0 ? (prev[idx].crawlEvents || []) : [];
          const crawlEvents = [...existingEvents, crawlEvent].slice(-200);
          const currentTask = evt.done
            ? `Completed crawl as ${username} (${evt.pages_visited || 0} pg)`
            : `Crawling ${truncUrl(evt.current_url || "", 88)} as ${username}`;
          return upsertAgent(prev, {
            id: "crawler",
            role: "Crawler",
            status: "active",
            currentTask,
            crawlEvents,
          });
        });
        // crawl_progress is still used for the done flag
        if (evt.username && evt.done) {
          setRun(prev => {
            if (!prev) return prev;
            const pup = { ...(prev.per_user_progress || {}) };
            pup[evt.username] = { ...pup[evt.username], done: true };
            return { ...prev, per_user_progress: pup };
          });
        }
      } else if (evt.type === "node_scan_status") {
        setGraph(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            nodes: prev.nodes.map(n =>
              n.id === evt.page_id ? { ...n, scan_status: evt.scan_status } : n
            ),
          };
        });
      } else if (evt.type === "thinking_scan_update") {
        setThinkingStatus(evt);
        if (evt.status && !isDynamicScanActive(evt.status)) setThinkingStopReq(false);
      } else if (evt.type === "scanner_phase") {
        setActivityLog(prev => {
          const ts = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
          const entry = { ...evt, _ts: ts, _id: Date.now() + Math.random() };
          const next = [...prev, entry];
          return next.length > 500 ? next.slice(-500) : next;
        });
        if (evt.phase === "site_plan" && evt.status === "complete" && evt.data) {
          setSitePlanData(evt.data);
        }
      } else if (evt.type === "task_graph_update") {
        api.getTaskGraph(runId).then(setTaskGraph).catch(() => {});
      } else if (evt.type === "finding_validation_update") {
        setFindings(prev => prev.map(f =>
          f.id === evt.finding_id
            ? {
                ...f,
                validation_status: evt.validation_status,
                validation_note: evt.validation_note ?? f.validation_note,
                evidence_json: evt.evidence_json ?? f.evidence_json,
                evidence_items: evt.evidence_items ?? f.evidence_items,
              }
            : f
        ));
        // Refresh validation status summary when an individual finding resolves.
        api.getValidateStatus(runId).then(setValidateStatus).catch(() => {});
      } else if (evt.type === "agent_status") {
        const ts = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
        setAgents(prev => {
          const histEntry = { ts, task: evt.current_task, outcome: evt.outcome };
          return upsertAgent(prev, {
            id: evt.agent_id,
            role: evt.role,
            status: evt.status,
            currentTask: evt.current_task,
            outcome: evt.outcome,
          }, histEntry);
        });
      } else if (evt.type === "specialist_step") {
        const ts = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
        const agentId = evt.agent_id;
        if (agentId) {
          setAgents(prev => {
            const idx = prev.findIndex(a => a.id === agentId);
            const stepEntry = { ts, step: evt.step, action_type: evt.action_type, method: evt.method, url: evt.url, status: evt.status, observation: evt.observation };
            if (idx === -1) return prev;
            const updated = [...prev];
            const prev_agent = updated[idx];
            updated[idx] = {
              ...prev_agent,
              stepHistory: [...(prev_agent.stepHistory || []), stepEntry].slice(-200),
            };
            return updated;
          });
        }
      } else if (evt.type === "token_usage_update") {
        setTokenUsage(evt.totals);
      } else if (evt.type === "scope_hosts_updated") {
        setScopeHosts(evt.scope_hosts || []);
      }
    };
    es.onerror = () => { /* auto-reconnects */ };
    return () => es.close();
  }, [runId]);

  // Poll run metadata (including per_user_progress current URLs) while crawling
  // or while the backend is unwinding after a stop request.
  useEffect(() => {
    if (run?.status !== "running" && !crawlStopRequested) return;
    const iv = setInterval(() => {
      api.getRun(runId).then(r => {
        lastRunPollOkRef.current = Date.now();
        setRun(r);
        if (r.status !== "running") {
          setAgents(prev => prev.map(a => (
            a.id === "crawler" && a.status === "active"
              ? { ...a, status: "idle", currentTask: "Crawl is not running" }
              : a
          )));
        }
        if (crawlStopRequested && r.completed_at) setCrawlStopRequested(false);
      }).catch(() => {
        setAgents(prev => prev.map(a => (
          a.id === "crawler" && a.status === "active"
            ? { ...a, status: "idle", currentTask: "Crawler connection stale" }
            : a
        )));
      });
    }, 2000);
    return () => clearInterval(iv);
  }, [run?.status, runId, crawlStopRequested]);

  // Poll findings when on findings tab.
  useEffect(() => {
    if (activeTab !== "findings") return;
    api.getFindings(runId).then(setFindings).catch(() => {});
    const iv = setInterval(() => { api.getFindings(runId).then(setFindings).catch(() => {}); }, 4000);
    return () => clearInterval(iv);
  }, [runId, activeTab]);

  // Poll thinking-scan status independently.
  useEffect(() => {
    const active = isDynamicScanActive(thinkingStatus?.status) || thinkingStopRequested;
    if (!active) return;
    const iv = setInterval(() => {
      api.getThinkingStatus(runId).then(s => {
        setThinkingStatus(s);
        if (thinkingStopRequested && !isDynamicScanActive(s.status)) setThinkingStopReq(false);
        if (!isDynamicScanActive(s.status)) {
          api.getFindings(runId).then(setFindings).catch(() => {});
          // Refresh checkpoint status once the scan finishes so the Resume button
          // appears/disappears correctly without a page reload.
          api.getCheckpointStatus(runId).then(setCheckpointStatus).catch(() => {});
        }
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(iv);
  }, [runId, thinkingStatus?.status, thinkingStopRequested]);

  // Poll validation status while validating is running
  useEffect(() => {
    if (validateStatus?.status !== "running" && activeTab !== "findings") return;
    const iv = setInterval(() => {
      api.getValidateStatus(runId).then(vs => {
        setValidateStatus(vs);
        if (vs.status !== "running") setValidateBusy(false);
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(iv);
  }, [runId, validateStatus?.status, activeTab]);

  // Fetch findings when switching to findings tab
  useEffect(() => {
    if (activeTab !== "findings") return;
    api.getFindings(runId).then(setFindings).catch(()=>{});
    api.getValidateStatus(runId).then(setValidateStatus).catch(()=>{});
  }, [activeTab, runId]);

  useEffect(() => {
    if (activeTab !== "intelligence" && run?.status !== "running") return;
    const loadIntel = () => api.getTargetIntelligence(runId, targetIntelKind).then(setTargetIntel).catch(()=>{});
    loadIntel();
    if (run?.status !== "running") return;
    const iv = setInterval(loadIntel, 4000);
    return () => clearInterval(iv);
  }, [activeTab, runId, targetIntelKind, run?.status]);

  useEffect(() => {
    const active = activeTab === "tasks" || isDynamicScanActive(thinkingStatus?.status);
    if (!active) return;
    const loadTasks = () => api.getTaskGraph(runId).then(setTaskGraph).catch(()=>{});
    loadTasks();
    api.getReconSummary(runId).then(setReconSummary).catch(()=>{});
    if (!isDynamicScanActive(thinkingStatus?.status)) return;
    const iv = setInterval(loadTasks, 4000);
    return () => clearInterval(iv);
  }, [activeTab, runId, thinkingStatus?.status]);

  useEffect(() => {
    const active = activeTab === "sessions" || isDynamicScanActive(thinkingStatus?.status);
    if (!active) return;
    const loadSessions = () => api.getScannerSessions(runId).then(setScannerSessions).catch(()=>{});
    loadSessions();
    if (activeTab === "sessions" && !isDynamicScanActive(thinkingStatus?.status)) return;
    const iv = setInterval(loadSessions, 4000);
    return () => clearInterval(iv);
  }, [activeTab, runId, thinkingStatus?.status]);

  useEffect(() => {
    api.getTrafficCount(runId).then(r => setTrafficTotal(r.count || 0)).catch(()=>{});
  }, [runId]);

  // Traffic log polling — always active while crawling or scanning; also when on the tab
  useEffect(() => {
    const poll = async () => {
      try {
        const entries = await api.getTraffic(runId, lastTrafficIdRef.current);
        if (entries.length > 0) {
          lastTrafficIdRef.current = entries[entries.length - 1].id;
          setTraffic(prev => {
            const base = prev.length;
            const stamped = entries.map((e, i) => ({ ...e, _seq: base + i + 1 }));
            const next = [...prev, ...stamped];
            return next.length > 2000 ? next.slice(-2000) : next;
          });
        }
        if (activeTab === "traffic" || entries.length > 0) {
          api.getTrafficCount(runId).then(r => setTrafficTotal(r.count || 0)).catch(()=>{});
        }
      } catch(_) {}
    };
    const isActive = (
      activeTab === "traffic" ||
      run?.status === "running" ||
      isDynamicScanActive(thinkingStatus?.status) ||
      crawlStopRequested ||
      thinkingStopRequested
    );
    if (!isActive) return;
    poll();
    const iv = setInterval(poll, 2000);
    return () => clearInterval(iv);
  }, [activeTab, run?.status, thinkingStatus?.status, runId, crawlStopRequested, thinkingStopRequested]);

  // Auto-scroll traffic table to bottom when new entries arrive
  useEffect(() => {
    if (!autoScroll || activeTab !== "traffic" || !trafficTableRef.current) return;
    trafficTableRef.current.scrollTop = trafficTableRef.current.scrollHeight;
  }, [traffic.length, activeTab, autoScroll]);

  // Auto-scroll activity feed when new entries arrive
  useEffect(() => {
    if (activeTab !== "activity" || !activityFeedRef.current) return;
    activityFeedRef.current.scrollTop = activityFeedRef.current.scrollHeight;
  }, [activityLog.length, activeTab]);

  // Fetch page detail when node selected
  useEffect(() => {
    if (!selectedNode) { setPageDetail(null); setPageViews([]); return; }
    let cancelled = false;
    const pageId = selectedNode.id;
    setPageDetail(null);
    setPageViews([]);
    api.getPage(runId, pageId)
      .then(detail => {
        if (!cancelled && selectedNode.id === pageId) setPageDetail(detail);
      })
      .catch(()=>{});
    api.getPageViews(runId, pageId)
      .then(views => {
        if (!cancelled && selectedNode.id === pageId) setPageViews(views);
      })
      .catch(()=>{ if (!cancelled) setPageViews([]); });
    return () => { cancelled = true; };
  }, [selectedNode, runId]);

  // D3 force graph
  useEffect(() => {
    if (!graph || !svgRef.current) return;

    const structureKey = `${activeTab}:${graphView}:${graph.nodes.length}:${graph.links.length}`;

    // Status-only change (same nodes/links, just colour updates) — update in-place.
    if (structureKey === prevGraphKeyRef.current && simRef.current) {
      const simNodes = simRef.current.nodes();
      graph.nodes.forEach(updated => {
        const sn = simNodes.find(n => n.id === updated.id);
        if (sn) Object.assign(sn, updated);
      });
      d3.select(svgRef.current).selectAll("circle.node-dot")
        .filter(d => d && d.id != null)
        .attr("fill", nodeColorFn);
      return;
    }

    prevGraphKeyRef.current = structureKey;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const W = svgRef.current.clientWidth || 800;
    const H = svgRef.current.clientHeight || 500;

    const nodes = graph.nodes.map(n => ({...n}));
    const links = graph.links.map(l => ({...l}));

    const zoom = d3.zoom().scaleExtent([0.2, 4]).on("zoom", e => g.attr("transform", e.transform));
    svg.call(zoom);

    const g = svg.append("g");

    // Arrow marker
    svg.append("defs").append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -4 8 8")
      .attr("refX", 18).attr("refY", 0)
      .attr("markerWidth", 6).attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path").attr("d", "M0,-4L8,0L0,4").attr("fill", "var(--border-2)");

    const link = g.append("g").selectAll("line")
      .data(links).join("line")
      .attr("stroke", "var(--border-2)")
      .attr("stroke-width", 1.5)
      .attr("marker-end", "url(#arrow)");

    const node = g.append("g").selectAll("g")
      .data(nodes).join("g")
      .attr("cursor", "pointer")
      .call(d3.drag()
        .on("start", (e,d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
        .on("drag",  (e,d) => { d.fx=e.x; d.fy=e.y; })
        .on("end",   (e,d) => { if (!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }))
      .on("click", (e, d) => { e.stopPropagation(); setSelNode(d); });

    node.append("circle")
      .attr("class", "node-dot")
      .attr("r", 10)
      .attr("fill", nodeColorFn)
      .attr("stroke", d => d.status === "failed" ? "#fbbf24" : "var(--bg)")
      .attr("stroke-width", 2);

    const rootNode = nodes.find(n => n.depth === 0);
    let baseHost = null;
    try { if (rootNode) baseHost = new URL(rootNode.url).host; } catch {}

    node.append("text")
      .attr("dy", 22).attr("text-anchor", "middle")
      .attr("fill", "var(--muted)")
      .attr("font-size", "10px")
      .attr("pointer-events", "none")
      .text(d => {
        try {
          const u = new URL(d.url);
          const label = u.host === baseHost
            ? (u.pathname + u.search + u.hash || "/")
            : d.url;
          return label.length > 36 ? label.slice(0, 35) + "…" : label;
        } catch { return truncUrl(d.url, 36); }
      });

    // Tooltip on hover
    node.append("title").text(d => d.url);

    svg.on("click", () => setSelNode(null));

    const sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d=>d.id).distance(110).strength(0.8))
      .force("charge", d3.forceManyBody().strength(-350))
      .force("center", d3.forceCenter(W/2, H/2))
      .force("collision", d3.forceCollide(22))
      .on("tick", () => {
        link
          .attr("x1", d=>d.source.x).attr("y1", d=>d.source.y)
          .attr("x2", d=>d.target.x).attr("y2", d=>d.target.y);
        node.attr("transform", d=>`translate(${d.x},${d.y})`);
      });

    simRef.current = sim;
    return () => sim.stop();
  }, [graph, activeTab, graphView]);

  // Highlight the node whose URL is currently being crawled.
  // Runs after the D3 graph effect so the SVG is already populated.
  useEffect(() => {
    if (!svgRef.current || !graph) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll(".node-crawl-pulse").remove();
    if (!run?.current_url) return;
    const cur = run.current_url.replace(/\/$/, "");
    svg.select("g").selectAll("g")
      .filter(d => d && d.url && d.url.replace(/\/$/, "") === cur)
      .insert("circle", ":first-child")
        .attr("class", "node-crawl-pulse")
        .attr("r", 10);
  }, [run?.current_url, graph]);

  // Pulse graph nodes that are actively being scanned.
  // Compute the fill colour for a graph node based on current view mode.
  const nodeColorFn = (d) => {
    if (graphView === "user") return userColor(d, run?.credentials);
    return scopeColor(d);
  };

  // ── Traffic helpers ────────────────────────────────────────────────────────
  const fmtRequest = (e) => {
    if (!e) return "";
    const u = new URL(e.url);
    const path = u.pathname + u.search;
    const hdrs = Object.entries(e.request_headers||{})
      .map(([k,v])=>`${k}: ${v}`).join("\n");
    return `${e.method} ${path} HTTP/1.1\nHost: ${u.host}\n${hdrs}${e.request_body?"\n\n"+e.request_body:""}`;
  };
  const fmtResponse = (e) => {
    if (!e) return "";
    const hdrs = Object.entries(e.response_headers||{})
      .map(([k,v])=>`${k}: ${v}`).join("\n");
    return `HTTP/1.1 ${e.status??""}\n${hdrs}${e.response_body?"\n\n"+e.response_body:""}`;
  };
  const statusClass = (s) => !s ? "" : s<300 ? "tr-2xx" : s<400 ? "tr-3xx" : s<500 ? "tr-4xx" : "tr-5xx";
  const filteredTraffic = (() => {
    let list = trafficFilter
      ? traffic.filter(e =>
          e.url.toLowerCase().includes(trafficFilter.toLowerCase()) ||
          (e.method||"").toLowerCase().includes(trafficFilter.toLowerCase()) ||
          String(e.status||"").includes(trafficFilter) ||
          (e.source||"").toLowerCase().includes(trafficFilter.toLowerCase()))
      : traffic;
    const { field, dir } = trafficSort;
    const mul = dir === "asc" ? 1 : -1;
    const numeric = new Set(["_seq", "status", "duration_ms", "id"]);
    list = [...list].sort((a, b) => {
      let av = a[field], bv = b[field];
      if (numeric.has(field)) {
        av = av ?? -1; bv = bv ?? -1;
        return (av - bv) * mul;
      }
      return String(av ?? "").localeCompare(String(bv ?? "")) * mul;
    });
    return list;
  })();
  const onTrafficSort = (field) => setTrafficSort(prev =>
    prev.field === field ? { field, dir: prev.dir === "asc" ? "desc" : "asc" } : { field, dir: "asc" }
  );
  const sortArrow = (field) => trafficSort.field === field
    ? html`<span className="sort-arrow">${trafficSort.dir === "asc" ? "▲" : "▼"}</span>` : "";
  const fmtTs = (iso) => { try { const d = parseDate(iso); return d.toTimeString().slice(0,8)+"."+String(d.getMilliseconds()).padStart(3,"0"); } catch { return iso||""; } };

  const onDeleteFinding = async (e, findingId) => {
    e.stopPropagation();
    try {
      await api.deleteFinding(runId, findingId);
      setFindings(prev => prev.filter(f => f.id !== findingId));
      if (expandedFinding === findingId) setExpandedFinding(null);
    } catch(err) { setError(err.message); }
  };

  const onDeleteFindingGroup = async (e, title) => {
    e.stopPropagation();
    if (!confirm(`Delete all instances of "${title}"?`)) return;
    try {
      await api.deleteFindingGroup(runId, title);
      setFindings(prev => prev.filter(f => f.title !== title));
      setExpandedGroups(prev => { const next = new Set(prev); next.delete(title); return next; });
    } catch(err) { setError(err.message); }
  };

  const onValidateAll = async () => {
    if (validateBusy) return;
    setValidateBusy(true);
    try {
      const vs = await api.validateAllFindings(runId);
      setValidateStatus(vs);
    } catch(err) { setError(err.message); setValidateBusy(false); }
  };

  const onDeduplicateFindings = async () => {
    if (dedupeBusy) return;
    setDedupeBusy(true);
    try {
      const result = await api.deduplicateFindings(runId);
      setFindings(await api.getFindings(runId));
      api.getValidateStatus(runId).then(setValidateStatus).catch(()=>{});
      if (result.removed > 0) {
        setExpandedFinding(null);
        setExpandedGroups(new Set());
      }
      const mode = result.llm_used ? " with LLM review" : "";
      alert(`Removed ${result.removed} duplicate issue${result.removed === 1 ? "" : "s"}${mode}.`);
    } catch(err) { setError(err.message); }
    finally { setDedupeBusy(false); }
  };

  const onExportFindingsMarkdown = () => {
    try {
      const md = findingsToMarkdown(findings, {
        runName: run?.name,
        siteName,
        generatedAt: new Date(),
      });
      downloadTextFile(markdownExportFilename(run, siteName), md, "text/markdown;charset=utf-8");
    } catch(err) { setError(err.message); }
  };

  const onImportFindingsClick = () => {
    issueImportInputRef.current?.click();
  };

  const onImportFindingsFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const imported = parseFindingsMarkdown(await file.text());
      if (!imported.length) throw new Error("No issues found in the selected file.");
      const result = await api.importFindings(runId, imported);
      setFindings(await api.getFindings(runId));
      api.getValidateStatus(runId).then(setValidateStatus).catch(()=>{});
      const [r, g] = await Promise.all([api.getRun(runId), api.getGraph(runId)]);
      setRun(r); setGraph(g);
      alert(`Imported ${result.imported} issue${result.imported === 1 ? "" : "s"}.`);
    } catch(err) { setError(err.message); }
  };

  const onValidateFinding = async (e, findingId) => {
    e.stopPropagation();
    try {
      const updated = await api.validateFinding(runId, findingId);
      setFindings(prev => prev.map(f => f.id === findingId ? { ...f, ...updated } : f));
      setValidateStatus(vs => vs ? { ...vs, status: "running" } : vs);
      setValidateBusy(true);
    } catch(err) { setError(err.message); }
  };

  const onStopValidation = async () => {
    try {
      const vs = await api.stopValidation(runId);
      setValidateStatus(vs);
      setValidateBusy(false);
      setFindings(await api.getFindings(runId));
    } catch(err) { setError(err.message); }
  };

  const onStopThinkingScan = async () => {
    try {
      setThinkingStopReq(true);
      const s = await api.stopThinkingScan(runId);
      setThinkingStatus(s);
      if (!isDynamicScanActive(s.status)) setThinkingStopReq(false);
    } catch(e) { setThinkingStopReq(false); setError(e.message); }
  };

  const onStartThinkingScan = async () => {
    try {
      setThinkingStopReq(false);
      setThinkingStatus({ status: "running" });
      setCheckpointStatus(null);
      const s = await api.startThinkingScan(runId);
      setThinkingStatus(s);
    } catch(e) { setThinkingStopReq(false); setError(e.message); }
  };

  const onResumeThinkingScan = async () => {
    try {
      setThinkingStopReq(false);
      setThinkingStatus({ status: "running" });
      const s = await api.resumeThinkingScan(runId);
      setThinkingStatus(s);
    } catch(e) { setThinkingStopReq(false); setError(e.message); }
  };

  const onEditSettings = () => {
    setEditDepth(String(run.max_depth));
    setEditPages(String(run.max_pages));
    setEditLlmProfileId(run.llm_config_id || null);
    setEditingSettings(true);
  };
  const onSaveSettings = async () => {
    const d = parseInt(editDepth, 10);
    const p = parseInt(editPages, 10);
    if (!d || !p || d < 1 || d > 10 || p < 5 || p > 500) return;
    try {
      const r = await api.updateRun(runId, { max_depth: d, max_pages: p, llm_config_id: editLlmProfileId || null });
      setRun(r);
      setEditingSettings(false);
    } catch(e) { setError(e.message); }
  };

  const onToggleScope = async () => {
    if (!selectedNode || scopeBusy) return;
    setScopeBusy(true);
    const newScope = selectedNode.in_scope === false ? true : false;
    try {
      await api.setPageScope(runId, selectedNode.id, { in_scope: newScope, cascade });
      const g = await api.getGraph(runId);
      setGraph(g);
      const updated = g.nodes.find(n => n.id === selectedNode.id);
      if (updated) setSelNode(updated);
    } catch(e) { setError(e.message); } finally { setScopeBusy(false); }
  };

  const onDeleteNode = async () => {
    if (!selectedNode || scopeBusy) return;
    setScopeBusy(true);
    try {
      await api.deletePage(runId, selectedNode.id, cascade);
      const g = await api.getGraph(runId);
      setGraph(g);
      setSelNode(null);
    } catch(e) { setError(e.message); } finally { setScopeBusy(false); }
  };

  const onStart = async () => {
    try {
      setCrawlStopRequested(false);
      const r = await api.startRun(runId);
      // Optimistically mark as running so the poll interval starts immediately.
      // Clear per_user_progress so stale data from the previous crawl is never
      // shown — fresh entries arrive via crawl_progress SSE events.
      setRun({...r, status: "running", per_user_progress: {}});
    } catch(e) { setError(e.message); }
  };
  const onStop = async () => {
    try {
      setCrawlStopRequested(true);
      const r = await api.stopRun(runId);
      setRun(r);
    } catch(e) {
      setCrawlStopRequested(false);
      setError(e.message);
    }
  };
  const onClearCrawl = async () => {
    if (!confirm("Clear all crawled pages for this run?")) return;
    try {
      setCrawlStopRequested(false);
      setGraph({nodes:[], links:[]});
      const r = await api.clearCrawl(runId);
      setRun({...r, status: "pending", per_user_progress: null});
    } catch(e) { setError(e.message); }
  };

  const effectiveThinkingStatus = thinkingStatus?.status || "idle";
  const dynamicScanActive = isDynamicScanActive(effectiveThinkingStatus) || thinkingStopRequested;
  const headerStatus = runWorkflowStatus(run, {
    thinkingStatus: effectiveThinkingStatus,
    crawlStopping: crawlStopRequested,
    thinkingStopping: thinkingStopRequested,
  });
  const STATUS_COLOR = {
    neutral:"var(--muted)",
    pending:"var(--muted)",
    running:"var(--warn)",
    stopping:"var(--warn)",
    partial:"var(--text-2)",
    ok:"var(--ok)",
    danger:"var(--danger)",
  };
  const canStart   = run && !crawlStopRequested && ["pending","stopped","failed","complete"].includes(run.status);
  const canClearCrawl = run && !crawlStopRequested && ["stopped","failed","complete"].includes(run.status);
  const canStop    = run?.status === "running" && !crawlStopRequested;
  const canStopThinking = isDynamicScanActive(effectiveThinkingStatus);
  const canStartAnyScan = run?.status !== "running" && !crawlStopRequested && !isDynamicScanActive(effectiveThinkingStatus);
  const hasCheckpoint = checkpointStatus?.exists === true && canStartAnyScan && !isDynamicScanActive(effectiveThinkingStatus);

  return html`
    <div className="topbar">
      <div className="topbar-title" style=${{flexDirection:"column",alignItems:"flex-start",gap:2}}>
        <div className="row" style=${{alignItems:"center",gap:0}}>
          <a href=${run?`#/sites/${run.site_id}`:"#/"} style=${{color:"var(--muted)",fontWeight:400}}>${siteName || "Site"}</a>
          <span className="breadcrumb-sep"> / </span>
          ${run ? run.name : "…"}
          ${run && html`<span className=${"run-status-badge"+(["running","stopping"].includes(headerStatus.key)?" running":"")} style=${{color:STATUS_COLOR[headerStatus.key]||"var(--muted)"}}>● ${headerStatus.label}</span>`}
        </div>
        ${run && run.llm_config_id && runProfiles.length > 0 && html`
        <div style=${{fontSize:11,fontWeight:400,color:"var(--muted)",marginLeft:0}}>
            LLM: ${(runProfiles.find(p=>p.id===run.llm_config_id)||{name:"#"+run.llm_config_id}).name}
          </div>`}
      </div>
      <div className="topbar-actions">
        ${canStart && html`<button className="btn sm" onClick=${onStart}><${IconPlay}/> Start crawl</button>`}
        ${!thinkingStopRequested && canStartAnyScan && (effectiveThinkingStatus==="idle"||effectiveThinkingStatus==="complete"||effectiveThinkingStatus==="stopped"||effectiveThinkingStatus==="failed"||effectiveThinkingStatus==null) && html`
          <button className="btn sm" title="Run the adaptive Pentest" onClick=${onStartThinkingScan}><${IconPlay}/> Start Pentest</button>`}
        ${hasCheckpoint && html`
          <button className="btn sm" style=${{background:"var(--warn)",color:"#000",borderColor:"var(--warn)"}} title=${`Resume scan from step ${checkpointStatus.step_count}`} onClick=${onResumeThinkingScan}><${IconPlay}/> Resume Pentest</button>`}
        ${canStop && html`<button className="btn danger-outline" onClick=${onStop}><${IconStop}/> Stop crawl</button>`}
        ${crawlStopRequested && html`<button className="btn danger-outline" disabled><${IconStop}/> Stopping…</button>`}
        ${!canStop && !crawlStopRequested && canStopThinking && html`<button className="btn danger-outline" onClick=${onStopThinkingScan} disabled=${thinkingStopRequested}><${IconStop}/> ${thinkingStopRequested ? "Stopping…" : "Stop Dynamic Scan"}</button>`}
        ${aliceGlobalRunning && html`
          <button
            className="btn danger-outline"
            style=${{ borderColor: "var(--danger)", color: "var(--danger)", background: "rgba(239,68,68,.08)" }}
            onClick=${handleAliceStop}
            title="Stop the running A.L.I.C.E. agent"
          ><${IconStop}/> Stop A.L.I.C.E.</button>
        `}
      </div>
    </div>

    <div className="content" style=${{paddingBottom:0,display:"flex",flexDirection:"column",flex:1,minHeight:0}}>
      ${error && html`<div className="alert error" style=${{marginBottom:12}}>${error}</div>`}

      <div className="tab-bar">
        <button className=${"tab-btn"+(activeTab==="activity"?" active":"")}
          onClick=${()=>{ setActiveTab("activity"); setSelNode(null); nav(`#/runs/${runId}/activity`); }}>
          Status${isDynamicScanActive(thinkingStatus?.status) && activityLog.length>0 ? html`<span className="activity-live-dot">●</span>` : ""}
        </button>
        <button className=${"tab-btn"+(activeTab==="sitemap"?" active":"")}
          onClick=${()=>{ setActiveTab("sitemap"); setSelNode(null); nav(`#/runs/${runId}/sitemap`); }}>Site Map</button>
        <button className=${"tab-btn"+(activeTab==="intelligence"?" active":"")}
          onClick=${()=>{ setActiveTab("intelligence"); setSelNode(null); nav(`#/runs/${runId}/intelligence`); }}>
          Intelligence${targetIntel && Object.values(targetIntel.counts||{}).reduce((a,b)=>a+b,0)>0 ? html` <span className="traffic-count">${Object.values(targetIntel.counts||{}).reduce((a,b)=>a+b,0)}</span>` : ""}
        </button>
        <button className=${"tab-btn"+(activeTab==="tasks"?" active":"")}
          onClick=${()=>{ setActiveTab("tasks"); setSelNode(null); nav(`#/runs/${runId}/tasks`); }}>
          Task Graph${taskGraph?.counts?.tasks>0 ? html` <span className="traffic-count">${taskGraph.counts.tasks}</span>` : ""}
        </button>
        <button className=${"tab-btn"+(activeTab==="sessions"?" active":"")}
          onClick=${()=>{ setActiveTab("sessions"); setSelNode(null); nav(`#/runs/${runId}/sessions`); }}>
          Sessions${scannerSessions?.counts?.total>0 ? html` <span className="traffic-count">${scannerSessions.counts.total}</span>` : ""}
        </button>
        <button className=${"tab-btn"+(activeTab==="findings"?" active":"")}
          onClick=${()=>{ setActiveTab("findings"); setSelNode(null); nav(`#/runs/${runId}/findings`); }}>
          Findings${findings.length>0?html` <span className="findings-badge">${findings.length}</span>`:""}
        </button>
        <button className=${"tab-btn"+(activeTab==="traffic"?" active":"")}
          onClick=${()=>{ setActiveTab("traffic"); setSelNode(null); nav(`#/runs/${runId}/traffic`); }}>
          Traffic Log${trafficTotal>0?html` <span className="traffic-count">${trafficTotal}</span>`:""}
        </button>
        <div style=${{flex:1}}></div>
        ${canClearCrawl && activeTab==="sitemap" && html`<button className="btn danger-outline sm" style=${{margin:"auto 8px auto 0"}} onClick=${onClearCrawl}>Clear crawl</button>`}
        ${activeTab==="sitemap" && run?.credentials?.length > 1 && html`
          <div className="view-toggle" style=${{margin:"auto 8px auto 0"}}>
            <button className=${"btn ghost sm"+(graphView==="scope"?" active":"")}
              onClick=${()=>setGraphView("scope")}>By Scope</button>
            <button className=${"btn ghost sm"+(graphView==="user"?" active":"")}
              onClick=${()=>setGraphView("user")}>By User</button>
          </div>`}
      </div>

      ${activeTab==="sitemap" && run && html`
        <div className="run-meta">
          <div className="run-stat"><span className="run-stat-val">${run.pages_discovered}</span><span className="run-stat-lbl">Pages found</span></div>
          ${editingSettings ? html`
            <div className="run-stat-edit">
              <div className="run-stat-edit-field">
                <label>Max depth</label>
                <input type="number" min="1" max="10" value=${editDepth}
                  onInput=${e=>setEditDepth(e.target.value)} style=${{width:54}}/>
              </div>
              <div className="run-stat-edit-field">
                <label>Max pages</label>
                <input type="number" min="5" max="500" value=${editPages}
                  onInput=${e=>setEditPages(e.target.value)} style=${{width:64}}/>
              </div>
              <div style=${{display:"flex",gap:6,alignItems:"center"}}>
                <button className="btn sm" onClick=${onSaveSettings}>Save</button>
                <button className="btn ghost sm" onClick=${()=>setEditingSettings(false)}>Cancel</button>
              </div>
            </div>
          ` : html`
            <div className="run-stat">
              <span className="run-stat-val">${run.max_depth}</span>
              <span className="run-stat-lbl">Max depth</span>
            </div>
            <div className="run-stat">
              <span className="run-stat-val">${run.max_pages}</span>
              <span className="run-stat-lbl">Max pages</span>
            </div>
            ${run.llm_config_id && runProfiles.length > 0 && html`
              <div className="run-stat">
                <span className="run-stat-val" style=${{fontSize:12}}>${(runProfiles.find(p=>p.id===run.llm_config_id)||{name:"#"+run.llm_config_id}).name}</span>
                <span className="run-stat-lbl">LLM profile</span>
              </div>`}
            ${run.status !== "running" && html`
              <button className="btn ghost sm" style=${{alignSelf:"center",marginLeft:4}}
                title="Edit depth / pages" onClick=${onEditSettings}>✎</button>`}
          `}
          ${(()=>{
            const pup = run.per_user_progress || {};
            const multiUser = run.credentials?.length > 1;
            if (multiUser) return null; // per-user section rendered below
            return html`
              ${crawlUsername&&html`<div className="run-stat"><span className="run-stat-lbl">Crawling as</span><span className="run-stat-val" style=${{fontSize:14}}>${crawlUsername}</span></div>`}
              ${run.current_url&&html`<div className="run-stat run-stat-url"><span className="run-stat-lbl">Current URL</span><span className="mono run-stat-url-val">${truncUrl(run.current_url,50)}</span></div>`}
            `;
          })()}
          ${run.error_message&&html`<div style=${{color:"var(--danger)",fontSize:12,flex:1}}>${run.error_message}</div>`}
        </div>
        ${activeTab==="sitemap" && run && html`
          <${ScopeHostsPanel}
            siteId=${run.site_id}
            hosts=${scopeHosts}
            onChange=${setScopeHosts}
          />`}
        ${(()=>{
          const credList = run.credentials || [];
          const multiUser = credList.length > 1;
          // Overall progress reaches the cap while crawling, then fills once discovery is complete.
          const overallPct = run.status === "complete"
            ? 100
            : Math.min(100, (run.pages_discovered / run.max_pages) * 100);
          const progressBar = (run.status === "running" || run.pages_discovered > 0) ? html`
            <div className="crawl-progress-bar">
              <div className="crawl-progress-fill" style=${{width: overallPct + "%"}}></div>
            </div>` : null;
          if (multiUser) {
            const pup = run.per_user_progress || {};
            return html`
              ${progressBar}
              <div className="crawl-user-progress">
                ${credList.map((c, idx) => {
                  const p = pup[c.username] || {};
                  const color = USER_PALETTE[idx % USER_PALETTE.length];
                  const isActive = run.status === "running" && !p.done;
                  return html`
                    <div key=${c.username} className="crawl-user-row">
                      <span className=${"crawl-user-dot"+(isActive?" active":"")} style=${{background:color}}></span>
                      <span className="crawl-user-name" title=${c.username}>${c.label||c.username}</span>
                      <span className="crawl-user-pages">${p.pages_visited||0} pg</span>
                      <span className="crawl-user-url mono" title=${p.current_url||""}>
                        ${p.current_url ? truncUrl(p.current_url, 42) : (p.done ? "done" : "waiting…")}
                      </span>
                    </div>`;
                })}
              </div>`;
          }
          return progressBar;
        })()}`}

      <div className="graph-layout" style=${{display: (activeTab==="findings"||activeTab==="traffic"||activeTab==="activity"||activeTab==="intelligence"||activeTab==="tasks"||activeTab==="sessions") ? "none" : "flex"}}>
        <div className="graph-canvas-wrap">
          ${graph&&graph.nodes.length===0 && html`
            <div className="graph-empty">
              ${activeTab==="sitemap" && run?.status==="pending"
                ? html`<div style=${{display:"flex",flexDirection:"column",alignItems:"center",gap:12}}>
                    <span>Ready to crawl.</span>
                    <button className="btn" onClick=${onStart}><${IconPlay}/> Start crawl</button>
                    <span className="subtle" style=${{fontSize:12}}>or</span>
                    <button className="btn" onClick=${onStartThinkingScan}><${IconPlay}/> Start Dynamic Scan</button>
                    ${hasCheckpoint && html`
                      <button className="btn" style=${{background:"var(--warn)",color:"#000",borderColor:"var(--warn)"}} onClick=${onResumeThinkingScan}><${IconPlay}/> Resume Pentest (step ${checkpointStatus.step_count})</button>`}
                  </div>`
                : html`<span>No pages discovered yet.</span>`}
            </div>`}
          <svg ref=${svgRef} className="graph-svg" width="100%" height="100%" style=${{pointerEvents: (!graph || graph.nodes.length === 0) ? "none" : "all"}}></svg>
          ${graph&&graph.nodes.length>0 && html`
            <div className="graph-legend">
              ${graphView === "user" && run?.credentials?.length > 1 ? html`
                ${(run.credentials||[]).map((c,i) => html`
                  <div key=${c.id} className="legend-item">
                    <span className="legend-dot" style=${{background:USER_PALETTE[i%USER_PALETTE.length]}}></span>
                    ${c.label||c.username}
                  </div>`)}
                <div className="legend-item"><span className="legend-dot" style=${{background:USER_BOTH_COLOR}}></span>All users</div>
              ` : html`
                <div className="legend-item"><span className="legend-dot" style=${{background:SCOPE_IN_COLOR}}></span>In Scope</div>
                <div className="legend-item"><span className="legend-dot" style=${{background:SCOPE_OUT_COLOR}}></span>Out of Scope</div>
                <div className="legend-item"><span className="legend-dot" style=${{background:"var(--bg)",border:"2px solid #fbbf24"}}></span>Failed</div>
              `}
            </div>`}
        </div>

        ${selectedNode && html`
          <div className="graph-panel">
            <div className="graph-panel-header">
              <div className="graph-panel-url">${selectedNode.url}</div>
              <button className="btn ghost sm" onClick=${()=>setSelNode(null)}>✕</button>
            </div>
            ${pageDetail ? html`
              <div className="graph-panel-body">
                ${pageDetail.title && html`<div className="graph-panel-title">${pageDetail.title}</div>`}

                <div className="graph-panel-section-label">Scope</div>
                <div className="scope-row">
                  <span className=${"scope-badge " + (selectedNode.in_scope === false ? "out" : "in")}>
                    ${selectedNode.in_scope === false ? "Out of Scope" : "In Scope"}
                  </span>
                  <button className="btn sm" onClick=${onToggleScope} disabled=${scopeBusy}>
                    ${scopeBusy ? "…" : (selectedNode.in_scope === false ? "Mark in scope" : "Mark out of scope")}
                  </button>
                  <button className="btn danger-outline sm" onClick=${onDeleteNode} disabled=${scopeBusy}
                    title="Delete this node (and children if checkbox is ticked)">🗑</button>
                </div>
                <label className="scope-cascade-label">
                  <input type="checkbox" checked=${cascade} onChange=${e=>setCascade(e.target.checked)}/>
                  Also apply to all children
                </label>

                <div className="graph-panel-section-label" style=${{marginTop:14}}>Page Categories</div>
                <div className="page-cats">
                  ${[
                    ["req_auth",          "Auth Required"],
                    ["takes_input",       "Takes Input"],
                    ["has_object_ref",    "Object Reference"],
                    ["has_business_logic","Business Logic"],
                  ].map(([key, label]) => {
                    const val = pageDetail[key];
                    const cls = val === true ? "cat-yes" : val === false ? "cat-no" : "cat-unknown";
                    const badge = val === true ? "Yes" : val === false ? "No" : "?";
                    return html`<div key=${key} className="cat-row">
                      <span className="cat-label">${label}</span>
                      <span className=${"cat-badge " + cls}>${badge}</span>
                    </div>`;
                  })}
                </div>

                ${pageViews.length > 0 ? html`
                  <div className="graph-panel-section-label" style=${{marginTop:14}}>
                    Views by User
                  </div>
                  ${pageViews.map(v => {
                    const apiTranscript = apiTranscriptText(v.page_text || pageDetail.page_text);
                    return html`
                      <div key=${v.id} className="credential-view-card">
                        <div className="credential-view-label">
                          ${v.username || "Anonymous"}
                        </div>
                        ${v.screenshot_b64 && html`
                          <img src=${"data:image/png;base64,"+v.screenshot_b64}
                            className="credential-view-screenshot" alt=${"screenshot ("+v.username+")"}/>`}
                        ${!v.screenshot_b64 && apiTranscript && html`
                          <div className="api-transcript-label">API Request / Response</div>
                          <pre className="api-transcript">${apiTranscript}</pre>`}
                        <div className="credential-view-context">
                          ${v.llm_context || "No context."}
                        </div>
                      </div>`;
                  })}
                ` : html`
                  <div className="graph-panel-section-label" style=${{marginTop:14}}>LLM Context</div>
                  <div className="graph-panel-context">${pageDetail.llm_context || "No context available."}</div>
                  ${pageDetail.screenshot_b64 && html`
                    <div className="graph-panel-section-label" style=${{marginTop:12}}>Screenshot</div>
                    <img src=${`data:image/png;base64,${pageDetail.screenshot_b64}`}
                      style=${{width:"100%",borderRadius:6,border:"1px solid var(--border)"}} alt="screenshot"/>`}
                  ${!pageDetail.screenshot_b64 && apiTranscriptText(pageDetail.page_text) && html`
                    <div className="graph-panel-section-label" style=${{marginTop:12}}>API Request / Response</div>
                    <pre className="api-transcript">${apiTranscriptText(pageDetail.page_text)}</pre>`}
                `}
              </div>` : html`<div className="subtle" style=${{padding:12}}>Loading…</div>`}
          </div>`}
      </div>

      ${activeTab==="findings" && html`
        <div className="findings-panel">
          <div className="findings-status-bar">
            ${thinkingStatus && thinkingStatus.status && thinkingStatus.status !== "idle" && html`
              <span className=${"scan-status-badge scan-status-"+(thinkingStopRequested ? "stopping" : thinkingStatus.status)}>
                ${thinkingStopRequested ? "Stopping Dynamic Scan…" :
                  thinkingStatus.status==="running"   ? "Dynamic Scan running…" :
                  thinkingStatus.status==="analysing" ? "Dynamic Scan analysing…" :
                  thinkingStatus.status==="stopping"  ? "Dynamic Scan stopping…" :
                  thinkingStatus.status==="complete"  ? "Dynamic Scan complete" :
                  thinkingStatus.status==="stopped"   ? "Dynamic Scan stopped" :
                  thinkingStatus.status==="failed"    ? "Dynamic Scan failed" : "Dynamic Scan"}
              </span>`}
            <div style=${{flex:1}}></div>
            ${validateStatus?.status==="running"
              ? html`<span className="val-status-badge val-running">Validating… ${validateStatus.confirmed+validateStatus.false_positives+(validateStatus.unconfirmed||0)}/${validateStatus.total}</span>`
              : validateStatus?.status==="stopped"
                ? html`<span className="val-status-badge val-fp">Validation stopped</span>`
              : validateStatus?.status==="complete"
                ? html`<span className="val-status-badge val-complete">${validateStatus.confirmed} confirmed · ${validateStatus.unconfirmed||0} unconfirmed · ${validateStatus.false_positives} low confidence</span>`
                : null}
            ${validateStatus?.status==="running" && html`
              <button className="btn danger-outline sm" style=${{marginLeft:8}}
                onClick=${onStopValidation}>Stop validation</button>`}
            ${dedupeBusy && html`
              <span className="val-status-badge val-running dedupe-status">
                <span className="inline-spinner"></span>
                De-duplicating with LLM…
              </span>`}
            <div className="row" style=${{gap:8,marginLeft:8}}>
              ${findings.length>0 && html`
                <button className="btn sm" onClick=${onExportFindingsMarkdown}>
                  Export Issues
                </button>`}
              <button className="btn sm" onClick=${onImportFindingsClick}>
                Import Issues
              </button>
              <input ref=${issueImportInputRef} type="file" accept=".md,text/markdown,text/plain"
                style=${{display:"none"}} onChange=${onImportFindingsFile}/>
              ${findings.length>0 && html`
                <button className="btn sm"
                  disabled=${validateBusy||validateStatus?.status==="running"}
                  onClick=${onValidateAll}>✓ Validate Issues</button>`}
              ${findings.length>0 && html`
                <button className="btn sm"
                  disabled=${dedupeBusy||validateBusy||validateStatus?.status==="running"}
                  onClick=${onDeduplicateFindings}>
                  ${dedupeBusy && html`<span className="inline-spinner"></span>`}
                  ${dedupeBusy ? "De-duplicating…" : "De-duplicate Issues"}
                </button>`}
              ${findings.length>0 && html`
                <button className="btn danger-outline sm"
                  disabled=${clearBusy==="findings"}
                  onClick=${async()=>{
                    if (!confirm("Clear all findings and reset page scan status?\nThis lets you re-run the scanner on the same crawl.")) return;
                    setClearBusy("findings"); setClearError(null);
                    try { await api.clearFindings(runId); setFindings([]); }
                    catch(e) { setClearError(e.message); }
                    finally { setClearBusy(""); }
                  }}>${clearBusy==="findings"?"Clearing…":"Clear all"}</button>`}
            </div>
          </div>
          ${findings.length === 0
            ? html`<div className="subtle" style=${{padding:24,textAlign:"center"}}>
                ${isDynamicScanActive(thinkingStatus?.status)
                  ? "Scan running… findings will appear here."
                  : "No findings yet. Start a Dynamic Scan to begin."}
              </div>`
            : html`
              <div className="findings-table-wrap">${(()=>{
                const SEV_ORDER = {critical:0,high:1,medium:2,low:3,info:4};
                const VAL_ORDER = {confirmed:0, validating:1, unvalidated:2, unconfirmed:3, false_positive:4, low_confidence:4};
                const DETERMINISTIC_GROUP_KEY = "__deterministic__";
                const UNCONFIRMED_GROUP_KEY = "__unconfirmed__";
                const FP_GROUP_KEY = "__low_confidence__";
                const activeMap = {};
                const unconfirmedMap = {};
                const fpMap = {};
                const deterministicMap = {};
                for (const f of findings) {
                  const target = (f.finding_source === "deterministic_probe")
                    ? deterministicMap
                    : (f.validation_status === "false_positive" || f.validation_status === "low_confidence")
                      ? fpMap
                      : f.validation_status === "unconfirmed"
                        ? unconfirmedMap
                        : activeMap;
                  (target[f.title] = target[f.title]||[]).push(f);
                }
                const makeGroups = (map) => Object.entries(map).map(([title, items]) => {
                  const sortedItems = [...items].sort((a,b)=>{
                    const va = VAL_ORDER[a.validation_status] ?? 2;
                    const vb = VAL_ORDER[b.validation_status] ?? 2;
                    if (va !== vb) return va - vb;
                    return (SEV_ORDER[a.severity]??99)-(SEV_ORDER[b.severity]??99);
                  });
                  const topSev = items.reduce((b,f)=>
                    (SEV_ORDER[f.severity]??99)<(SEV_ORDER[b]??99)?f.severity:b, items[0].severity);
                  return { title, items:sortedItems, topSev, count:items.length, source:items[0].finding_source || "unknown" };
                }).sort((a,b)=>{
                  return (SEV_ORDER[a.topSev]??99)-(SEV_ORDER[b.topSev]??99);
                });
                const groups = makeGroups(activeMap);
                const unconfirmedGroups = makeGroups(unconfirmedMap);
                const fpGroups = makeGroups(fpMap);
                const deterministicGroups = makeGroups(deterministicMap);
                const unconfirmedCount = unconfirmedGroups.reduce((total,g)=>total+g.count,0);
                const fpCount = fpGroups.reduce((total,g)=>total+g.count,0);
                const deterministicCount = deterministicGroups.reduce((total,g)=>total+g.count,0);
                const evidenceItemsFor = (f) => {
                  if (Array.isArray(f.evidence_items)) return f.evidence_items;
                  try {
                    const parsed = JSON.parse(f.evidence_json || "[]");
                    return Array.isArray(parsed) ? parsed : [];
                  } catch (_) {
                    return [];
                  }
                };
                const renderFinding = (f, keyPrefix="") => html`
                  <tr key=${keyPrefix+f.id} className="finding-instance-row"
                    onClick=${()=>setExpandedFinding(expandedFinding===f.id?null:f.id)}>
                    <td>
                      ${f.validation_status==="confirmed"      && html`<span className="val-badge val-confirmed">confirmed</span>`}
                      ${f.validation_status==="unconfirmed"   && html`<span className="val-badge val-unconfirmed">unconfirmed</span>`}
                      ${f.validation_status==="false_positive" && html`<span className="val-badge val-fp">low conf</span>`}
                      ${f.validation_status==="low_confidence" && html`<span className="val-badge val-fp">low conf</span>`}
                      ${f.validation_status==="validating"    && html`<span className="val-badge val-validating">…</span>`}
                    </td>
                    <td></td>
                    <td colSpan="2">
                      <span className="instance-chevron">${expandedFinding===f.id?"▾":"▸"}</span>
                      <span className="finding-affected-label" style=${{marginRight:6}}>Affected URL</span>
                      <span className="mono" style=${{fontSize:11,wordBreak:"break-all"}}>${f.affected_url||"—"}</span>
                    </td>
                    <td>
                      <div className="row" style=${{gap:4,justifyContent:"flex-end"}}>
                        ${(f.validation_status==="unvalidated"||f.validation_status==="unconfirmed"||f.validation_status==="false_positive"||f.validation_status==="low_confidence") && html`
                          <button className="btn ghost sm finding-del-btn" title="Validate"
                            onClick=${e=>onValidateFinding(e,f.id)}>✓</button>`}
                        <button className="btn ghost sm finding-del-btn" title="Delete"
                          onClick=${e=>onDeleteFinding(e,f.id)}>🗑</button>
                      </div>
                    </td>
                  </tr>
                  ${expandedFinding===f.id && html`
                    <tr key=${"ev-"+keyPrefix+f.id} className="finding-evidence-row">
                      <td colSpan="5">
                        <div className="finding-description">
                          <div><strong>Description</strong></div>
                          <div>${f.description || "—"}</div>
                          <div style=${{marginTop:8}}><strong>Impact</strong></div>
                          <div>${f.impact || "—"}</div>
                          <div style=${{marginTop:8}}><strong>Likelihood</strong></div>
                          <div>${f.likelihood || "—"}</div>
                          <div style=${{marginTop:8}}><strong>Recommendation</strong></div>
                          <div>${f.recommendation || "—"}</div>
                          <div style=${{marginTop:8}}><strong>CVSS 3.1</strong></div>
                          <div>
                            ${f.cvss_score !== undefined && f.cvss_score !== null ? `${Number(f.cvss_score).toFixed(1)} (${f.severity})` : "—"}
                            ${f.cvss_vector ? html`<span className="mono" style=${{marginLeft:8,fontSize:11}}>${f.cvss_vector}</span>` : ""}
                          </div>
                        </div>
                        ${f.validation_note && html`
                          <div className=${"finding-validation-note val-note-"+f.validation_status}>
                            <strong>Validation (${f.validation_status}):</strong> ${f.validation_note}
                          </div>`}
                        ${evidenceItemsFor(f).length > 0 && html`
                          <div className="structured-evidence">
                            ${evidenceItemsFor(f).map((item,idx)=>html`
                              <div key=${idx} className=${"structured-evidence-item evidence-type-"+(item.type||"note")}>
                                <div className="structured-evidence-label">
                                  <span>${item.label || item.type || "Evidence"}</span>
                                  ${item.confidence && html`<span className="structured-evidence-confidence">${item.confidence}</span>`}
                                </div>
                                <pre className="structured-evidence-value">${item.value}</pre>
                              </div>`)}
                          </div>`}
                        ${f.request_evidence && html`
                          <pre className="finding-evidence">REQUEST:\n${f.request_evidence}</pre>`}
                        ${f.response_evidence && html`
                          <pre className="finding-evidence">RESPONSE:\n${f.response_evidence}</pre>`}
                        ${!f.request_evidence && !f.response_evidence && f.evidence && html`
                          <pre className="finding-evidence">${f.evidence}</pre>`}
                        ${f.screenshot_b64 && html`
                          <div className="finding-screenshot-wrap">
                            <div className="finding-affected-label">Screenshot</div>
                            <img src=${"data:image/png;base64,"+f.screenshot_b64}
                              className="finding-screenshot" alt="proof screenshot"/>
                          </div>`}
                        ${(()=>{
                          const instances = (()=>{ try { return JSON.parse(f.merged_instances||"[]"); } catch(_){return [];} })();
                          if (!instances.length) return null;
                          return html`
                            <div style=${{marginTop:12}}>
                              <strong>Additional Affected Instances (${instances.length})</strong>
                              ${instances.map((inst,idx)=>html`
                                <div key=${idx} style=${{marginTop:8,paddingLeft:12,borderLeft:"2px solid var(--border,#ccc)"}}>
                                  <div className="finding-affected-label">Instance ${idx+2}</div>
                                  <span className="mono" style=${{fontSize:11,wordBreak:"break-all"}}>${inst.url||"\u2014"}</span>
                                  ${inst.request_evidence && html`<pre className="finding-evidence" style=${{marginTop:4}}>REQUEST:\n${inst.request_evidence}</pre>`}
                                  ${inst.response_evidence && html`<pre className="finding-evidence">RESPONSE:\n${inst.response_evidence}</pre>`}
                                  ${!inst.request_evidence && !inst.response_evidence && inst.evidence && html`<pre className="finding-evidence">${inst.evidence}</pre>`}
                                </div>`)}
                            </div>`;
                        })()}
                      </td>
                    </tr>`}
                `;
                const renderStatusRows = (statusGroups, keyPrefix) => statusGroups.map(g => {
                  const groupKey = keyPrefix + ":" + g.title;
                  return html`
                    <tr key=${groupKey} className="finding-group-row"
                      onClick=${()=>toggleGroup(groupKey)}>
                      <td><span className=${"sev-badge sev-"+g.topSev}>${g.topSev}</span></td>
                      <td><span className="source-badge">${sourceLabel(g.source)}</span></td>
                      <td className="finding-title">
                        <span className="group-chevron">${expandedGroups.has(groupKey)?"▾":"▸"}</span>
                        ${g.title}
                      </td>
                      <td><span className="finding-count-badge">${g.count}</span></td>
                      <td></td>
                    </tr>
                    ${expandedGroups.has(groupKey) && g.items.map(f => renderFinding(f,keyPrefix+"-"))}
                  `;
                });
                const unconfirmedRows = renderStatusRows(unconfirmedGroups, "unconfirmed");
                const fpRows = renderStatusRows(fpGroups, "fp");
                const deterministicRows = renderStatusRows(deterministicGroups, "deterministic");
                return html`
                <table className="findings-table">
                  <colgroup>${findColW.map((w,i)=>html`<col key=${i} style=${{width:w!=null?w+"px":undefined}}/>`)}</colgroup>
                  <thead>
                    <tr>
                      <th>Severity <div className="col-rh" onMouseDown=${e=>startFindResize(0,e)} onClick=${e=>e.stopPropagation()}/></th>
                      <th>Source <div className="col-rh" onMouseDown=${e=>startFindResize(1,e)} onClick=${e=>e.stopPropagation()}/></th>
                      <th>Title <div className="col-rh" onMouseDown=${e=>startFindResize(2,e)} onClick=${e=>e.stopPropagation()}/></th>
                      <th># <div className="col-rh" onMouseDown=${e=>startFindResize(3,e)} onClick=${e=>e.stopPropagation()}/></th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    ${groups.map(g => html`
                      <tr key=${g.title} className="finding-group-row"
                        onClick=${()=>toggleGroup(g.title)}>
                        <td><span className=${"sev-badge sev-"+g.topSev}>${g.topSev}</span></td>
                        <td><span className="source-badge">${sourceLabel(g.source)}</span></td>
                        <td className="finding-title">
                          <span className="group-chevron">${expandedGroups.has(g.title)?"▾":"▸"}</span>
                          ${g.title}
                        </td>
                        <td><span className="finding-count-badge">${g.count}</span></td>
                        <td>
                          <button className="btn ghost sm finding-del-btn" title="Delete group"
                            onClick=${e=>onDeleteFindingGroup(e,g.title)}>🗑</button>
                        </td>
                      </tr>
                      ${expandedGroups.has(g.title) && g.items.map(f => renderFinding(f))}
                    `)}
                    ${unconfirmedCount > 0 && html`
                      <tr key=${UNCONFIRMED_GROUP_KEY} className="finding-group-row"
                        onClick=${()=>toggleGroup(UNCONFIRMED_GROUP_KEY)}>
                        <td><span className="val-badge val-unconfirmed">unconfirmed</span></td>
                        <td></td>
                        <td className="finding-title">
                          <span className="group-chevron">${expandedGroups.has(UNCONFIRMED_GROUP_KEY)?"▾":"▸"}</span>
                          Unconfirmed Findings
                        </td>
                        <td><span className="finding-count-badge">${unconfirmedCount}</span></td>
                        <td></td>
                      </tr>
                      ${expandedGroups.has(UNCONFIRMED_GROUP_KEY) && unconfirmedRows}
                    `}
                    ${fpCount > 0 && html`
                      <tr key=${FP_GROUP_KEY} className="finding-group-row"
                        onClick=${()=>toggleGroup(FP_GROUP_KEY)}>
                        <td><span className="val-badge val-fp">low conf</span></td>
                        <td></td>
                        <td className="finding-title">
                          <span className="group-chevron">${expandedGroups.has(FP_GROUP_KEY)?"▾":"▸"}</span>
                          Low Confidence
                        </td>
                        <td><span className="finding-count-badge">${fpCount}</span></td>
                        <td></td>
                      </tr>
                      ${expandedGroups.has(FP_GROUP_KEY) && fpRows}
                    `}
                    ${deterministicCount > 0 && html`
                      <tr key=${DETERMINISTIC_GROUP_KEY} className="finding-group-row"
                        onClick=${()=>toggleGroup(DETERMINISTIC_GROUP_KEY)}>
                        <td><span className="val-badge val-fp">deterministic</span></td>
                        <td></td>
                        <td className="finding-title">
                          <span className="group-chevron">${expandedGroups.has(DETERMINISTIC_GROUP_KEY)?"▾":"▸"}</span>
                          Deterministic Findings
                        </td>
                        <td><span className="finding-count-badge">${deterministicCount}</span></td>
                        <td></td>
                      </tr>
                      ${expandedGroups.has(DETERMINISTIC_GROUP_KEY) && deterministicRows}
                    `}
                  </tbody>
                </table>`;
              })()}
              </div>`}
        </div>`}

      ${activeTab==="intelligence" && html`
        <${TargetIntelligencePanel}
          data=${targetIntel}
          selectedKind=${targetIntelKind}
          onKind=${setTargetIntelKind}
          refresh=${()=>api.getTargetIntelligence(runId, targetIntelKind).then(setTargetIntel).catch(()=>{})}
          onClear=${async()=>{
            if (!confirm("Clear all target intelligence for this run?")) return;
            setClearBusy("intel"); setClearError(null);
            try { await api.clearTargetIntel(runId); setTargetIntel(null); setTargetIntelKind(""); }
            catch(e) { setClearError(e.message); }
            finally { setClearBusy(""); }
          }}
          clearing=${clearBusy==="intel"}
        />`}

      ${activeTab==="tasks" && html`
        <${TaskGraphPanel}
          data=${taskGraph}
          reconSummary=${reconSummary}
          subTab=${tasksSubTab}
          onSubTab=${setTasksSubTab}
          refresh=${()=>api.getTaskGraph(runId).then(setTaskGraph).catch(()=>{})}
          seed=${()=>api.seedTaskGraph(runId).then(setTaskGraph).catch(e=>setError(e.message))}
          onClear=${async()=>{
            if (!confirm("Clear all hypotheses and tasks for this run?")) return;
            setClearBusy("tasks"); setClearError(null);
            try { await api.clearTaskGraph(runId); setTaskGraph(null); }
            catch(e) { setClearError(e.message); }
            finally { setClearBusy(""); }
          }}
          clearing=${clearBusy==="tasks"}
        />`}

      ${activeTab==="sessions" && html`
        <${ScannerSessionsPanel}
          runId=${runId}
          data=${scannerSessions}
          refresh=${()=>api.getScannerSessions(runId).then(setScannerSessions).catch(()=>{})}
        />`}

      ${activeTab==="activity" && html`
        <div className="activity-panel">
          ${(() => {
            const isAgentic = activityLog.some(e => e.data?.mode === "agentic");
            const fmtTok = (n) => n >= 1_000_000 ? (n/1_000_000).toFixed(1)+"M" : n >= 1_000 ? (n/1_000).toFixed(1)+"K" : String(n||0);
            const hasTokens = tokenUsage && (tokenUsage.total_input > 0 || tokenUsage.total_output > 0);
            return html`
              <div className="activity-token-bar" onClick=${hasTokens ? ()=>setTokenExpanded(p=>!p) : undefined}
                   style=${{cursor: hasTokens ? "pointer" : "default"}}>
                ${hasTokens ? html`
                  <span className="token-bar-label">Tokens</span>
                  <span className="token-bar-in" title="Input tokens">↑${fmtTok(tokenUsage.total_input)} in</span>
                  <span className="token-bar-sep">·</span>
                  <span className="token-bar-out" title="Output tokens">↓${fmtTok(tokenUsage.total_output)} out</span>
                  ${(tokenUsage.total_cache_read > 0 || tokenUsage.total_cache_write > 0) ? html`
                    <span className="token-bar-sep">·</span>
                    ${tokenUsage.total_cache_read > 0 ? html`<span className="token-bar-cache-read" title="Cache read tokens">⚡${fmtTok(tokenUsage.total_cache_read)} cached</span>` : null}
                    ${tokenUsage.total_cache_write > 0 ? html`<span className="token-bar-cache-write" title="Cache write tokens">✎${fmtTok(tokenUsage.total_cache_write)} written</span>` : null}
                  ` : null}
                  <span className="activity-expand-chevron" style=${{marginLeft:4}}>${tokenExpanded?"▲":"▼"}</span>
                ` : html`<span className="token-bar-empty">No token data yet</span>`}
              </div>
              ${tokenExpanded && hasTokens && html`
                <div className="token-breakdown">
                  ${Object.entries(tokenUsage.by_model||{}).map(([model, v]) => html`
                    <div key=${model} className="token-breakdown-row">
                      <span className="token-model-name">${model}</span>
                      <span className="token-in">↑${fmtTok(v.input)}</span>
                      <span className="token-out">↓${fmtTok(v.output)}</span>
                      ${(v.cache_read > 0 || v.cache_write > 0) ? html`
                        ${v.cache_read > 0 ? html`<span className="token-cache-read" title="Cache read">⚡${fmtTok(v.cache_read)}</span>` : null}
                        ${v.cache_write > 0 ? html`<span className="token-cache-write" title="Cache write">✎${fmtTok(v.cache_write)}</span>` : null}
                      ` : null}
                    </div>`)}
                </div>`}
              <div className="activity-sub-tab-bar">
                <button className=${"activity-sub-tab-btn"+(activitySubTab==="agents"?" active":"")}
                  onClick=${()=>setActivitySubTab("agents")}>Agents${agents.map(normalizeAgentForRun).some(a=>a.status==="active")?" ●":""}</button>
                <button className=${"activity-sub-tab-btn"+(activitySubTab==="specialists"?" active":"")}
                  onClick=${()=>setActivitySubTab("specialists")}>Specialist${agents.filter(a=>a.id.startsWith("specialist-")).some(a=>a.status==="active")?" ●":""}</button>
                <button className=${"activity-sub-tab-btn"+(activitySubTab==="log"?" active":"")}
                  onClick=${()=>setActivitySubTab("log")}>Log</button>
              </div>`;
          })()}
          ${activitySubTab==="log" && html`
          <div className="activity-feed" ref=${activityFeedRef}>
            <div className="activity-log-toolbar">
              <span className="activity-count-label">${activityLog.length} event${activityLog.length!==1?"s":""}</span>
              ${activityLog.some(e => e.data?.mode === "agentic") && html`<span className="activity-mode-badge">Continuous session</span>`}
              <a className="btn ghost sm" href=${`/api/test-runs/${runId}/thinking-log/export`} download>Export log ↓</a>
              ${activityLog.length>0 && html`
                <button className="btn danger-outline sm"
                  disabled=${clearBusy==="activity"}
                  onClick=${async()=>{
                    if (!confirm("Clear all activity log entries for this run?")) return;
                    setClearBusy("activity"); setClearError(null);
                    try { await api.clearScanLog(runId); setActivityLog([]); setSitePlanData(null); setTokenUsage(null); }
                    catch(e) { setClearError(e.message); }
                    finally { setClearBusy(""); }
                  }}>${clearBusy==="activity"?"Clearing…":"Clear"}</button>`}
            </div>
            ${sitePlanData && html`
              <div className="site-plan-card">
                <div className="site-plan-header">
                  <span className="site-plan-label">Site Test Plan</span>
                  <span className="site-plan-badge">LLM Analysis</span>
                </div>
                <div className="site-plan-summary">${sitePlanData.app_summary}</div>
                ${(sitePlanData.hypotheses||[]).length > 0 && html`
                  <div className="site-plan-section">
                    <div className="site-plan-section-title">Attack Hypotheses</div>
                    <div className="hypotheses-list">
                      ${(sitePlanData.hypotheses||[]).map((h, i) => html`
                        <div key=${i} className="hypothesis-row">
                          <span className="owasp-badge">${h.owasp || "?"}</span>
                          <div className="hypothesis-body">
                            <div className="hypothesis-label">${h.hypothesis}</div>
                            <div className="hypothesis-desc">${h.description}</div>
                          </div>
                        </div>`)}
                    </div>
                  </div>`}
                ${(sitePlanData.critical_areas||[]).length > 0 && html`
                  <div className="site-plan-section">
                    <div className="site-plan-section-title">Critical Areas</div>
                    <div className="critical-areas-list">
                      ${(sitePlanData.critical_areas||[]).map((a, i) => html`<span key=${i} className="critical-area-tag">${a}</span>`)}
                    </div>
                  </div>`}
                ${sitePlanData.test_notes && html`
                  <div className="site-plan-section">
                    <div className="site-plan-section-title">Test Notes</div>
                    <div className="site-plan-notes">${sitePlanData.test_notes}</div>
                  </div>`}
              </div>`}
            ${activityLog.length === 0 && html`
              <div className="subtle" style=${{padding:"24px",textAlign:"center"}}>
                No scanner activity yet. Start a Dynamic Scan to begin.
              </div>`}
            ${activityLog.map(entry => {
              const PHASE_META = {
                site_plan:          { label: "Plan",      cls: "phase-plan" },
                page_plan:          { label: "Probes",    cls: "phase-probes" },
                page_followup:      { label: "Follow-up", cls: "phase-followup" },
                page_analysis:      { label: "Finding",   cls: entry.data?.finding_count > 0 ? "phase-finding" : "phase-ok" },
                sweep:              { label: "Sweep",     cls: "phase-sweep" },
                llm_request:        { label: "LLM ►",     cls: "phase-llm-req" },
                llm_response:       { label: "LLM ◄",     cls: "phase-llm-resp" },
                llm_heartbeat:      { label: "LLM ⟳",     cls: "phase-llm-wait" },
                credential_warning: { label: "⚠ Auth",   cls: "phase-warning" },
                thinking_step:      { label: entry.status === "deciding" ? "···" : "Step", cls: "phase-thinking" },
                thinking_analysis:  { label: "Report",    cls: "phase-reporting" },
                reporting_turn:     { label: "Turn",      cls: entry.data?.findings_this_turn > 0 ? "phase-finding" : "phase-ok" },
                post_scan_review:   { label: "Review",    cls: "phase-reporting" },
                post_review_turn:   { label: "Review",    cls: entry.data?.low_confidence > 0 ? "phase-warning" : "phase-ok" },
              };
              const _baseMeta = PHASE_META[entry.phase] || { label: entry.phase, cls: "phase-other" };
              const meta = entry.status === "error"
                ? { label: _baseMeta.label, cls: "phase-finding" }
                : _baseMeta;
              const suffix = entry.status === "complete" ? " ✓" : entry.status === "start" ? " …" : entry.status === "error" ? " ✗" : "";
              // Augment llm_request message to surface agentic context count
              const displayMessage = (
                entry.phase === "llm_request" && entry.data?.message_count != null
                  ? entry.message.replace(/\(.*messages in context\)/, `(${entry.data.message_count} msgs in context)`)
                  : entry.message
              );
              const hasThinkingDetail = entry.phase === "thinking_step" && !!(
                entry.data?.observation || entry.data?.hypothesis ||
                entry.data?.payload_purpose || entry.data?.payload_summary
              );
              const hasReportingDetail = entry.phase === "reporting_turn" && entry.data?.titles?.length > 0;
              const hasPayload = !!(entry.data?.prompt || entry.data?.raw_response || hasThinkingDetail || hasReportingDetail);
              const isExpanded = expandedLogIds.has(entry._id);
              return html`
                <div key=${entry._id}>
                  <div className=${"activity-entry" + (hasPayload ? " activity-entry--expandable" : "")}
                       onClick=${hasPayload ? () => toggleLogId(entry._id) : undefined}>
                    <span className="activity-ts">${entry._ts}</span>
                    <span className=${"activity-badge "+meta.cls}>${meta.label}${suffix}</span>
                    ${entry.page_url && html`<span className="activity-url mono" title=${entry.page_url}>${truncUrl(entry.page_url, 42)}</span>`}
                    <span className="activity-msg">${displayMessage}</span>
                    ${hasPayload && html`<span className="activity-expand-chevron">${isExpanded ? "▲" : "▼"}</span>`}
                  </div>
                  ${isExpanded && html`
                    <div className="activity-payload">
                      ${entry.data?.prompt && html`
                        <div className="activity-payload-label">Prompt</div>
                        <pre>${entry.data.prompt}</pre>`}
                      ${entry.data?.raw_response && html`
                        <div className="activity-payload-label" style=${{marginTop: entry.data?.prompt ? 8 : 0}}>Response</div>
                        <pre>${entry.data.raw_response}</pre>`}
                      ${hasThinkingDetail && html`
                        ${entry.data?.observation && html`
                          <div className="activity-payload-label">Observation</div>
                          <pre>${entry.data.observation}</pre>`}
                        ${entry.data?.hypothesis && html`
                          <div className="activity-payload-label" style=${{marginTop:6}}>Hypothesis</div>
                          <pre>${entry.data.hypothesis}</pre>`}
                        ${entry.data?.payload_purpose && html`
                          <div className="activity-payload-label" style=${{marginTop:6}}>Payload purpose</div>
                          <pre>${entry.data.payload_purpose}</pre>`}
                        ${entry.data?.payload_summary && html`
                          <div className="activity-payload-label" style=${{marginTop:6}}>Payload</div>
                          <pre>${entry.data.payload_summary}</pre>`}`}
                      ${(entry.phase === "reporting_turn" && entry.data?.titles?.length > 0) && html`
                        <div className="activity-payload-label">Issues identified this turn</div>
                        <ul style=${{margin:"4px 0 0 0",paddingLeft:18}}>
                          ${entry.data.titles.map((t,i) => html`<li key=${i}>${t}</li>`)}
                        </ul>`}
                    </div>`}
                </div>`;
            })}
          </div>`}
          ${activitySubTab==="specialists" && html`
          <div className="agents-panel">
            ${(()=>{
              const specialistAgents = agents.filter(ag => ag.id.startsWith("specialist-")).map(normalizeAgentForRun);
              if (specialistAgents.length === 0) return html`<div className="subtle" style=${{padding:"24px",textAlign:"center"}}>No specialist agents dispatched yet.</div>`;
              return specialistAgents.map(sa => {
                const saActive = sa.status === "active";
                const saTask = sa.currentTask || sa.taskHistory?.slice(-1)[0]?.task || "Initializing…";
                const saSteps = sa.stepHistory || [];
                const saExpanded = saSteps.length > 0 && !collapsedAgentIds.has(sa.id);
                const threadLabel = sa.id.replace("specialist-","").replace(/-([0-9]+)$/," #$1");
                return html`
                  <div key=${sa.id} className=${"agent-row"+(saActive?" agent-row--active":" agent-row--complete")+(saSteps.length>0?" agent-row--expandable":"")}
                       onClick=${saSteps.length>0 ? ()=>toggleAgentId(sa.id) : undefined}>
                    <span className=${"agent-dot"+(saActive?" agent-dot--active":"")} aria-hidden="true"></span>
                    <span className=${"agent-role-name"+(saActive?" agent-role-name--pulse":"")} style=${{textTransform:"capitalize"}}>${threadLabel}</span>
                    <span className=${"agent-badge"+(saActive?" agent-badge-active":" agent-badge-complete")}>
                      ${saActive?"ACTIVE":"DONE"}
                    </span>
                    <span className="agent-current-task" title=${saTask}>${saTask.length>90?saTask.slice(0,89)+"…":saTask}</span>
                    ${saSteps.length>0 && html`<span className="activity-expand-chevron">${saExpanded?"▲":"▼"}</span>`}
                    ${saSteps.length>0 && saExpanded && html`
                      <div className="agent-task-history">
                        ${saSteps.slice().reverse().map((s,i) => html`
                          <div key=${i} className="agent-history-entry">
                            <span className="activity-ts">${s.ts}</span>
                            <span className="agent-step-method">
                              ${s.method ? html`${s.method} ${s.url ? html`<span title=${s.url}>${truncUrl(s.url,80)}</span>` : ""}` : s.action_type || "tool"}
                            </span>
                            ${s.observation && html`<span className="agent-history-outcome" title=${s.observation}>${String(s.observation).slice(0,80)}</span>`}
                          </div>`)}
                      </div>`}
                  </div>`;
              });
            })()}
          </div>`}
          ${activitySubTab==="agents" && html`
          <div className="agents-panel">
            ${(()=>{
              const roster = defaultAgentRoster();
              // Container slots (specialist/burp/validator) must always render as
              // their placeholder so the multi-agent container row fires correctly.
              const CONTAINER_IDS = new Set(["specialist", "burp", "validator"]);
              const rosterAgents = roster.map(p =>
                CONTAINER_IDS.has(p.id) ? p : (agents.find(a => representsAgent(a, p)) || p)
              );
              const extras = agents.filter(a => !roster.some(p => representsAgent(a, p)));
              const shownAgents = [...rosterAgents, ...extras].map(normalizeAgentForRun);
              const renderRow = (a) => {
                // ── Specialist container row ────────────────────────────────
                if (a.id === "specialist") {
                  const specialistAgents = agents.filter(ag => ag.id.startsWith("specialist-")).map(normalizeAgentForRun);
                  const anyActive = specialistAgents.some(ag => ag.status === "active");
                  const containerStatus = anyActive ? "active" : (specialistAgents.length > 0 ? "complete" : "idle");
                  const activeCount = specialistAgents.filter(ag => ag.status === "active").length;
                  const doneCount = specialistAgents.length - activeCount;
                  const summaryTask = specialistAgents.length === 0
                    ? "No specialist dispatched"
                    : activeCount > 0 && doneCount > 0
                      ? `${activeCount} running, ${doneCount} complete`
                      : activeCount > 0
                        ? `${activeCount} thread${activeCount !== 1 ? "s" : ""} running`
                        : `${doneCount} thread${doneCount !== 1 ? "s" : ""} complete`;
                  const canExpand = specialistAgents.length > 0;
                  const isExpanded = canExpand && !collapsedAgentIds.has("specialist");
                  return html`
                    <div key="specialist" className=${"agent-row"+(anyActive?" agent-row--active":" agent-row--complete")+(canExpand?" agent-row--expandable":"")}
                         onClick=${canExpand ? ()=>toggleAgentId("specialist") : undefined}>
                      <span className=${"agent-dot"+(anyActive?" agent-dot--active":"")} aria-hidden="true"></span>
                      <span className=${"agent-role-name"+(anyActive?" agent-role-name--pulse":"")}>Specialist</span>
                      <span className=${"agent-badge"+(anyActive?" agent-badge-active":" agent-badge-complete")}>
                        ${anyActive ? "ACTIVE" : (specialistAgents.length > 0 ? "COMPLETE" : "IDLE")}
                      </span>
                      <span className="agent-current-task">${summaryTask}</span>
                      ${canExpand && html`<span className="activity-expand-chevron">${isExpanded?"▲":"▼"}</span>`}
                      ${canExpand && isExpanded && html`
                        <div className="agent-task-history">
                          ${specialistAgents.map(sa => {
                            const saActive = sa.status === "active";
                            const saTask = sa.currentTask || sa.taskHistory?.slice(-1)[0]?.task || "Initializing…";
                            return html`
                              <div key=${sa.id} className=${"agent-thread-row"+(saActive?" agent-thread-row--active":"")}>
                                <span className=${"agent-dot agent-dot--sm"+(saActive?" agent-dot--active":"")} aria-hidden="true"></span>
                                <span className="agent-thread-id">${sa.id.replace("specialist-","").replace(/-([0-9]+)$/," #$1")}</span>
                                <span className=${"agent-badge agent-badge--sm"+(saActive?" agent-badge-active":" agent-badge-complete")}>
                                  ${saActive?"ACTIVE":"DONE"}
                                </span>
                                <span className="agent-current-task" title=${saTask}>${saTask.length>90?saTask.slice(0,89)+"…":saTask}</span>
                              </div>`;
                          })}
                        </div>`}
                    </div>`;
                }
                // ── Validator container row ────────────────────────────────
                if (a.id === "validator") {
                  const validatorAgents = agents.filter(ag => ag.id.startsWith("validator-")).map(normalizeAgentForRun);
                  const anyActive = validatorAgents.some(ag => ag.status === "active");
                  const activeCount = validatorAgents.filter(ag => ag.status === "active").length;
                  const doneCount = validatorAgents.length - activeCount;
                  const summaryTask = validatorAgents.length === 0
                    ? "No validation running"
                    : activeCount > 0 && doneCount > 0
                      ? `${activeCount} validating, ${doneCount} complete`
                      : activeCount > 0
                        ? `${activeCount} finding${activeCount !== 1 ? "s" : ""} validating`
                        : `${doneCount} finding${doneCount !== 1 ? "s" : ""} validated`;
                  const canExpand = validatorAgents.length > 0;
                  const isExpanded = canExpand && !collapsedAgentIds.has("validator");
                  return html`
                    <div key="validator" className=${"agent-row"+(anyActive?" agent-row--active":" agent-row--complete")+(canExpand?" agent-row--expandable":"")}
                         onClick=${canExpand ? ()=>toggleAgentId("validator") : undefined}>
                      <span className=${"agent-dot"+(anyActive?" agent-dot--active":"")} aria-hidden="true"></span>
                      <span className=${"agent-role-name"+(anyActive?" agent-role-name--pulse":"")}>Validator</span>
                      <span className=${"agent-badge"+(anyActive?" agent-badge-active":" agent-badge-complete")}>
                        ${anyActive ? "ACTIVE" : (validatorAgents.length > 0 ? "COMPLETE" : "IDLE")}
                      </span>
                      <span className="agent-current-task">${summaryTask}</span>
                      ${canExpand && html`<span className="activity-expand-chevron">${isExpanded?"▲":"▼"}</span>`}
                      ${canExpand && isExpanded && html`
                        <div className="agent-task-history">
                          ${validatorAgents.map(va => {
                            const vaActive = va.status === "active";
                            const vaTask = va.currentTask || va.taskHistory?.slice(-1)[0]?.task || "Initializing…";
                            const vaOutcome = va.outcome || va.taskHistory?.slice(-1)[0]?.outcome;
                            const findingNum = va.id.replace("validator-", "");
                            return html`
                              <div key=${va.id} className=${"agent-thread-row"+(vaActive?" agent-thread-row--active":"")}>
                                <span className=${"agent-dot agent-dot--sm"+(vaActive?" agent-dot--active":"")} aria-hidden="true"></span>
                                <span className="agent-thread-id">Finding #${findingNum}</span>
                                <span className=${"agent-badge agent-badge--sm"+(vaActive?" agent-badge-active":" agent-badge-complete")}>
                                  ${vaActive?"ACTIVE":"DONE"}
                                </span>
                                <span className="agent-current-task" title=${vaTask}>${vaTask.length>90?vaTask.slice(0,89)+"…":vaTask}</span>
                                ${vaOutcome && !vaActive && html`<span className="agent-history-outcome">${vaOutcome}</span>`}
                              </div>`;
                          })}
                        </div>`}
                    </div>`;
                }
                // ── Burp container row ──────────────────────────────────────
                if (a.id === "burp") {
                  const burpAgents = agents.filter(ag => ag.id.startsWith("burp-")).map(normalizeAgentForRun);
                  const anyActive = burpAgents.some(ag => ag.status === "active");
                  const containerStatus = anyActive ? "active" : (burpAgents.length > 0 ? "complete" : "idle");
                  const activeCount = burpAgents.filter(ag => ag.status === "active").length;
                  const doneCount = burpAgents.length - activeCount;
                  const summaryTask = burpAgents.length === 0
                    ? "No active scan dispatched"
                    : activeCount > 0 && doneCount > 0
                      ? `${activeCount} scanning, ${doneCount} complete`
                      : activeCount > 0
                        ? `${activeCount} scan${activeCount !== 1 ? "s" : ""} running`
                        : `${doneCount} scan${doneCount !== 1 ? "s" : ""} complete`;
                  const canExpand = burpAgents.length > 0;
                  const isExpanded = canExpand && !collapsedAgentIds.has("burp");
                  return html`
                    <div key="burp" className=${"agent-row"+(anyActive?" agent-row--active":" agent-row--complete")+(canExpand?" agent-row--expandable":"")}
                         onClick=${canExpand ? ()=>toggleAgentId("burp") : undefined}>
                      <span className=${"agent-dot"+(anyActive?" agent-dot--active":"")} aria-hidden="true"></span>
                      <span className=${"agent-role-name"+(anyActive?" agent-role-name--pulse":"")}>Burp</span>
                      <span className=${"agent-badge"+(anyActive?" agent-badge-active":" agent-badge-complete")}>
                        ${anyActive ? "ACTIVE" : (burpAgents.length > 0 ? "COMPLETE" : "IDLE")}
                      </span>
                      <span className="agent-current-task">${summaryTask}</span>
                      ${canExpand && html`<span className="activity-expand-chevron">${isExpanded?"▲":"▼"}</span>`}
                      ${canExpand && isExpanded && html`
                        <div className="agent-task-history">
                          ${burpAgents.map(ba => {
                            const baActive = ba.status === "active";
                            const baTask = ba.currentTask || ba.taskHistory?.slice(-1)[0]?.task || "Initializing…";
                            return html`
                              <div key=${ba.id} className=${"agent-thread-row"+(baActive?" agent-thread-row--active":"")}>
                                <span className=${"agent-dot agent-dot--sm"+(baActive?" agent-dot--active":"")} aria-hidden="true"></span>
                                <span className="agent-thread-id">${ba.id.replace("burp-","")}</span>
                                <span className=${"agent-badge agent-badge--sm"+(baActive?" agent-badge-active":" agent-badge-complete")}>
                                  ${baActive?"ACTIVE":ba.status==="failed"?"FAILED":"DONE"}
                                </span>
                                <span className="agent-current-task" title=${baTask}>${baTask.length>90?baTask.slice(0,89)+"…":baTask}</span>
                              </div>`;
                          })}
                        </div>`}
                    </div>`;
                }
                // ── A.L.I.C.E custom row ────────────────────────────────────
                if (a.id === "alice") {
                  const isExpanded = !collapsedAgentIds.has("alice");
                  const isActive = a.status === "active";
                  const currentTask = a.currentTask;
                  return html`
                    <div key="alice" className="agent-row agent-row--alice-chat agent-row--expandable"
                         onClick=${() => toggleAgentId("alice")}>
                      <span className=${"agent-dot agent-dot--alice" + (isActive ? " agent-dot--active" : "")} aria-hidden="true"></span>
                      <span className=${"agent-role-name" + (isActive ? " agent-role-name--pulse" : "")}>A.L.I.C.E</span>
                      <span className=${"agent-badge" + (isActive ? " agent-badge-alice-active" : " agent-badge-alice-idle")}>
                        ${isActive ? "ACTIVE" : "STANDBY"}
                      </span>
                      <span className="agent-current-task" title=${currentTask}>${currentTask}</span>
                      <span className="activity-expand-chevron">${isExpanded ? "▲" : "▼"}</span>
                      ${isExpanded && html`
                        <div className="alice-chat-container" onClick=${e => e.stopPropagation()}>
                          <div className="alice-chat-tabs-bar">
                            ${aliceChats.map(tab => {
                              const isActiveTab = tab.id === activeAliceTabId;
                              return html`
                                <div
                                  key=${tab.id}
                                  className=${"alice-chat-tab-pill" + (isActiveTab ? " alice-chat-tab-pill--active" : "")}
                                  onClick=${() => setActiveAliceTabId(tab.id)}
                                >
                                  <span>${tab.title}</span>
                                  <span
                                    className="alice-chat-tab-close"
                                    onClick=${(e) => deleteAliceTab(tab.id, e)}
                                    title="Close Session"
                                  >
                                    ×
                                  </span>
                                </div>
                              `;
                            })}
                            <button
                              className="alice-chat-add-tab-btn"
                              onClick=${createAliceTab}
                              title="New Session"
                            >
                              +
                            </button>
                          </div>
                          <div className="alice-chat-history" style=${{ height: `${aliceChatHeight}px` }} ref=${(el) => { if (el) { el.scrollTop = el.scrollHeight; } }}>
                            ${aliceMessages.map((msg) => {
                              if (msg.type === "thinking") {
                                const isThinkExpanded = aliceExpandedThinkIds.has(msg.id);
                                return html`
                                  <div key=${msg.id} className="alice-msg-row">
                                    <div className="alice-msg-bubble--thinking">
                                      <div className="alice-thinking-header" onClick=${() => {
                                        setAliceExpandedThinkIds(prev => {
                                          const next = new Set(prev);
                                          next.has(msg.id) ? next.delete(msg.id) : next.add(msg.id);
                                          return next;
                                        });
                                      }}>
                                        <${IconBrain}/>
                                        <span>Thought Process ${isThinkExpanded ? "▲" : "▼"}</span>
                                        <span style=${{ marginLeft: "auto", fontSize: "9px", opacity: 0.6 }}>${msg.ts}</span>
                                      </div>
                                      ${isThinkExpanded && html`
                                        <div className="alice-thinking-body">
                                          ${renderAliceBlocks(msg.text, true)}
                                        </div>
                                      `}
                                    </div>
                                  </div>
                                `;
                              }
                              const isUser = msg.sender === "user";
                              return html`
                                <div key=${msg.id} className=${"alice-msg-row" + (isUser ? " alice-msg-row--user" : " alice-msg-row--alice")}>
                                  <div className=${"alice-msg-bubble" + (isUser ? " alice-msg-bubble--user" : " alice-msg-bubble--alice")}>
                                    <div>
                                      ${isUser ? renderMarkdown(msg.text) : renderAliceBlocks(msg.text, false)}
                                    </div>
                                    <div className="alice-msg-meta">
                                      <span>${msg.ts}</span>
                                    </div>
                                  </div>
                                </div>
                              `;
                            })}
                            ${aliceIsThinking && html`
                              <div className="alice-msg-row alice-msg-row--alice">
                                <div className="alice-typing-bubble">
                                  <div className="alice-typing-dot"></div>
                                  <div className="alice-typing-dot"></div>
                                  <div className="alice-typing-dot"></div>
                                </div>
                              </div>
                            `}
                          </div>
                          
                          <div className="alice-chat-resizer" onMouseDown=${startAliceResize}></div>
                          
                          <div className="alice-chat-input-bar">
                            <input
                              className="alice-chat-input"
                              placeholder="Direct A.L.I.C.E. on what to test..."
                              value=${aliceInputText}
                              disabled=${aliceIsThinking}
                              onKeyDown=${(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                  e.preventDefault();
                                  handleAliceSend();
                                }
                              }}
                              onInput=${e => setAliceInputText(e.target.value)}
                            />
                            ${aliceIsThinking ? html`
                              <button
                                className="alice-chat-stop-btn"
                                onClick=${handleAliceStop}
                                title="Stop Generation"
                              >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                  <rect x="4" y="4" width="16" height="16" rx="1" ry="1"></rect>
                                </svg>
                              </button>
                            ` : html`
                              <button
                                className="alice-chat-input-btn"
                                disabled=${!aliceInputText.trim()}
                                onClick=${handleAliceSend}
                                title="Send Instruction"
                              >
                                <${IconSend}/>
                              </button>
                            `}
                          </div>
                        </div>
                      `}
                    </div>
                  `;
                }
                const isActive = a.status==="active";
                const roleLabel = agentRoleLabel(a);
                const currentTask = agentCurrentTask(a);
                const crawlEvents = agentCrawlEvents(a);
                const taskHistory = agentTaskHistory(a);
                const canExpand = (a.id === "crawler" && crawlEvents.length > 0) ||
                  taskHistory.length > 1 ||
                  taskHistory.some(h => h.outcome);
                const isExpanded = canExpand && !collapsedAgentIds.has(a.id);
                return html`
                  <div key=${a.id} className=${"agent-row"+(isActive?" agent-row--active":" agent-row--complete")+(canExpand?" agent-row--expandable":"")}
                       onClick=${canExpand ? ()=>toggleAgentId(a.id) : undefined}>
                    <span className=${"agent-dot"+(isActive?" agent-dot--active":"")} aria-hidden="true"></span>
                    <span className=${"agent-role-name"+(isActive?" agent-role-name--pulse":"")}>
                      ${roleLabel}${a.id.includes("-")&&!["scanner","crawler"].includes(a.id)&&!a.id.startsWith("burp-")?html`<br/><span className="agent-role-sub">${a.id.replace(/^[a-z]+-/,"").replace(/-/g," ")}</span>`:""}
                    </span>
                    <span className=${"agent-badge"+(isActive?" agent-badge-active":" agent-badge-complete")}>
                      ${agentStatusLabel(a)}
                    </span>
                    <span className="agent-current-task" title=${currentTask}>${currentTask}</span>
                    ${canExpand && html`<span className="activity-expand-chevron">${isExpanded?"▲":"▼"}</span>`}
                    ${canExpand && isExpanded && html`
                      <div className="agent-task-history">
                        ${a.id === "crawler" && crawlEvents.length > 0 ? html`
                          ${crawlEvents.slice().reverse().map((h,i)=>html`
                            <div key=${i} className="agent-history-entry agent-history-entry--crawl">
                              <span className="activity-ts">${h.ts}</span>
                              <span className="agent-history-user">${h.username || "anonymous"}</span>
                              <span className="agent-history-task mono" title=${h.url || ""}>
                                ${h.done ? `Finished (${h.pagesVisited || 0} pg)` : truncUrl(h.url || "", 112)}
                              </span>
                            </div>`)}
                        ` : html`
                          ${taskHistory.slice().reverse().map((h,i)=>html`
                            <div key=${i} className="agent-history-entry">
                              <span className="activity-ts">${h.ts}</span>
                              <span className="agent-history-task">${h.task}</span>
                              ${h.outcome && html`<span className="agent-history-outcome">${h.outcome}</span>`}
                            </div>`)}
                        `}
                      </div>`}
                  </div>`;
              };
              return html`
                ${shownAgents.map(renderRow)}`;
            })()}
          </div>`}
        </div>`}

      ${activeTab==="traffic" && html`
        <div className="traffic-panel">
          <div className="traffic-toolbar">
            <input className="traffic-filter" type="text" placeholder="Filter by URL, method or status…"
              value=${trafficFilter} onInput=${e=>setTrafficFilter(e.target.value)}/>
            <span className="traffic-count-label">${filteredTraffic.length} shown${trafficTotal>filteredTraffic.length ? ` of ${trafficTotal}` : ""}</span>
            <label className="traffic-autoscroll">
              <input type="checkbox" checked=${autoScroll} onChange=${e=>setAutoScroll(e.target.checked)}/>
              Auto-scroll
            </label>
            <button className="btn ghost sm" onClick=${async ()=>{ try { await api.clearTraffic(runId); } catch(_){} setTraffic([]); lastTrafficIdRef.current=0; setSelectedTraffic(null); }}>Clear</button>
          </div>

          <div className="traffic-table-wrap" ref=${trafficTableRef}>
            <table className="traffic-table">
              <colgroup>${trafficColW.map((w,i)=>html`<col key=${i} style=${{width:w!=null?w+"px":undefined}}/>`)}</colgroup>
              <thead>
                <tr>
                  <th className="sortable tr-num" onClick=${()=>onTrafficSort("_seq")}>#${sortArrow("_seq")}<div className="col-rh" onMouseDown=${e=>startTrafficResize(0,e)} onClick=${e=>e.stopPropagation()}/></th>
                  <th className="sortable tr-ts"  onClick=${()=>onTrafficSort("created_at")}>Time${sortArrow("created_at")}<div className="col-rh" onMouseDown=${e=>startTrafficResize(1,e)} onClick=${e=>e.stopPropagation()}/></th>
                  <th className="sortable" onClick=${()=>onTrafficSort("source")}>Source${sortArrow("source")}<div className="col-rh" onMouseDown=${e=>startTrafficResize(2,e)} onClick=${e=>e.stopPropagation()}/></th>
                  <th className="sortable" onClick=${()=>onTrafficSort("username")}>User${sortArrow("username")}<div className="col-rh" onMouseDown=${e=>startTrafficResize(3,e)} onClick=${e=>e.stopPropagation()}/></th>
                  <th className="sortable" onClick=${()=>onTrafficSort("method")}>Method${sortArrow("method")}<div className="col-rh" onMouseDown=${e=>startTrafficResize(4,e)} onClick=${e=>e.stopPropagation()}/></th>
                  <th className="sortable" onClick=${()=>onTrafficSort("status")}>Status${sortArrow("status")}<div className="col-rh" onMouseDown=${e=>startTrafficResize(5,e)} onClick=${e=>e.stopPropagation()}/></th>
                  <th className="sortable" onClick=${()=>onTrafficSort("url")}>URL${sortArrow("url")}<div className="col-rh" onMouseDown=${e=>startTrafficResize(6,e)} onClick=${e=>e.stopPropagation()}/></th>
                  <th className="sortable tr-dur" onClick=${()=>onTrafficSort("duration_ms")}>Duration${sortArrow("duration_ms")}<div className="col-rh" onMouseDown=${e=>startTrafficResize(7,e)} onClick=${e=>e.stopPropagation()}/></th>
                </tr>
              </thead>
              <tbody>
                ${filteredTraffic.map((e,i) => html`
                  <tr key=${e.id}
                    className=${"traffic-row"+(selectedTraffic?.id===e.id?" selected":"")}
                    onClick=${()=>setSelectedTraffic(selectedTraffic?.id===e.id?null:e)}>
                    <td className="tr-num">${e._seq??i+1}</td>
                    <td className="tr-ts">${fmtTs(e.created_at)}</td>
                    <td><span className=${"src-badge src-"+e.source}>${e.source}</span></td>
                    <td className="tr-user">${e.username||"-"}</td>
                    <td className="tr-method">${e.method}</td>
                    <td><span className=${"status-pill "+statusClass(e.status)}>${e.status??"-"}</span></td>
                    <td className="tr-url" title=${e.url}>${e.url}</td>
                    <td className="tr-dur">${e.duration_ms!=null?e.duration_ms+"ms":"-"}</td>
                  </tr>`)}
              </tbody>
            </table>
            ${filteredTraffic.length===0 && html`
              <div className="subtle" style=${{padding:"24px",textAlign:"center"}}>
                ${run?.status==="running"||isDynamicScanActive(thinkingStatus?.status)
                  ? "Capturing traffic…" : "No traffic recorded yet. Start a crawl or scan."}
              </div>`}
          </div>

          ${selectedTraffic && html`
            <div className="traffic-detail">
              <div className="traffic-pane">
                <div className="traffic-pane-label">REQUEST — ${selectedTraffic.method} ${selectedTraffic.url}</div>
                <pre className="traffic-raw">${fmtRequest(selectedTraffic)}</pre>
              </div>
              <div className="traffic-pane">
                <div className="traffic-pane-label">RESPONSE — ${selectedTraffic.status??"-"} ${selectedTraffic.duration_ms!=null?"("+selectedTraffic.duration_ms+"ms)":""}</div>
                <pre className="traffic-raw">${fmtResponse(selectedTraffic)}</pre>
              </div>
            </div>`}
        </div>`}
    </div>`;
}

function TargetIntelligencePanel({ data, selectedKind, onKind, refresh, onClear, clearing }) {
  const [intelColW, startIntelResize] = useColResize("colw:intel", [116, 86, 120, null, 130, 82]);
  const counts = data?.counts || {};
  const items = data?.items || [];
  const kinds = ["", ...Object.keys(counts).sort()];
  const total = Object.values(counts).reduce((a,b)=>a+b,0);
  const KIND_LABELS = {
    endpoint:"Endpoints",
    form:"Forms",
    input:"Inputs",
    script:"Scripts",
    storage_key:"Storage Keys",
    id:"IDs",
    response_field:"Response Fields",
  };
  const kindLabel = (k) => k ? (KIND_LABELS[k] || k.replace(/_/g, " ")) : "All";
  const compactMeta = (meta) => {
    if (!meta || Object.keys(meta).length === 0) return "";
    const shown = Object.entries(meta)
      .filter(([k]) => !["fields"].includes(k))
      .slice(0, 5)
      .map(([k,v]) => `${k}: ${Array.isArray(v) ? v.length+" item(s)" : String(v).slice(0,80)}`);
    return shown.join(" · ");
  };
  return html`
    <div className="intel-panel">
      <div className="intel-toolbar">
        <div className="intel-title">
          <span>Target Intelligence</span>
          <span className="subtle">${total} item${total===1?"":"s"} discovered during crawl</span>
        </div>
        <div className="intel-filter">
          <label>Kind</label>
          <select className="select" value=${selectedKind} onChange=${e=>onKind(e.target.value)}>
            ${kinds.map(k => html`<option key=${k||"all"} value=${k}>${kindLabel(k)}${k ? ` (${counts[k]||0})` : ""}</option>`)}
          </select>
          <button className="btn ghost sm" onClick=${refresh}>Refresh</button>
          ${total>0 && html`<button className="btn danger-outline sm" disabled=${clearing} onClick=${onClear}>${clearing?"Clearing…":"Clear"}</button>`}
        </div>
      </div>

      <div className="intel-counts">
        ${Object.entries(counts).sort(([a],[b])=>a.localeCompare(b)).map(([kind,count]) => html`
          <button key=${kind} className=${"intel-count-card"+(selectedKind===kind?" active":"")} onClick=${()=>onKind(selectedKind===kind?"":kind)}>
            <span className="intel-count-value">${count}</span>
            <span className="intel-count-label">${kindLabel(kind)}</span>
          </button>`)}
        ${total===0 && html`<div className="subtle">No target intelligence has been collected yet. Start or restart a crawl to populate the inventory.</div>`}
      </div>

      <div className="intel-table-wrap">
        <table className="intel-table">
          <colgroup>${intelColW.map((w,i)=>html`<col key=${i} style=${{width:w!=null?w+"px":undefined}}/>`)}</colgroup>
          <thead>
            <tr>
              <th>Kind <div className="col-rh" onMouseDown=${e=>startIntelResize(0,e)} onClick=${e=>e.stopPropagation()}/></th>
              <th>Method <div className="col-rh" onMouseDown=${e=>startIntelResize(1,e)} onClick=${e=>e.stopPropagation()}/></th>
              <th>Key <div className="col-rh" onMouseDown=${e=>startIntelResize(2,e)} onClick=${e=>e.stopPropagation()}/></th>
              <th>Value <div className="col-rh" onMouseDown=${e=>startIntelResize(3,e)} onClick=${e=>e.stopPropagation()}/></th>
              <th>Source <div className="col-rh" onMouseDown=${e=>startIntelResize(4,e)} onClick=${e=>e.stopPropagation()}/></th>
              <th>Conf. <div className="col-rh" onMouseDown=${e=>startIntelResize(5,e)} onClick=${e=>e.stopPropagation()}/></th>
            </tr>
          </thead>
          <tbody>
            ${items.map(item => html`
              <tr key=${item.id}>
                <td><span className="intel-kind">${kindLabel(item.kind)}</span></td>
                <td><span className="mono">${item.method || "-"}</span></td>
                <td>
                  <div className="intel-primary" title=${item.key}>${item.key || "—"}</div>
                  ${item.url && html`<div className="intel-url mono" title=${item.url}>${truncUrl(item.url, 72)}</div>`}
                </td>
                <td>
                  <div className="intel-value" title=${item.value}>${item.value || "—"}</div>
                  ${item.evidence && html`<div className="intel-evidence">${item.evidence}</div>`}
                  ${compactMeta(item.item_metadata) && html`<div className="intel-meta">${compactMeta(item.item_metadata)}</div>`}
                </td>
                <td>${item.source}</td>
                <td>${Math.round((item.confidence ?? 0) * 100)}%</td>
              </tr>`)}
          </tbody>
        </table>
        ${items.length===0 && total>0 && html`
          <div className="subtle" style=${{padding:"24px",textAlign:"center"}}>No items match this filter.</div>`}
      </div>
    </div>`;
}

function ScannerSessionsPanel({ runId, data, refresh }) {
  const [sessColW, startSessResize] = useColResize("colw:sessions", [150, 100, 130, null, 180, 170, 150]);
  const sessions = data?.sessions || [];
  const counts = data?.counts || {};
  const kinds = Object.entries(counts)
    .filter(([kind]) => !["total", "active", "inactive"].includes(kind))
    .sort(([a],[b]) => a.localeCompare(b));
  const fmtAge = (iso) => {
    if (!iso) return "—";
    try { return parseDate(iso).toLocaleString(); } catch { return iso; }
  };
  const renameSession = async (session) => {
    const next = prompt("Session label", session.label);
    if (next === null) return;
    try {
      await api.updateScannerSession(runId, session.id, { label: next });
      await refresh();
    } catch(e) { alert(e.message); }
  };
  const setSessionActive = async (session, isActive) => {
    const verb = isActive ? "Reactivate" : "Deactivate";
    if (!confirm(`${verb} session "${session.label}"?`)) return;
    try {
      await api.updateScannerSession(runId, session.id, { is_active: isActive });
      await refresh();
    } catch(e) { alert(e.message); }
  };
  return html`
    <div className="intel-panel">
      <div className="intel-toolbar">
        <div className="intel-title">
          <span>Scanner Sessions</span>
          <span className="subtle">${counts.total || 0} durable label${(counts.total || 0)===1?"":"s"}; auth material is redacted</span>
        </div>
        <div className="intel-filter">
          <button className="btn ghost sm" onClick=${refresh}>Refresh</button>
        </div>
      </div>

      <div className="intel-counts">
        <div className="task-summary-card"><span className="task-summary-value">${counts.total || 0}</span><span className="task-summary-label">Total</span></div>
        <div className="task-summary-card"><span className="task-summary-value">${counts.active || 0}</span><span className="task-summary-label">Active</span></div>
        ${kinds.map(([kind,count]) => html`
          <div key=${kind} className="task-summary-card">
            <span className="task-summary-value">${count}</span>
            <span className="task-summary-label">${kind.replace(/_/g," ")}</span>
          </div>`)}
        ${sessions.length===0 && html`<div className="subtle">No scanner sessions have been recorded yet. Start a Structured or Dynamic Scan to populate durable session labels.</div>`}
      </div>

      <div className="intel-table-wrap">
        <table className="intel-table scanner-session-table">
          <colgroup>${sessColW.map((w,i)=>html`<col key=${i} style=${{width:w!=null?w+"px":undefined}}/>`)}</colgroup>
          <thead>
            <tr>
              <th>Label <div className="col-rh" onMouseDown=${e=>startSessResize(0,e)} onClick=${e=>e.stopPropagation()}/></th>
              <th>Kind <div className="col-rh" onMouseDown=${e=>startSessResize(1,e)} onClick=${e=>e.stopPropagation()}/></th>
              <th>User <div className="col-rh" onMouseDown=${e=>startSessResize(2,e)} onClick=${e=>e.stopPropagation()}/></th>
              <th>Auth material <div className="col-rh" onMouseDown=${e=>startSessResize(3,e)} onClick=${e=>e.stopPropagation()}/></th>
              <th>Source <div className="col-rh" onMouseDown=${e=>startSessResize(4,e)} onClick=${e=>e.stopPropagation()}/></th>
              <th>Updated <div className="col-rh" onMouseDown=${e=>startSessResize(5,e)} onClick=${e=>e.stopPropagation()}/></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${sessions.map(s => html`
              <tr key=${s.id}>
                <td><div className="intel-primary mono">${s.label}</div>${!s.is_active && html`<span className="task-status status-skipped">inactive</span>`}</td>
                <td><span className=${"task-status status-"+(s.kind === "anonymous" ? "skipped" : "confirmed")}>${s.kind}</span></td>
                <td>${s.username || "—"}${s.credential_id ? html`<div className="intel-meta">credential #${s.credential_id}</div>` : ""}</td>
                <td>
                  <div className="session-material-row">
                    <span className="intel-kind">Cookies</span>
                    <span>${(s.cookie_names||[]).length ? s.cookie_names.join(", ") : "none"}</span>
                  </div>
                  <div className="session-material-row">
                    <span className="intel-kind">Headers</span>
                    <span>${(s.header_names||[]).length ? s.header_names.join(", ") : "none"}</span>
                  </div>
                  ${s.token_hint && html`<div className="intel-meta">token: ${s.token_hint}</div>`}
                </td>
                <td>${s.source || "scanner"}</td>
                <td>${fmtAge(s.updated_at)}</td>
                <td>
                  <div className="row session-actions">
                    <button className="btn secondary sm" onClick=${()=>renameSession(s)}>Rename</button>
                    ${s.is_active
                      ? html`<button className="btn danger-outline sm" onClick=${()=>setSessionActive(s, false)}>Deactivate</button>`
                      : html`<button className="btn secondary sm" onClick=${()=>setSessionActive(s, true)}>Reactivate</button>`}
                  </div>
                </td>
              </tr>`)}
          </tbody>
        </table>
      </div>
    </div>`;
}

function TaskGraphPanel({ data, reconSummary, subTab, onSubTab, refresh, seed, onClear, clearing }) {
  const [taskColW, startTaskResize] = useColResize("colw:tasks", [88, 84, null, 86, 200]);
  const hypotheses = data?.hypotheses || [];
  const tasks = data?.tasks || [];
  const counts = data?.counts || {};
  const tasksByHypothesis = tasks.reduce((acc, task) => {
    const key = task.hypothesis_id || "none";
    (acc[key] = acc[key] || []).push(task);
    return acc;
  }, {});
  const statusLabel = (status) => (status || "queued").replace(/_/g, " ");
  const taskStatusCounts = ["queued", "running", "blocked", "done", "skipped"]
    .map(status => [status, counts["task_"+status] || 0])
    .filter(([, count]) => count > 0);
  const orphanTasks = tasksByHypothesis.none || [];
  const priorityTone = (p) => p >= 88 ? "high" : p >= 78 ? "medium" : "low";
  const activeSubTab = subTab || "attack-surface";
  return html`
    <div className="task-panel">
      <div className="tasks-subtab-bar">
        <button className=${"tasks-subtab-btn"+(activeSubTab==="attack-surface"?" active":"")}
          onClick=${()=>onSubTab("attack-surface")}>
          Attack Surface${reconSummary?.attack_classes?.length>0 ? html` <span className="traffic-count">${reconSummary.attack_classes.length}</span>` : ""}
        </button>
        <button className=${"tasks-subtab-btn"+(activeSubTab==="task-queue"?" active":"")}
          onClick=${()=>onSubTab("task-queue")}>
          Task Queue${counts.tasks>0 ? html` <span className="traffic-count">${counts.tasks}</span>` : ""}
        </button>
      </div>

      ${activeSubTab==="attack-surface" && html`<${AttackSurfacePanel} summary=${reconSummary}/>`}

      ${activeSubTab==="task-queue" && html`
      <div className="intel-toolbar">
        <div className="intel-title">
          <span>Hypothesis & Task Graph</span>
          <span className="subtle">${hypotheses.length} hypotheses · ${tasks.length} tasks</span>
        </div>
        <div className="intel-filter">
          <button className="btn ghost sm" onClick=${seed}>Seed from intelligence</button>
          <button className="btn ghost sm" onClick=${refresh}>Refresh</button>
          ${(hypotheses.length>0||tasks.length>0) && html`<button className="btn danger-outline sm" disabled=${clearing} onClick=${onClear}>${clearing?"Clearing…":"Clear"}</button>`}
        </div>
      </div>

      <div className="task-summary">
        <div className="task-summary-card">
          <span className="task-summary-value">${counts.hypotheses || 0}</span>
          <span className="task-summary-label">Hypotheses</span>
        </div>
        <div className="task-summary-card">
          <span className="task-summary-value">${counts.tasks || 0}</span>
          <span className="task-summary-label">Tasks</span>
        </div>
        ${taskStatusCounts.map(([status, count]) => html`
          <div key=${status} className="task-summary-card">
            <span className="task-summary-value">${count}</span>
            <span className="task-summary-label">${statusLabel(status)}</span>
          </div>`)}
        ${tasks.length===0 && html`<div className="subtle">No task graph yet. Seed it from collected target intelligence, or start a Dynamic Scan.</div>`}
      </div>

      <div className="task-list">
        ${hypotheses.map(h => {
          const groupedTasks = tasksByHypothesis[h.id] || [];
          return html`
            <div key=${h.id} className="hypothesis-card">
              <div className="hypothesis-card-head">
                <div>
                  <div className="hypothesis-card-title">${h.title}</div>
                  <div className="hypothesis-card-meta">
                    <span className=${"task-priority "+priorityTone(h.priority)}>P${h.priority}</span>
                    <span className=${"task-status status-"+h.status}>${statusLabel(h.status)}</span>
                    ${h.owasp_category && html`<span className="owasp-badge">${h.owasp_category}</span>`}
                    ${h.attack_area && html`<span>${h.attack_area}</span>`}
                    <span>${Math.round((h.confidence || 0) * 100)}% confidence</span>
                  </div>
                </div>
                <span className="task-count-pill">${groupedTasks.length} task${groupedTasks.length===1?"":"s"}</span>
              </div>
              <div className="hypothesis-rationale">${h.rationale || h.description}</div>
              ${groupedTasks.length > 0 && html`
                <div className="task-table-wrap">
                  <table className="task-table" style=${{tableLayout:"fixed"}}>
                    <colgroup>${taskColW.map((w,i)=>html`<col key=${i} style=${{width:w!=null?w+"px":undefined}}/>`)}</colgroup>
                    <thead>
                      <tr>
                        <th>Status <div className="col-rh" onMouseDown=${e=>startTaskResize(0,e)} onClick=${e=>e.stopPropagation()}/></th>
                        <th>Type <div className="col-rh" onMouseDown=${e=>startTaskResize(1,e)} onClick=${e=>e.stopPropagation()}/></th>
                        <th>Task <div className="col-rh" onMouseDown=${e=>startTaskResize(2,e)} onClick=${e=>e.stopPropagation()}/></th>
                        <th>Method <div className="col-rh" onMouseDown=${e=>startTaskResize(3,e)} onClick=${e=>e.stopPropagation()}/></th>
                        <th>Target <div className="col-rh" onMouseDown=${e=>startTaskResize(4,e)} onClick=${e=>e.stopPropagation()}/></th>
                      </tr>
                    </thead>
                    <tbody>
                      ${groupedTasks.map(task => html`
                        <tr key=${task.id}>
                          <td><span className=${"task-status status-"+task.status}>${statusLabel(task.status)}</span></td>
                          <td><span className="intel-kind">${task.task_type}</span></td>
                          <td>
                            <div className="intel-primary">${task.title}</div>
                            <div className="intel-evidence">${task.result_summary || task.description}</div>
                            ${task.evidence && html`<div className="task-evidence">${task.evidence}</div>`}
                          </td>
                          <td><span className="mono">${task.method || "-"}</span></td>
                          <td><span className="mono task-target" title=${task.target_url}>${task.target_url ? truncUrl(task.target_url, 86) : "—"}</span></td>
                        </tr>`)}
                    </tbody>
                  </table>
                </div>`}
            </div>`;
        })}
        ${orphanTasks.length > 0 && html`
          <div className="hypothesis-card">
            <div className="hypothesis-card-title">Unlinked Tasks</div>
            <div className="task-table-wrap">
              <table className="task-table">
                <tbody>
                  ${orphanTasks.map(task => html`
                    <tr key=${task.id}>
                      <td><span className=${"task-status status-"+task.status}>${statusLabel(task.status)}</span></td>
                      <td>${task.title}</td>
                      <td><span className="mono">${task.target_url}</span></td>
                    </tr>`)}
                </tbody>
              </table>
            </div>
          </div>`}
      </div>`}
    </div>`;
}

function AttackSurfacePanel({ summary }) {
  const [expanded, setExpanded] = useState({ trust_zones: true, attack_classes: true, meta: false });
  const toggle = (key) => setExpanded(prev => ({...prev, [key]: !prev[key]}));
  const priorityTone = (p) => p >= 88 ? "high" : p >= 78 ? "medium" : "low";

  if (!summary) {
    return html`
      <div className="attack-surface-empty">
        <span className="subtle">No attack surface summary yet. Run a Dynamic Scan to generate one.</span>
      </div>`;
  }

  const { trust_zones = {}, attack_classes = [], tech_stack = [], credential_roles = [], entry_points = [] } = summary;
  const zoneEntries = Object.entries(trust_zones).filter(([,urls]) => urls?.length > 0);

  return html`
    <div className="attack-surface-panel">

        <div className="attack-surface-section">
          <div className="attack-surface-section-head" onClick=${()=>toggle("trust_zones")}>
            <span className="attack-surface-toggle">${expanded.trust_zones ? "▾" : "▸"}</span>
            <span className="attack-surface-section-title">Trust Zones</span>
            ${zoneEntries.map(([zone, urls]) => html`
              <span key=${zone} className=${"zone-badge zone-"+zone}>${zone.toUpperCase()} (${urls.length})</span>`)}
          </div>
          ${expanded.trust_zones && html`
            <div className="attack-surface-body">
              ${zoneEntries.map(([zone, urls]) => html`
                <div key=${zone} className="trust-zone-group">
                  <div className=${"trust-zone-label zone-"+zone}>${zone.toUpperCase()}</div>
                  <div className="trust-zone-urls">
                    ${urls.slice(0,8).map(url => html`<div key=${url} className="mono trust-zone-url" title=${url}>${truncUrl(url,90)}</div>`)}
                    ${urls.length > 8 && html`<div className="subtle">+${urls.length - 8} more</div>`}
                  </div>
                </div>`)}
            </div>`}
        </div>

        <div className="attack-surface-section">
          <div className="attack-surface-section-head" onClick=${()=>toggle("attack_classes")}>
            <span className="attack-surface-toggle">${expanded.attack_classes ? "▾" : "▸"}</span>
            <span className="attack-surface-section-title">Attack Classes</span>
            <span className="subtle">${attack_classes.length} identified</span>
          </div>
          ${expanded.attack_classes && html`
            <div className="attack-surface-body">
              ${attack_classes.map(cls => {
                const urls = cls.entry_point_urls || [];
                return html`
                  <div key=${cls.id} className="attack-class-card">
                    <div className="attack-class-head">
                      <span className=${"task-priority "+priorityTone(cls.priority)}>P${cls.priority}</span>
                      <span className="owasp-badge">${cls.owasp}</span>
                      <span className="attack-class-id">${cls.id?.replace(/_/g," ")}</span>
                    </div>
                    <div className="attack-class-rationale">${cls.rationale}</div>
                    ${urls.length > 0 && html`
                      <div className="attack-class-urls">
                        ${urls.slice(0,4).map(url => html`<span key=${url} className="mono attack-class-url" title=${url}>${truncUrl(url,70)}</span>`)}
                        ${urls.length > 4 && html`<span className="subtle">+${urls.length-4} more</span>`}
                      </div>`}
                  </div>`;
              })}
            </div>`}
        </div>

        <div className="attack-surface-section">
          <div className="attack-surface-section-head" onClick=${()=>toggle("meta")}>
            <span className="attack-surface-toggle">${expanded.meta ? "▾" : "▸"}</span>
            <span className="attack-surface-section-title">Tech Stack & Credentials</span>
          </div>
          ${expanded.meta && html`
            <div className="attack-surface-body">
              ${tech_stack.length > 0 && html`
                <div className="meta-row">
                  <span className="meta-label">Tech stack:</span>
                  ${tech_stack.map(t => html`<span key=${t} className="intel-kind">${t}</span>`)}
                </div>`}
              ${credential_roles.length > 0 && html`
                <div className="meta-row">
                  <span className="meta-label">Credential roles:</span>
                  ${credential_roles.map(r => html`<span key=${r} className="intel-kind">${r}</span>`)}
                </div>`}
              <div className="meta-row">
                <span className="meta-label">Entry points:</span>
                <span>${entry_points.length} total</span>
              </div>
            </div>`}
        </div>

    </div>`;
}

// ── Settings ──────────────────────────────────────────────────────────────────

function ScannerPolicyFields({ form, upd, disabled=false }) {
  return html`
    <div className="form-section-title">Mode</div>
    <div className="field">
      <label>Scan mode</label>
      <select className="select" disabled=${disabled} value=${form.scan_mode} onChange=${e=>upd({scan_mode:e.target.value})}>
        ${SCAN_MODE_OPTIONS.map(([value,label])=>html`<option key=${value} value=${value}>${label}</option>`)}
      </select>
    </div>
    <${ScanModeDefinitions} selected=${form.scan_mode}/>
    <div className="divider"/>
    <div className="form-section-title">Limits</div>
    <div className="two-col">
      <div className="field"><label>Max probes per page</label>
        <input type="number" disabled=${disabled} min="0" max="500" value=${form.max_probes_per_page} onChange=${e=>upd({max_probes_per_page:e.target.value})}/></div>
      <div className="field"><label>Request timeout (seconds)</label>
        <input type="number" disabled=${disabled} min="1" max="120" step="0.5" value=${form.request_timeout_s} onChange=${e=>upd({request_timeout_s:e.target.value})}/></div>
      <div className="field"><label>Minimum delay (seconds)</label>
        <input type="number" disabled=${disabled} min="0" max="60" step="0.05" value=${form.min_delay_s} onChange=${e=>upd({min_delay_s:e.target.value})}/></div>
      <div className="field"><label>Max request body bytes</label>
        <input type="number" disabled=${disabled} min="0" max=${10*1024*1024} value=${form.max_request_body_bytes} onChange=${e=>upd({max_request_body_bytes:e.target.value})}/></div>
    </div>
    <div className="field"><label>Response body read limit bytes</label>
      <input type="number" disabled=${disabled} min="1024" max=${10*1024*1024} value=${form.response_body_read_limit_bytes} onChange=${e=>upd({response_body_read_limit_bytes:e.target.value})}/></div>
    <div className="divider"/>
    <div className="form-section-title">Scope</div>
    <div className="two-col">
      <div className="field"><label>Allowed schemes</label>
        <input type="text" disabled=${disabled} value=${form.allowed_schemes} onChange=${e=>upd({allowed_schemes:e.target.value})}/></div>
      <div className="field"><label>Blocked headers</label>
        <input type="text" disabled=${disabled} value=${form.blocked_headers} onChange=${e=>upd({blocked_headers:e.target.value})}/></div>
    </div>
    <label className="toggle-row">
      <input type="checkbox" disabled=${disabled} checked=${form.follow_redirects} onChange=${e=>upd({follow_redirects:e.target.checked})}/>
      <span>Follow redirects</span>
    </label>
    <label className="toggle-row">
      <input type="checkbox" disabled=${disabled} checked=${form.allow_subdomains} onChange=${e=>upd({allow_subdomains:e.target.checked})}/>
      <span>Allow subdomains of the crawled host</span>
    </label>
    <div className="divider"/>
    <div className="form-section-title">Methods</div>
    <div className="two-col">
      <div className="field"><label>Passive</label>
        <input type="text" disabled=${disabled} value=${form.methods_passive} onChange=${e=>upd({methods_passive:e.target.value})}/></div>
      <div className="field"><label>Safe active</label>
        <input type="text" disabled=${disabled} value=${form.methods_safe_active} onChange=${e=>upd({methods_safe_active:e.target.value})}/></div>
      <div className="field"><label>Aggressive</label>
        <input type="text" disabled=${disabled} value=${form.methods_aggressive} onChange=${e=>upd({methods_aggressive:e.target.value})}/></div>
      <div className="field"><label>Destructive</label>
        <input type="text" disabled=${disabled} value=${form.methods_destructive} onChange=${e=>upd({methods_destructive:e.target.value})}/></div>
    </div>`;
}

function ScannerPolicySettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const upd = p => { setSaved(false); setForm(f=>({...f,...p})); };

  useEffect(() => {
    (async () => {
      try { setForm(policyToForm(await api.getScannerPolicy())); }
      catch(e) { setError(e.message); }
    })();
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true); setSaved(false);
    try {
      const savedPolicy = await api.upsertScannerPolicy(policyPayload(form));
      setForm(policyToForm(savedPolicy));
      setSaved(true);
    } catch(e) { setError(e.message); } finally { setSaving(false); }
  };

  return html`
    ${!form&&!error&&html`<div className="subtle">Loading…</div>`}
    ${error&&html`<div className="alert error">${error}</div>`}
    ${form&&html`
      <form className="card" onSubmit=${onSubmit}>
        <${ScannerPolicyFields} form=${form} upd=${upd}/>
        <div className="divider"/>
        <div className="row spread">
          <div>${saved&&html`<span className="save-confirm"><${IconCheck}/> Saved</span>`}</div>
          <button type="submit" className="btn" disabled=${saving}>${saving?"Saving…":"Save policy"}</button>
        </div>
      </form>`}`;
}

function UpstreamProxySettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const upd = p => { setSaved(false); setForm(f=>({...f,...p})); };

  useEffect(() => {
    (async () => {
      try { setForm(await api.getUpstreamProxy()); }
      catch(e) { setError(e.message); }
    })();
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true); setSaved(false);
    try {
      const saved = await api.upsertUpstreamProxy({
        proxy_url: form.proxy_scanner || form.proxy_llm ? (form.proxy_url||"").trim()||null : null,
        proxy_scanner: !!form.proxy_scanner,
        proxy_llm: !!form.proxy_llm,
      });
      setForm(saved);
      setSaved(true);
    } catch(e) { setError(e.message); } finally { setSaving(false); }
  };

  const anyProxy = form && (form.proxy_scanner || form.proxy_llm);

  return html`
    ${!form&&!error&&html`<div className="subtle">Loading…</div>`}
    ${error&&html`<div className="alert error">${error}</div>`}
    ${form&&html`
      <form className="card" onSubmit=${onSubmit}>
        <div className="form-section-title">Upstream Proxy</div>
        <label className="toggle-row">
          <input type="checkbox" checked=${!!form.proxy_scanner} onChange=${e=>upd({proxy_scanner:e.target.checked})}/>
          <span>Send target requests through an upstream proxy</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${!!form.proxy_llm} onChange=${e=>upd({proxy_llm:e.target.checked})}/>
          <span>Send LLM requests through the upstream proxy</span>
        </label>
        ${anyProxy&&html`
          <div className="field">
            <label>Proxy URL</label>
            <input type="url" required value=${form.proxy_url||""} placeholder="http://127.0.0.1:8080" onChange=${e=>upd({proxy_url:e.target.value})}/>
          </div>
        `}
        <div className="divider"/>
        <div className="row spread">
          <div>${saved&&html`<span className="save-confirm"><${IconCheck}/> Saved</span>`}</div>
          <button type="submit" className="btn" disabled=${saving}>${saving?"Saving…":"Save"}</button>
        </div>
      </form>`}`;
}

const DEFAULT_SPECIALIST_AGENT_FORM = {
  enabled: true,
  max_concurrent: 5,
  max_steps: 30,
  min_priority: 7,
  dispatch_idor: true,
  dispatch_auth_bypass: true,
  dispatch_sqli: true,
  dispatch_xss: true,
  dispatch_business_logic: true,
  dispatch_ssrf: true,
  dispatch_path_traversal: true,
  dispatch_cors: false,
  dispatch_crypto: true,
  dispatch_config: false,
  trigger_specialist_on_burp: false,
};

function specialistAgentToForm(cfg) {
  return cfg ? {
    enabled:           cfg.enabled           ?? true,
    max_concurrent:    cfg.max_concurrent     ?? 5,
    max_steps:         cfg.max_steps          ?? 30,
    min_priority:      cfg.min_priority       ?? 7,
    dispatch_idor:     cfg.dispatch_idor      ?? true,
    dispatch_auth_bypass: cfg.dispatch_auth_bypass ?? true,
    dispatch_sqli:     cfg.dispatch_sqli      ?? true,
    dispatch_xss:      cfg.dispatch_xss       ?? true,
    dispatch_business_logic: cfg.dispatch_business_logic ?? true,
    dispatch_ssrf:     cfg.dispatch_ssrf      ?? true,
    dispatch_path_traversal: cfg.dispatch_path_traversal ?? true,
    dispatch_cors:     cfg.dispatch_cors      ?? false,
    dispatch_crypto:   cfg.dispatch_crypto    ?? true,
    dispatch_config:   cfg.dispatch_config    ?? false,
    trigger_specialist_on_burp: cfg.trigger_specialist_on_burp ?? false,
  } : { ...DEFAULT_SPECIALIST_AGENT_FORM };
}

function specialistAgentPayload(form) {
  return {
    enabled:             !!form.enabled,
    max_concurrent:      Number(form.max_concurrent),
    max_steps:           Number(form.max_steps),
    min_priority:        Number(form.min_priority),
    dispatch_idor:       !!form.dispatch_idor,
    dispatch_auth_bypass:!!form.dispatch_auth_bypass,
    dispatch_sqli:       !!form.dispatch_sqli,
    dispatch_xss:        !!form.dispatch_xss,
    dispatch_business_logic: !!form.dispatch_business_logic,
    dispatch_ssrf:       !!form.dispatch_ssrf,
    dispatch_path_traversal: !!form.dispatch_path_traversal,
    dispatch_cors:       !!form.dispatch_cors,
    dispatch_crypto:     !!form.dispatch_crypto,
    dispatch_config:     !!form.dispatch_config,
    trigger_specialist_on_burp: !!form.trigger_specialist_on_burp,
  };
}

function SpecialistAgentSettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const upd = p => { setSaved(false); setForm(f=>({...f,...p})); };

  useEffect(() => {
    (async () => {
      try { setForm(specialistAgentToForm(await api.getSpecialistAgentConfig())); }
      catch(e) { setError(e.message); }
    })();
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true); setSaved(false);
    try {
      const savedConfig = await api.upsertSpecialistAgentConfig(specialistAgentPayload(form));
      setForm(specialistAgentToForm(savedConfig));
      setSaved(true);
    } catch(e) { setError(e.message); } finally { setSaving(false); }
  };

  const dis = form && !form.enabled;

  return html`
    ${!form&&!error&&html`<div className="subtle">Loading…</div>`}
    ${error&&html`<div className="alert error">${error}</div>`}
    ${form&&html`
      <form className="card" onSubmit=${onSubmit}>
        <div className="form-section-title">Specialist Agent Dispatch</div>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.enabled} onChange=${e=>upd({enabled:e.target.checked})}/>
          <span>Enable specialist agent dispatch</span>
        </label>
        <div className="field-hint" style=${{marginBottom:"12px"}}>
          When enabled, the Test Lead can dispatch focused specialist agents to investigate
          specific vulnerability leads in parallel. Each specialist receives an independent
          LLM session and a subset of tools (HTTP, browser, context, write_finding).
        </div>

        <div className="form-section-title">Concurrency &amp; Budget</div>
        <div className="field">
          <label>Max concurrent specialists</label>
          <input type="number" min="0" max="20" value=${form.max_concurrent} disabled=${dis}
            onChange=${e=>upd({max_concurrent:Number(e.target.value)})}/>
          <div className="field-hint">Maximum number of specialist agents running at the same time (0 = effectively disabled). Default: 5.</div>
        </div>
        <div className="field">
          <label>Max steps per specialist</label>
          <input type="number" min="1" max="200" value=${form.max_steps} disabled=${dis}
            onChange=${e=>upd({max_steps:Number(e.target.value)})}/>
          <div className="field-hint">Step budget for each specialist agent before it is stopped. Default: 30.</div>
        </div>
        <div className="field">
          <label>Minimum priority to dispatch</label>
          <input type="number" min="1" max="10" value=${form.min_priority} disabled=${dis}
            onChange=${e=>upd({min_priority:Number(e.target.value)})}/>
          <div className="field-hint">Only dispatch a specialist if the lead's priority score meets this threshold (1–10). Default: 7.</div>
        </div>

        <div className="divider"/>
        <div className="form-section-title">Attack Classes to Dispatch</div>
        <div className="field-hint" style=${{marginBottom:"8px"}}>
          Only dispatch specialists for the selected vulnerability classes. Disable classes
          you don't need to keep token usage under control.
        </div>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.dispatch_idor} disabled=${dis} onChange=${e=>upd({dispatch_idor:e.target.checked})}/>
          <span>IDOR / Broken Object Level Authorization (A01)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.dispatch_auth_bypass} disabled=${dis} onChange=${e=>upd({dispatch_auth_bypass:e.target.checked})}/>
          <span>Authentication Bypass / Broken Auth (A07)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.dispatch_sqli} disabled=${dis} onChange=${e=>upd({dispatch_sqli:e.target.checked})}/>
          <span>SQL Injection (A03)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.dispatch_xss} disabled=${dis} onChange=${e=>upd({dispatch_xss:e.target.checked})}/>
          <span>Cross-Site Scripting / XSS (A03)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.dispatch_business_logic} disabled=${dis} onChange=${e=>upd({dispatch_business_logic:e.target.checked})}/>
          <span>Business Logic (A04)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.dispatch_ssrf} disabled=${dis} onChange=${e=>upd({dispatch_ssrf:e.target.checked})}/>
          <span>Server-Side Request Forgery / SSRF (A10)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.dispatch_path_traversal} disabled=${dis} onChange=${e=>upd({dispatch_path_traversal:e.target.checked})}/>
          <span>Path Traversal / LFI (A01/A05)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.dispatch_crypto} disabled=${dis} onChange=${e=>upd({dispatch_crypto:e.target.checked})}/>
          <span>Cryptographic Failures (A02)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.dispatch_cors} disabled=${dis} onChange=${e=>upd({dispatch_cors:e.target.checked})}/>
          <span>CORS Misconfiguration (A05)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.dispatch_config} disabled=${dis} onChange=${e=>upd({dispatch_config:e.target.checked})}/>
          <span>Security Misconfiguration (A05)</span>
        </label>

        <div className="divider"/>
        <div className="row spread">
          <div>${saved&&html`<span className="save-confirm"><${IconCheck}/> Saved</span>`}</div>
          <button type="submit" className="btn" disabled=${saving}>${saving?"Saving…":"Save Specialist Settings"}</button>
        </div>
      </form>`}`;
}

const DEFAULT_BURP_REST_API_FORM = {
  api_key:"",
  scan_configuration_name:"Audit checks - all except time-based detection methods",
  scan_sqli:true,
  scan_xss:true,
  scan_command_injection:true,
  scan_path_traversal:true,
  scan_ssrf:true,
  scan_xxe:true,
  scan_ssti:true,
};

function burpRestApiToForm(cfg) {
  return cfg ? {
    enabled:cfg.enabled ?? false,
    api_url:cfg.api_url || DEFAULT_BURP_REST_API_FORM.api_url,
    api_key:cfg.api_key || "",
    scan_configuration_name:cfg.scan_configuration_name || "",
    scan_sqli:cfg.scan_sqli ?? true,
    scan_xss:cfg.scan_xss ?? true,
    scan_command_injection:cfg.scan_command_injection ?? true,
    scan_path_traversal:cfg.scan_path_traversal ?? true,
    scan_ssrf:cfg.scan_ssrf ?? true,
    scan_xxe:cfg.scan_xxe ?? true,
    scan_ssti:cfg.scan_ssti ?? true,
  } : {...DEFAULT_BURP_REST_API_FORM};
}

function burpRestApiPayload(form) {
  return {
    enabled:!!form.enabled,
    api_url:form.api_url.trim(),
    api_key:form.api_key.trim() || null,
    scan_configuration_name:form.scan_configuration_name.trim() || null,
    scan_sqli:!!form.scan_sqli,
    scan_xss:!!form.scan_xss,
    scan_command_injection:!!form.scan_command_injection,
    scan_path_traversal:!!form.scan_path_traversal,
    scan_ssrf:!!form.scan_ssrf,
    scan_xxe:!!form.scan_xxe,
    scan_ssti:!!form.scan_ssti,
  };
}

function BurpRestApiSettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [connTest, setConnTest] = useState(null);
  const [connTesting, setConnTesting] = useState(false);
  const upd = p => { setSaved(false); setForm(f=>({...f,...p})); };

  useEffect(() => {
    (async () => {
      try { setForm(burpRestApiToForm(await api.getBurpRestApiConfig())); }
      catch(e) { setError(e.message); }
    })();
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true); setSaved(false);
    try {
      const savedConfig = await api.upsertBurpRestApiConfig(burpRestApiPayload(form));
      setForm(burpRestApiToForm(savedConfig));
      setSaved(true);
    } catch(e) { setError(e.message); } finally { setSaving(false); }
  };

  const onTestConnection = async () => {
    setConnTest(null); setConnTesting(true);
    try {
      const result = await api.testBurpConnection();
      setConnTest(result);
    } catch(e) { setConnTest({ok:false, message:e.message}); } finally { setConnTesting(false); }
  };

  return html`
    ${!form&&!error&&html`<div className="subtle">Loading…</div>`}
    ${error&&html`<div className="alert error">${error}</div>`}
    ${form&&html`
      <form className="card" onSubmit=${onSubmit}>
        <div className="form-section-title">Burp Suite Active Scan</div>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.enabled} onChange=${e=>upd({enabled:e.target.checked})}/>
          <span>Enable Burp Suite active scan integration</span>
        </label>
        <div className="field-hint" style=${{marginBottom:"12px"}}>
          When enabled, the scanner automatically triggers Burp Suite active scans for
          enabled vulnerability classes as the LLM discovers candidate endpoints.
          Requires Burp Suite Professional with the REST API enabled (Burp menu → Settings → Suite → REST API).
        </div>
        <div className="field">
          <label>REST API URL</label>
          <input type="url" required value=${form.api_url} placeholder="http://127.0.0.1:1337"
            onChange=${e=>upd({api_url:e.target.value})}/>
          <div className="field-hint">Default: http://127.0.0.1:1337. Configure under Burp → Settings → Suite → REST API.</div>
        </div>
        <div className="field">
          <label>API key <span className="subtle">(optional)</span></label>
          <input type="password" value=${form.api_key} placeholder="Leave blank if not configured"
            onChange=${e=>upd({api_key:e.target.value})}/>
          <div className="field-hint">Set an API key in Burp REST API settings and paste it here for authentication.</div>
        </div>
        <div className="field">
          <label>Scan configuration <span className="subtle">(optional)</span></label>
          <input type="text" value=${form.scan_configuration_name} placeholder="Audit checks - all except time-based detection methods"
            onChange=${e=>upd({scan_configuration_name:e.target.value})}/>
          <div className="field-hint">Only enter a named configuration that exists in your Burp project. Blank avoids Unknown configuration errors.</div>
        </div>
        <div className="divider"/>
        <div className="form-section-title">Vulnerability Classes to Active Scan</div>
        <div className="field-hint" style=${{marginBottom:"8px"}}>When the LLM investigates a selected vulnerability class on a URL, Burp will actively scan that endpoint.</div>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.scan_sqli} onChange=${e=>upd({scan_sqli:e.target.checked})}/>
          <span>SQL Injection (A03)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.scan_xss} onChange=${e=>upd({scan_xss:e.target.checked})}/>
          <span>Cross-Site Scripting / XSS (A03)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.scan_command_injection} onChange=${e=>upd({scan_command_injection:e.target.checked})}/>
          <span>OS Command Injection (A03)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.scan_path_traversal} onChange=${e=>upd({scan_path_traversal:e.target.checked})}/>
          <span>Path Traversal / File Inclusion (A01/A05)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.scan_ssrf} onChange=${e=>upd({scan_ssrf:e.target.checked})}/>
          <span>Server-Side Request Forgery / SSRF (A10)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.scan_xxe} onChange=${e=>upd({scan_xxe:e.target.checked})}/>
          <span>XML External Entity / XXE (A05)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.scan_ssti} onChange=${e=>upd({scan_ssti:e.target.checked})}/>
          <span>Server-Side Template Injection / SSTI (A03)</span>
        </label>
        <div className="divider"/>
        ${connTest&&html`<div className=${"alert "+(connTest.ok?"success":"error")} style=${{marginBottom:"12px"}}>${connTest.message}</div>`}
        <div className="row spread">
          <div className="row" style=${{gap:"8px"}}>
            ${saved&&html`<span className="save-confirm"><${IconCheck}/> Saved</span>`}
            <button type="button" className="btn secondary" disabled=${connTesting} onClick=${onTestConnection}>
              ${connTesting?"Testing…":"Test Connection"}
            </button>
          </div>
          <button type="submit" className="btn" disabled=${saving}>${saving?"Saving…":"Save Burp Settings"}</button>
        </div>
      </form>`}`;
}

const API_FORMAT_LABELS = {
  anthropic:"Anthropic API",
  openai:"OpenAI API",
  openai_compatible:"OpenAI-compatible API",
  openrouter:"OpenRouter",
  google:"Google Gemini API",
  bedrock:"Amazon Bedrock Converse",
  azure_openai:"Azure OpenAI",
  azure_foundry:"Azure AI Foundry (OpenAI API)",
  azure_foundry_openai:"Azure AI Foundry (OpenAI API)",
  azure_foundry_anthropic:"Azure AI Foundry (Anthropic API)",
};
const DEFAULT_PROVIDER_FORM = { name:"", api_format:"anthropic", base_url:"", models:"", api_key:"", max_tpm:"", max_rpm:"" };
const DEFAULT_LLM_FORM = { name:"Default", provider_id:"", model:"", max_tokens:4096, temperature:0, use_vision:false, force_tool_choice:true };
const PROVIDER_BASE_URL_PLACEHOLDERS = {
  anthropic:"https://api.anthropic.com",
  openai:"https://api.openai.com/v1",
  openai_compatible:"http://localhost:1234/v1",
  openrouter:"https://openrouter.ai/api/v1",
  google:"https://generativelanguage.googleapis.com",
  bedrock:"https://bedrock-runtime.us-east-1.amazonaws.com",
  azure_openai:"https://myresource.openai.azure.com",
  azure_foundry:"https://myresource.services.ai.azure.com",
  azure_foundry_openai:"https://myresource.services.ai.azure.com/openai/v1",
  azure_foundry_anthropic:"https://myresource.services.ai.azure.com/anthropic/v1",
};
// Actual runtime defaults used by the backend when base_url is blank
const PROVIDER_DEFAULT_BASE_URLS = {
  anthropic:  "https://api.anthropic.com",
  openai:     "https://api.openai.com/v1",
  openai_compatible: null,           // no sensible default — must be set
  openrouter: "https://openrouter.ai/api/v1",
  google:     "https://generativelanguage.googleapis.com",
  bedrock:    "AWS SDK default (us-east-1)",
  azure_openai: null,                // must be set
  azure_foundry: null,
  azure_foundry_openai: null,
  azure_foundry_anthropic: null,
};
const PROVIDER_MODEL_PLACEHOLDERS = {
  anthropic:"claude-opus-4-5\nclaude-sonnet-4-5",
  openai:"gpt-4.1\ngpt-4o\nllama-3.1-8b-instruct",
  openai_compatible:"llama-3.1-8b-instruct\nqwen2.5-coder",
  openrouter:"openrouter/owl-alpha\nnvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
  google:"gemini-2.5-pro-preview-05-06\ngemini-2.5-flash-preview-04-17",
  bedrock:"global.anthropic.claude-sonnet-4-6\nglobal.anthropic.claude-opus-4-7",
  azure_openai:"gpt-4o\ngpt-4.1",
  azure_foundry:"gpt-4o\nMeta-Llama-3.3-70B-Instruct",
  azure_foundry_openai:"gpt-4o\nMeta-Llama-3.3-70B-Instruct",
  azure_foundry_anthropic:"claude-sonnet-4-5\nclaude-opus-4-1",
};

function providerToForm(provider) {
  return provider ? {
    name:provider.name || "",
    api_format:provider.api_format || "anthropic",
    base_url:provider.base_url || "",
    models:(provider.models || []).join("\n"),
    api_key:provider.api_key || "",
    max_tpm:provider.max_tpm != null ? provider.max_tpm : "",
    max_rpm:provider.max_rpm != null ? provider.max_rpm : "",
  } : {...DEFAULT_PROVIDER_FORM};
}

function providerPayload(form) {
  return {
    name:form.name.trim(),
    api_format:form.api_format,
    base_url:form.base_url.trim() || null,
    models:form.models.split(/\r?\n|,/).map(m=>m.trim()).filter(Boolean),
    api_key:form.api_key.trim() || null,
    max_tpm:form.max_tpm !== "" ? Number(form.max_tpm) : null,
    max_rpm:form.max_rpm !== "" ? Number(form.max_rpm) : null,
  };
}


function llmProfileToForm(cfg, providers=[]) {
  const providerId = cfg?.provider_id || providers[0]?.id || "";
  const provider = providers.find(p=>p.id===providerId) || providers[0];
  return cfg ? {
    name:cfg.name??"Default",
    provider_id:providerId,
    model:cfg.model,
    max_tokens:cfg.max_tokens,
    temperature:cfg.temperature,
    use_vision:cfg.use_vision??false,
    force_tool_choice:cfg.force_tool_choice??true,
  } : {
    ...DEFAULT_LLM_FORM,
    provider_id:provider?.id || "",
    model:provider?.models?.[0] || "",
  };
}

function llmPayload(form) {
  return {
    name:form.name.trim(),
    provider_id:Number(form.provider_id),
    model:form.model.trim(),
    max_tokens:Number(form.max_tokens),
    temperature:Number(form.temperature),
    use_vision:form.use_vision,
    force_tool_choice:form.force_tool_choice,
  };
}

function LLMProviderForm({ mode, provider, onSaved, onCancel }) {
  const [form, setForm] = useState(() => providerToForm(provider));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const upd = p => { setSaved(false); setForm(f=>({...f,...p})); };
  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true); setSaved(false);
    try {
      const payload = providerPayload(form);
      const savedProvider = mode === "edit"
        ? await api.updateLLMProvider(provider.id, payload)
        : await api.createLLMProvider(payload);
      setSaved(true);
      onSaved?.(savedProvider);
    } catch(e) { setError(e.message); } finally { setSaving(false); }
  };
  return html`
    ${error&&html`<div className="alert error">${error}</div>`}
    <form className="card" onSubmit=${onSubmit}>
      <div className="form-section-title">Provider</div>
      <div className="field"><label>Name</label>
        <input type="text" required maxLength="120" value=${form.name} onChange=${e=>upd({name:e.target.value})}/></div>
      <div className="field">
        <label>API format</label>
        <select className="select" value=${form.api_format} onChange=${e=>upd({api_format:e.target.value})}>
          <option value="anthropic">Anthropic API</option>
          <option value="openai">OpenAI API</option>
          <option value="openai_compatible">OpenAI-compatible API</option>
          <option value="openrouter">OpenRouter</option>
          <option value="google">Google Gemini API</option>
          <option value="bedrock">Amazon Bedrock Converse</option>
          <option value="azure_openai">Azure OpenAI</option>
          <option value="azure_foundry_openai">Azure AI Foundry (OpenAI API)</option>
          <option value="azure_foundry_anthropic">Azure AI Foundry (Anthropic API)</option>
        </select>
      </div>
      <div className="field"><label>Base URL <span className="field-optional">(optional)</span></label>
        <input type="url" value=${form.base_url} placeholder=${PROVIDER_BASE_URL_PLACEHOLDERS[form.api_format] || ""}
          onChange=${e=>upd({base_url:e.target.value})}/>
        ${form.api_format==="bedrock"&&html`<div className="field-hint">Leave blank to use the default boto3 Bedrock endpoint for AWS_REGION / AWS_DEFAULT_REGION.</div>`}
      </div>
      <div className="field"><label>Model names</label>
        <textarea required rows="5" value=${form.models} placeholder=${PROVIDER_MODEL_PLACEHOLDERS[form.api_format] || ""}
          onChange=${e=>upd({models:e.target.value})}></textarea>
        <div className="field-hint">Enter one model per line, or separate models with commas.</div>
      </div>
      <div className="field"><label>API Key <span className="field-optional">(optional)</span></label>
        <input type="password" value=${form.api_key} placeholder=${form.api_format==="bedrock"?"Leave blank to use boto3 / AWS_PROFILE / IAM role":"Leave blank if not required"}
          onChange=${e=>upd({api_key:e.target.value})}/>
        ${form.api_format==="bedrock"&&html`<div className="field-hint">When blank, Aespa uses boto3 credentials from AWS_PROFILE, environment variables, SSO, or the instance/task role.</div>`}
      </div>
      <div className="divider"/>
      <div className="form-section-title">Rate Limits <span className="field-optional">(optional)</span></div>
      <div className="field-hint" style=${{marginBottom:"8px"}}>Set token and request limits to automatically pace requests and prevent API rate-limiting errors (429).</div>
      <div className="two-col" style=${{gap:"16px", marginBottom:"8px"}}>
        <div className="field">
          <label>Max Tokens Per Minute (TPM)</label>
          <input type="number" min="1" placeholder="Unlimited" value=${form.max_tpm} onChange=${e=>upd({max_tpm:e.target.value})}/>
        </div>
        <div className="field">
          <label>Max Requests Per Minute (RPM)</label>
          <input type="number" min="1" placeholder="Unlimited" value=${form.max_rpm} onChange=${e=>upd({max_rpm:e.target.value})}/>
        </div>
      </div>
      <div className="divider"/>
      <div className="row spread">
        <div>${saved&&html`<span className="save-confirm"><${IconCheck}/> Saved</span>`}</div>
        <div className="row">
          ${onCancel&&html`<button type="button" className="btn ghost" onClick=${onCancel}>Cancel</button>`}
          <button type="submit" className="btn" disabled=${saving}>${saving?"Saving…":mode==="edit"?"Save provider":"Create provider"}</button>
        </div>
      </div>
    </form>`;
}

function LLMProfileForm({ mode, profile, providers, onSaved, onCancel }) {
  const [form, setForm] = useState(() => llmProfileToForm(profile, providers));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const upd = p => { setSaved(false); setForm(f=>({...f,...p})); };
  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true); setSaved(false);
    try {
      const payload = llmPayload(form);
      const savedProfile = mode === "edit"
        ? await api.updateLLMProfile(profile.id, payload)
        : await api.createLLMProfile(payload);
      setSaved(true);
      onSaved?.(savedProfile);
    } catch(e) { setError(e.message); } finally { setSaving(false); }
  };

  const selectedProvider = providers.find(p=>p.id===Number(form.provider_id));
  const models = selectedProvider?.models || [];

  return html`
    ${error&&html`<div className="alert error">${error}</div>`}
    <form className="card" onSubmit=${onSubmit}>
      <div className="form-section-title">Profile</div>
      <div className="field"><label>Name</label>
        <input type="text" required maxLength="120" value=${form.name} onChange=${e=>upd({name:e.target.value})}/></div>
      <div className="field">
        <label>Provider</label>
        <select className="select" required value=${form.provider_id} onChange=${e=>{
          const provider = providers.find(p=>p.id===Number(e.target.value));
          upd({provider_id:e.target.value, model:provider?.models?.[0] || ""});
        }}>
          ${providers.map(p=>html`<option key=${p.id} value=${p.id}>${p.name} (${API_FORMAT_LABELS[p.api_format]||p.api_format})</option>`)}
        </select>
      </div>
      <div className="field"><label>Model</label>
        <select className="select" required value=${form.model} onChange=${e=>upd({model:e.target.value})}>
          ${models.map(m=>html`<option key=${m} value=${m}>${m}</option>`)}
        </select>
      </div>
      <div className="divider"/>
      <div className="form-section-title">Sampling</div>
      <div className="two-col">
        <div className="field"><label>Max tokens</label>
          <input type="number" required min="1" max="64000" value=${form.max_tokens} onChange=${e=>upd({max_tokens:e.target.value})}/></div>
        <div className="field"><label>Temperature <span className="field-hint-inline">(0-2)</span></label>
          <input type="number" required min="0" max="2" step="0.05" value=${form.temperature} onChange=${e=>upd({temperature:e.target.value})}/></div>
      </div>
      <div className="divider"/>
      <div className="form-section-title">Vision</div>
      <label className="toggle-row">
        <input type="checkbox" checked=${form.use_vision} onChange=${e=>upd({use_vision:e.target.checked})}/>
        <span>Include page screenshots in LLM prompts (requires vision-capable model)</span>
      </label>
      <div className="divider"/>
      <div className="form-section-title">Advanced</div>
      <label className="toggle-row">
        <input type="checkbox" checked=${form.force_tool_choice} onChange=${e=>upd({force_tool_choice:e.target.checked})}/>
        <span>Force tool execution</span>
      </label>
      <div className="field-hint" style=${{marginBottom:"12px"}}>
        Enforces tool execution constraints on the LLM via standard OpenAI wire parameters. 
        Recommended for standard models to maintain high scanning density. 
        Disable if using custom reasoning/thinking models that reject forced tool choice (e.g. DeepSeek-R1, deepseek-reasoner).
      </div>
      <div className="divider"/>
      <div className="row spread">
        <div>${saved&&html`<span className="save-confirm"><${IconCheck}/> Saved</span>`}</div>
        <div className="row">
          ${onCancel&&html`<button type="button" className="btn ghost" onClick=${onCancel}>Cancel</button>`}
          <button type="submit" className="btn" disabled=${saving}>${saving?"Saving…":mode==="edit"?"Save profile":"Create profile"}</button>
        </div>
      </div>
    </form>`;
}

function SettingsPage() {
  const [profiles, setProfiles] = useState(null);
  const [providers, setProviders] = useState(null);
  const [tab, setTab] = useState("profiles");
  const [screen, setScreen] = useState("list");
  const [editing, setEditing] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
  const importRef = useRef(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [items,providerItems] = await Promise.all([api.listLLMProfiles(), api.listLLMProviders()]);
      setProfiles(items);
      setProviders(providerItems);
      if (tab === "profiles" && items.length === 0 && providerItems.length > 0) { setScreen("new"); setEditing(null); }
      else if (tab === "providers" && providerItems.length === 0) { setScreen("new"); setEditing(null); }
      else if (screen === "new" && ((tab === "profiles" && profiles?.length === 0) || (tab === "providers" && providers?.length === 0))) { setScreen("list"); }
    } catch(e) { setError(e.message); }
  }, [screen, tab, profiles?.length, providers?.length]);

  useEffect(() => { load(); }, []);

  const onSaved = async () => { await load(); setScreen("list"); setEditing(null); };
  const onEdit = profile => { setEditing(profile); setScreen("edit"); setError(null); };
  const onNew = () => { setEditing(null); setScreen("new"); setError(null); };
  const onCancel = () => { setScreen("list"); setEditing(null); setError(null); };
  const onActivate = async (profile) => {
    setBusyId(profile.id); setError(null);
    try { await api.activateLLMProfile(profile.id); await load(); }
    catch(e) { setError(e.message); } finally { setBusyId(null); }
  };
  const onDelete = async (profile) => {
    if (!confirm(`Delete LLM settings profile "${profile.name}"?`)) return;
    setBusyId(profile.id); setError(null);
    try { await api.deleteLLMProfile(profile.id); await load(); }
    catch(e) { setError(e.message); } finally { setBusyId(null); }
  };
  const onDeleteProvider = async (provider) => {
    if (!confirm(`Delete LLM provider "${provider.name}"?`)) return;
    setBusyId(provider.id); setError(null);
    try { await api.deleteLLMProvider(provider.id); await load(); }
    catch(e) { setError(e.message); } finally { setBusyId(null); }
  };
  const switchTab = next => { setTab(next); setScreen("list"); setEditing(null); setError(null); };

  const onExport = async () => {
    setError(null);
    try {
      const data = await api.exportLLMConfig();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `aespa-llm-config-${new Date().toISOString().slice(0,10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch(e) { setError(e.message); }
  };

  const onImportClick = () => { if (importRef.current) importRef.current.click(); };

  const onImportFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setError(null); setImporting(true);
    try {
      const text = await file.text();
      let parsed;
      try { parsed = JSON.parse(text); } catch { throw new Error("Invalid JSON file"); }
      const result = await api.importLLMConfig(parsed);
      await load();
      alert(`Import complete: ${result.providers_created} provider(s) created, ${result.providers_updated} updated; ${result.profiles_created} profile(s) created, ${result.profiles_updated} updated.`);
    } catch(e) { setError(e.message); } finally { setImporting(false); }
  };

  const title = tab === "providers"
    ? (screen === "new" ? "New LLM Provider" : screen === "edit" ? "Edit LLM Provider" : "LLM Providers")
    : (screen === "new" ? "New LLM Profile" : screen === "edit" ? "Edit LLM Profile" : "LLM Profiles");
  const canCreateProfile = (providers || []).length > 0;

  return html`
    <div className="topbar">
      <div className="topbar-title">${title}</div>
      <div className="topbar-actions">
        <button className="btn secondary sm" disabled=${importing} onClick=${onExport}>Export</button>
        <button className="btn secondary sm" disabled=${importing} onClick=${onImportClick}>${importing?"Importing…":"Import"}</button>
        <input ref=${importRef} type="file" accept=".json,application/json" style=${{display:"none"}} onChange=${onImportFile} />
        ${screen==="list"&&html`<button className="btn" disabled=${tab==="profiles"&&!canCreateProfile} onClick=${onNew}>${tab==="providers"?"New provider":"New profile"}</button>`}
      </div>
    </div>
    <div className="content scroll-content settings-content">
      <div className="tab-bar settings-tab-bar">
        <button className=${"tab-btn "+(tab==="profiles"?"active":"")} onClick=${()=>switchTab("profiles")}>Profiles</button>
        <button className=${"tab-btn "+(tab==="providers"?"active":"")} onClick=${()=>switchTab("providers")}>Providers</button>
      </div>
      ${(!profiles||!providers)&&!error&&html`<div className="subtle">Loading…</div>`}
      ${error&&html`<div className="alert error">${error}</div>`}
      ${profiles&&providers&&tab==="profiles"&&screen==="list"&&html`
        ${providers.length===0&&html`<div className="alert">Create a provider before adding LLM profiles.</div>`}
        <div className="settings-list settings-list-profiles">
          <div className="settings-list-head">
            <div>Name</div><div>Provider</div><div>Model</div><div>Vision</div><div>Status</div><div></div>
          </div>
          ${profiles.map(p=>html`
            <div className="settings-list-row" key=${p.id}>
              <div><strong>${p.name}</strong></div>
              <div>${p.provider_name || `Provider #${p.provider_id}`}</div>
              <div className="mono">${p.model}</div>
              <div>${p.use_vision?"On":"Off"}</div>
              <div>${p.is_active?html`<span className="badge ok">Active</span>`:html`<span className="subtle">Inactive</span>`}</div>
              <div className="row settings-list-actions">
                ${!p.is_active&&html`<button className="btn sm secondary" disabled=${busyId===p.id} onClick=${()=>onActivate(p)}>Use</button>`}
                <button className="btn sm" disabled=${busyId===p.id} onClick=${()=>onEdit(p)}>Edit</button>
                <button className="btn danger-outline sm" disabled=${busyId===p.id} onClick=${()=>onDelete(p)}>Delete</button>
              </div>
            </div>`)}
        </div>`}
      ${providers&&tab==="providers"&&screen==="list"&&html`
        <div className="settings-list settings-list-providers">
          <div className="settings-list-head">
            <div>Name</div><div>API</div><div>Base URL</div><div>Models</div><div>Limits</div><div></div>
          </div>
          ${providers.map(p=>html`
            <div className="settings-list-row" key=${p.id}>
              <div><strong>${p.name}</strong></div>
              <div>${API_FORMAT_LABELS[p.api_format]||p.api_format}</div>
              <div className="mono">${p.base_url || PROVIDER_DEFAULT_BASE_URLS[p.api_format] || "(must be set)"}</div>
              <div className="mono">${(p.models||[]).join(", ")}</div>
              <div>
                ${p.max_tpm || p.max_rpm ? html`
                  ${p.max_tpm ? html`<div>${Number(p.max_tpm).toLocaleString()} TPM</div>` : ""}
                  ${p.max_rpm ? html`<div style=${{fontSize:11,color:"var(--muted)",marginTop:1}}>${Number(p.max_rpm).toLocaleString()} RPM</div>` : ""}
                ` : html`<span className="subtle">Unlimited</span>`}
              </div>
              <div className="row settings-list-actions">
                <button className="btn sm" disabled=${busyId===p.id} onClick=${()=>onEdit(p)}>Edit</button>
                <button className="btn danger-outline sm" disabled=${busyId===p.id} onClick=${()=>onDeleteProvider(p)}>Delete</button>
              </div>
            </div>`)}
        </div>`}
      ${profiles&&providers&&tab==="profiles"&&screen==="new"&&html`<${LLMProfileForm} mode="new" providers=${providers} onSaved=${onSaved} onCancel=${profiles.length?onCancel:null}/>`}
      ${profiles&&providers&&tab==="profiles"&&screen==="edit"&&editing&&html`<${LLMProfileForm} mode="edit" profile=${editing} providers=${providers} onSaved=${onSaved} onCancel=${onCancel}/>`}
      ${providers&&tab==="providers"&&screen==="new"&&html`<${LLMProviderForm} mode="new" onSaved=${onSaved} onCancel=${providers.length?onCancel:null}/>`}
      ${providers&&tab==="providers"&&screen==="edit"&&editing&&html`<${LLMProviderForm} mode="edit" provider=${editing} onSaved=${onSaved} onCancel=${onCancel}/>`}
    </div>`;
}

const DEFAULT_VALIDATOR_FORM = {
  enabled: true,
  max_steps: 20,
  min_severity: "low",
  auto_validate_inline: true,
  require_concrete_disproof: true,
};

function validatorToForm(cfg) {
  return {
    enabled: cfg.enabled ?? true,
    max_steps: cfg.max_steps ?? 20,
    min_severity: cfg.min_severity ?? "low",
    auto_validate_inline: cfg.auto_validate_inline ?? true,
    require_concrete_disproof: cfg.require_concrete_disproof ?? true,
  };
}

function validatorPayload(form) {
  return {
    enabled: form.enabled,
    max_steps: Number(form.max_steps),
    min_severity: form.min_severity,
    auto_validate_inline: form.auto_validate_inline,
    require_concrete_disproof: form.require_concrete_disproof,
  };
}

function ValidatorSettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const upd = p => { setSaved(false); setForm(f=>({...f,...p})); };

  useEffect(() => {
    (async () => {
      try { setForm(validatorToForm(await api.getAdversarialValidatorConfig())); }
      catch(e) { setError(e.message); }
    })();
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true); setSaved(false);
    try {
      const savedConfig = await api.upsertAdversarialValidatorConfig(validatorPayload(form));
      setForm(validatorToForm(savedConfig));
      setSaved(true);
    } catch(e) { setError(e.message); } finally { setSaving(false); }
  };

  const dis = form && !form.enabled;

  return html`
    ${!form&&!error&&html`<div className="subtle">Loading…</div>`}
    ${error&&html`<div className="alert error">${error}</div>`}
    ${form&&html`
      <form className="card" onSubmit=${onSubmit}>
        <div className="form-section-title">Adversarial Validator</div>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.enabled} onChange=${e=>upd({enabled:e.target.checked})}/>
          <span>Enable adversarial validator</span>
        </label>
        <div className="field-hint" style=${{marginBottom:"12px"}}>
          When enabled, each finding is reviewed by an adversarial LLM agent whose explicit
          mandate is to <em>disprove</em> the finding before confirming it. This reduces false
          positives without relying on the scanner's own judgment. When disabled, the legacy
          static-probe validator is used instead.
        </div>

        <div className="form-section-title">Step Budget</div>
        <div className="field">
          <label>Max steps per finding</label>
          <input type="number" min="1" max="50" value=${form.max_steps} disabled=${dis}
            onChange=${e=>upd({max_steps:Number(e.target.value)})}/>
          <div className="field-hint">
            Maximum number of tool calls the validator may make per finding (1–50). Default: 20.
            Higher values give the validator more opportunities to disprove a finding but increase
            cost and latency.
          </div>
        </div>

        <div className="form-section-title">Severity Filter</div>
        <div className="field">
          <label>Minimum severity to validate</label>
          <select value=${form.min_severity} disabled=${dis}
            onChange=${e=>upd({min_severity:e.target.value})}>
            <option value="critical">Critical only</option>
            <option value="high">High and above</option>
            <option value="medium">Medium and above</option>
            <option value="low">Low and above (default)</option>
            <option value="info">All (including Info)</option>
          </select>
          <div className="field-hint">
            Findings below this severity are skipped by the validator and left as "unconfirmed".
          </div>
        </div>

        <div className="form-section-title">Behaviour</div>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.auto_validate_inline} disabled=${dis}
            onChange=${e=>upd({auto_validate_inline:e.target.checked})}/>
          <span>Auto-validate findings inline during scan</span>
        </label>
        <div className="field-hint" style=${{marginBottom:"12px"}}>
          When enabled, each finding is validated immediately after it is written, while the
          scan is still running. When disabled, validation only runs when triggered manually.
        </div>
        <label className="toggle-row">
          <input type="checkbox" checked=${form.require_concrete_disproof} disabled=${dis}
            onChange=${e=>upd({require_concrete_disproof:e.target.checked})}/>
          <span>Require concrete disproof (strict mode)</span>
        </label>
        <div className="field-hint" style=${{marginBottom:"12px"}}>
          When enabled (recommended), the validator must find a specific innocent explanation
          to mark a finding as a false positive — failure to reproduce is not sufficient.
          When disabled, inability to reproduce is treated as a false positive (lenient mode).
        </div>

        <div className="form-row">
          <button type="submit" className="btn" disabled=${saving}>${saving?"Saving…":"Save"}</button>
          ${saved&&html`<span className="saved-indicator">Saved</span>`}
        </div>
      </form>`}`;
}

function ScopeHostsPanel({ siteId, hosts, onChange }) {
  const [input, setInput] = useState("");
  const [saving, setSaving] = useState(false);

  const remove = async (host) => {
    const next = hosts.filter(h => h !== host);
    setSaving(true);
    try { await api.updateScopeHosts(siteId, next); onChange(next); }
    catch(e) { alert(e.message); }
    finally { setSaving(false); }
  };

  const add = async () => {
    const host = input.trim().toLowerCase().replace(/^https?:\/\//, "").split("/")[0];
    if (!host || hosts.includes(host)) { setInput(""); return; }
    const next = [...hosts, host];
    setSaving(true);
    try { await api.updateScopeHosts(siteId, next); onChange(next); setInput(""); }
    catch(e) { alert(e.message); }
    finally { setSaving(false); }
  };

  const onKey = (e) => { if (e.key === "Enter") { e.preventDefault(); add(); } };

  return html`
    <div className="scope-hosts-panel">
      <div className="scope-hosts-title">Attack Scope</div>
      <div className="scope-hosts-list">
        ${hosts.length === 0 && html`<span className="scope-hosts-empty">No restriction — all hosts allowed</span>`}
        ${hosts.map(h => html`
          <span key=${h} className="scope-host-chip">
            ${h}
            <button className="scope-host-remove" title="Remove" disabled=${saving}
              onClick=${()=>remove(h)}>×</button>
          </span>`)}
      </div>
      <div className="scope-hosts-add">
        <input className="scope-hosts-input" placeholder="Add hostname…" value=${input}
          onInput=${e=>setInput(e.target.value)} onKeyDown=${onKey} disabled=${saving}/>
        <button className="btn sm" onClick=${add} disabled=${saving||!input.trim()}>Add</button>
      </div>
    </div>`;
}

function ScanPolicyPage() {
  const [tab, setTab] = useState("scanner");
  return html`
    <div className="topbar"><div className="topbar-title">Agent Settings</div></div>
    <div className="content" style=${{paddingLeft:16,paddingRight:0,paddingBottom:0,display:"flex",flexDirection:"column",flex:1,minHeight:0}}>
      <div className="tab-bar">
        <button className=${"tab-btn"+(tab==="scanner"?" active":"")} onClick=${()=>setTab("scanner")}>Scanner</button>
        <button className=${"tab-btn"+(tab==="specialists"?" active":"")} onClick=${()=>setTab("specialists")}>Specialist Agents</button>
        <button className=${"tab-btn"+(tab==="validator"?" active":"")} onClick=${()=>setTab("validator")}>Validator</button>
      </div>
      <div className="scroll-content" style=${{flex:1,minHeight:0,overflowY:"auto",overflowX:"hidden",paddingTop:16,paddingBottom:28}}>
        ${tab==="scanner"     && html`<${ScannerPolicySettings}/>`}
        ${tab==="specialists" && html`<${SpecialistAgentSettings}/>`}
        ${tab==="validator"   && html`<${ValidatorSettings}/>`}
      </div>
    </div>`;
}

function ExternalIntegrationsPage() {
  const [tab, setTab] = useState("burp");
  return html`
    <div className="topbar">
      <div className="topbar-title">External Integrations</div>
    </div>
    <div className="content" style=${{paddingLeft:16,paddingRight:0,paddingBottom:0,display:"flex",flexDirection:"column",flex:1,minHeight:0}}>
      <div className="tab-bar">
        <button className=${"tab-btn"+(tab==="burp"?" active":"")} onClick=${()=>setTab("burp")}>Burp Suite Integration</button>
        <button className=${"tab-btn"+(tab==="proxy"?" active":"")} onClick=${()=>setTab("proxy")}>Upstream Proxy</button>
      </div>
      <div className="scroll-content" style=${{flex:1,minHeight:0,overflowY:"auto",overflowX:"hidden",paddingTop:16,paddingBottom:28}}>
        ${tab==="burp"  && html`<${BurpRestApiSettings}/>`}
        ${tab==="proxy" && html`<${UpstreamProxySettings}/>`}
      </div>
    </div>`;
}

function DebugPage({ showUsername, setShowUsername, username, reportingDebugCfg, setReportingDebugCfg }) {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  const [hdrCfg, setHdrCfg] = useState(null);
  const [hdrForm, setHdrForm] = useState({ header_name: "", header_value: "" });
  const [hdrSaving, setHdrSaving] = useState(false);
  const [hdrSaved, setHdrSaved] = useState(false);
  const [hdrError, setHdrError] = useState(null);
  const [repSaving, setRepSaving] = useState(false);
  const [repSaved, setRepSaved] = useState(false);
  const [repError, setRepError] = useState(null);

  useEffect(() => {
    (async () => {
      try { setCfg(await api.getSpecialistAgentConfig()); }
      catch(e) { setError(e.message); }
    })();
    (async () => {
      try {
        const h = await api.getGlobalHttpHeader();
        setHdrCfg(h);
        setHdrForm({ header_name: h.header_name || "", header_value: h.header_value || "" });
      } catch(e) { setHdrError(e.message); }
    })();
    (async () => {
      try { setReportingDebugCfg(await api.getReportingDebugConfig()); }
      catch(e) { setRepError(e.message); }
    })();
  }, []);

  const toggle = async (checked) => {
    setSaved(false); setSaving(true); setError(null);
    try {
      const updated = await api.upsertSpecialistAgentConfig({ ...cfg, trigger_specialist_on_burp: checked });
      setCfg(updated);
      setSaved(true);
    } catch(e) { setError(e.message); } finally { setSaving(false); }
  };

  const saveHeader = async (e) => {
    e.preventDefault();
    setHdrSaved(false); setHdrSaving(true); setHdrError(null);
    try {
      const updated = await api.upsertGlobalHttpHeader({
        header_name: hdrForm.header_name.trim() || null,
        header_value: hdrForm.header_value.trim() || null,
      });
      setHdrCfg(updated);
      setHdrForm({ header_name: updated.header_name || "", header_value: updated.header_value || "" });
      setHdrSaved(true);
    } catch(e) { setHdrError(e.message); } finally { setHdrSaving(false); }
  };

  const toggleReportingDebug = async (patch) => {
    const base = reportingDebugCfg || { capture_enabled:false, panel_enabled:false };
    setRepSaving(true); setRepSaved(false); setRepError(null);
    try {
      const updated = await api.upsertReportingDebugConfig({ ...base, ...patch });
      setReportingDebugCfg(updated);
      setRepSaved(true);
    } catch(e) { setRepError(e.message); } finally { setRepSaving(false); }
  };

  return html`
    <div className="topbar">
      <div className="topbar-title">Debug</div>
    </div>
    <div className="content scroll-content">
      ${!cfg && !hdrCfg && !error && !hdrError && html`<div className="subtle">Loading…</div>`}

      <div className="card">
        <div className="form-section-title">Global Extra HTTP Header</div>
        <div className="field-hint" style=${{marginBottom:12}}>
          Inject an additional HTTP header into every request made by the scanner and crawler
          (Playwright and HTTPX). Does not affect requests sent to LLMs. Leave the header name
          empty to disable.
        </div>
        ${hdrError && html`<div className="alert error">${hdrError}</div>`}
        ${hdrCfg !== null && html`
          <form onSubmit=${saveHeader}>
            <div className="form-row">
              <label className="form-label">Header Name</label>
              <input className="form-input" type="text"
                placeholder="e.g. X-Debug-Token"
                value=${hdrForm.header_name}
                disabled=${hdrSaving}
                onInput=${e => { setHdrSaved(false); setHdrForm(f => ({...f, header_name: e.target.value})); }}/>
            </div>
            <div className="form-row">
              <label className="form-label">Header Value</label>
              <input className="form-input" type="text"
                placeholder="e.g. my-secret-value"
                value=${hdrForm.header_value}
                disabled=${hdrSaving}
                onInput=${e => { setHdrSaved(false); setHdrForm(f => ({...f, header_value: e.target.value})); }}/>
            </div>
            <div style=${{display:"flex",alignItems:"center",gap:12,marginTop:8}}>
              <button className="btn btn-primary" type="submit" disabled=${hdrSaving}>
                ${hdrSaving ? "Saving…" : "Save"}
              </button>
              ${hdrSaved && html`<span className="save-confirm"><${IconCheck}/> Saved</span>`}
            </div>
          </form>`}
      </div>

      ${error && html`<div className="alert error">${error}</div>`}
      ${cfg && html`
        <div className="card">
          <div className="form-section-title">Specialist Agent</div>
          <label className="toggle-row">
            <input type="checkbox" checked=${cfg.trigger_specialist_on_burp ?? false}
              disabled=${saving}
              onChange=${e=>toggle(e.target.checked)}/>
            <span>Trigger a Specialist Agent whenever a Burp active scan is triggered</span>
          </label>
          <div className="field-hint">
            When enabled, a specialist agent is dispatched immediately alongside every Burp active scan,
            independently investigating the same URL. Use this to force specialist agents to fire for
            debugging purposes.
          </div>
          ${saved && html`<div className="save-confirm" style=${{marginTop:8}}><${IconCheck}/> Saved</div>`}
        </div>`}

      <div className="card" style=${{marginTop:16}}>
        <div className="form-section-title">Reporting Lab</div>
        <div className="field-hint" style=${{marginBottom:12}}>
          Capture reporting LLM messages from real scans and expose the replay lab in the sidebar.
          Captures include final reporting batches and during-scan writeups, and are stored
          in a separate SQLite database next to the main AESPA database.
        </div>
        ${repError && html`<div className="alert error">${repError}</div>`}
        <label className="toggle-row">
          <input type="checkbox" checked=${reportingDebugCfg?.capture_enabled ?? false}
            disabled=${repSaving}
            onChange=${e=>toggleReportingDebug({ capture_enabled:e.target.checked })}/>
          <span>Capture reporting LLM messages during scans</span>
        </label>
        <label className="toggle-row" style=${{marginTop:8}}>
          <input type="checkbox" checked=${reportingDebugCfg?.panel_enabled ?? false}
            disabled=${repSaving}
            onChange=${e=>toggleReportingDebug({ panel_enabled:e.target.checked })}/>
          <span>Show Reporting Lab in the sidebar</span>
        </label>
        ${repSaved && html`<div className="save-confirm" style=${{marginTop:8}}><${IconCheck}/> Saved</div>`}
      </div>

      <div className="card" style=${{marginTop: 16}}>
        <div className="form-section-title">Cloudflare Access</div>
        <div className="field-hint" style=${{marginBottom: 12}}>
          Show the authenticated user's email/username above the application version on the bottom left of the sidebar.
        </div>
        <label className="toggle-row">
          <input type="checkbox" checked=${showUsername}
            onChange=${e => {
              const checked = e.target.checked;
              setShowUsername(checked);
              try { localStorage.setItem("aespa_show_username", String(checked)); } catch(_) {}
            }}/>
          <span>Show Username in Sidebar</span>
        </label>
        ${showUsername && html`
          <div className="field-hint" style=${{marginTop: 8}}>
            Current verified username: <strong className="mono">${username || "None (will only be displayed in sidebar if verified)"}</strong>
          </div>
        `}
      </div>
    </div>`;
}

function ReportingDebugPage() {
  const [tab, setTab] = useState("prompt");
  const [promptKey, setPromptKey] = useState("reporting.analyse");
  const [promptVersions, setPromptVersions] = useState([]);
  const [selectedPromptVersionId, setSelectedPromptVersionId] = useState("");
  const [promptVersionName, setPromptVersionName] = useState("");
  const [promptText, setPromptText] = useState("");
  const [promptSaving, setPromptSaving] = useState(false);
  const [promptSaved, setPromptSaved] = useState(false);
  const [captures, setCaptures] = useState([]);
  const [captureDbPath, setCaptureDbPath] = useState("");
  const [selectedCaptureId, setSelectedCaptureId] = useState("");
  const [selectedCaptureDetail, setSelectedCaptureDetail] = useState(null);

  const [selectedReplayVersionId, setSelectedReplayVersionId] = useState("");
  const [replay, setReplay] = useState(null);
  const [replayBusy, setReplayBusy] = useState(false);
  const [replays, setReplays] = useState([]);
  const [selectedReplayId, setSelectedReplayId] = useState("");
  const [compareReplayId, setCompareReplayId] = useState("");
  const [compareReplay, setCompareReplay] = useState(null);
  const [error, setError] = useState(null);

  const selectedCapture = captures.find(c => String(c.id) === String(selectedCaptureId));
  const replayPromptKey = selectedCapture?.kind === "writeup" ? "reporting.writeup" : "reporting.analyse";
  const selectedPromptVersion = promptVersions.find(v => String(v.id) === String(selectedPromptVersionId));
  const promptKeyVersions = promptVersions.filter(v => v.key === promptKey);
  const replayPromptVersions = promptVersions.filter(v => v.key === replayPromptKey);
  const selectedReplayVersion = replayPromptVersions.find(v => String(v.id) === String(selectedReplayVersionId));
  const currentFindings = replay?.findings || [];
  const compareFindings = compareReplay?.findings || [];

  const setEditorVersion = (version) => {
    if (!version) return;
    setSelectedPromptVersionId(String(version.id));
    setPromptVersionName(version.name || "");
    setPromptText(version.prompt_text || "");
  };
  const loadPromptVersions = useCallback(async (key, selectedId = "") => {
    const d = await api.listReportingPromptVersions(key);
    const versions = d.versions || [];
    setPromptVersions(prev => [...prev.filter(v => v.key !== key), ...versions]);
    const current = versions.find(v => String(v.id) === String(selectedId)) || versions[0];
    if (key === promptKey) setEditorVersion(current);
    return versions;
  }, [promptKey]);
  const loadCaptures = useCallback(async () => {
    const d = await api.listReportingCaptures();
    setCaptures(d.captures || []);
    setCaptureDbPath(d.db_path || "");
    if (!selectedCaptureId && d.captures?.[0]) setSelectedCaptureId(String(d.captures[0].id));
  }, [selectedCaptureId]);
  const loadReplays = useCallback(async () => {
    const d = await api.listReportingReplays();
    setReplays(d.replays || []);
    if (!selectedReplayId && d.replays?.[0]) setSelectedReplayId(String(d.replays[0].id));
  }, [selectedReplayId]);

  useEffect(() => {
    loadPromptVersions("reporting.analyse").catch(e=>setError(e.message));
    loadPromptVersions("reporting.writeup").catch(e=>setError(e.message));
    loadCaptures().catch(e=>setError(e.message));
    loadReplays().catch(e=>setError(e.message));
  }, []);
  useEffect(() => {
    setSelectedPromptVersionId("");
    loadPromptVersions(promptKey).catch(e=>setError(e.message));
  }, [promptKey]);
  useEffect(() => {
    if (replayPromptVersions.length === 0) {
      loadPromptVersions(replayPromptKey).catch(e=>setError(e.message));
      return;
    }
    if (!selectedReplayVersionId || !replayPromptVersions.some(v => String(v.id) === String(selectedReplayVersionId))) {
      const builtin = replayPromptVersions.find(v => v.is_builtin) || replayPromptVersions[0];
      setSelectedReplayVersionId(String(builtin.id));
    }
  }, [replayPromptKey, selectedReplayVersionId, replayPromptVersions.length]);

  useEffect(() => {
    if (!replay || !["queued","running"].includes(replay.status)) return;
    const iv = setInterval(async () => {
      try {
        const next = await api.getReportingReplay(replay.id);
        setReplay(next);
        if (!["queued","running"].includes(next.status)) {
          setReplayBusy(false);
          setSelectedReplayId(String(next.id));
          loadReplays().catch(()=>{});
        }
      } catch(e) {
        setError(e.message);
        setReplayBusy(false);
      }
    }, 1500);
    return () => clearInterval(iv);
  }, [replay?.id, replay?.status]);
  useEffect(() => {
    if (!selectedReplayId) return;
    api.getReportingReplay(selectedReplayId).then(setReplay).catch(()=>{});
  }, [selectedReplayId]);
  useEffect(() => {
    if (!compareReplayId) { setCompareReplay(null); return; }
    api.getReportingReplay(compareReplayId).then(setCompareReplay).catch(()=>{});
  }, [compareReplayId]);
  useEffect(() => {
    if (!selectedCaptureId) { setSelectedCaptureDetail(null); return; }
    api.getReportingCapture(selectedCaptureId).then(setSelectedCaptureDetail).catch(()=>{});
  }, [selectedCaptureId]);

  const savePrompt = async () => {
    if (!selectedPromptVersion || selectedPromptVersion.is_builtin) return;
    setPromptSaving(true); setPromptSaved(false); setError(null);
    try {
      const p = await api.updateReportingPromptVersion(selectedPromptVersion.id, {
        name: promptVersionName,
        prompt_text: promptText,
      });
      await loadPromptVersions(promptKey, p.id);
      setPromptSaved(true);
    } catch(e) { setError(e.message); } finally { setPromptSaving(false); }
  };
  const createPromptVersion = async () => {
    const name = promptVersionName.trim() || `Version ${new Date().toLocaleString()}`;
    setPromptSaving(true); setPromptSaved(false); setError(null);
    try {
      const p = await api.createReportingPromptVersion({ key: promptKey, name, prompt_text: promptText });
      await loadPromptVersions(promptKey, p.id);
      setPromptSaved(true);
    } catch(e) { setError(e.message); } finally { setPromptSaving(false); }
  };
  const deletePromptVersion = async () => {
    if (!selectedPromptVersion || selectedPromptVersion.is_builtin) return;
    if (!confirm(`Delete prompt version "${selectedPromptVersion.name}"? Saved replay findings remain available.`)) return;
    setPromptSaving(true); setPromptSaved(false); setError(null);
    try {
      await api.deleteReportingPromptVersion(selectedPromptVersion.id);
      await loadPromptVersions(promptKey);
    } catch(e) { setError(e.message); } finally { setPromptSaving(false); }
  };
  const startReplay = async () => {
    if (!selectedCaptureId || !selectedReplayVersion?.id) return;
    setReplayBusy(true); setError(null); setReplay(null);
    try {
      const r = await api.replayReportingCapture(selectedCaptureId, { prompt_version_id: Number(selectedReplayVersion.id) });
      setReplay(r);
      setSelectedReplayId(String(r.id));
      setTab("replay");
    } catch(e) { setError(e.message); setReplayBusy(false); }
  };

  return html`
    <div className="topbar">
      <div className="topbar-title">Reporting Lab</div>
    </div>
    <div className="content scroll-content settings-content">
      <div className="tab-bar settings-tab-bar">
        <button className=${"tab-btn"+(tab==="prompt"?" active":"")} onClick=${()=>setTab("prompt")}>Prompt</button>
        <button className=${"tab-btn"+(tab==="replay"?" active":"")} onClick=${()=>{ setTab("replay"); loadCaptures().catch(()=>{}); }}>Replay</button>
        <button className=${"tab-btn"+(tab==="findings"?" active":"")} onClick=${()=>{ setTab("findings"); loadReplays().catch(()=>{}); }}>Debug Findings</button>
      </div>
      ${error && html`<div className="alert error">${error}</div>`}

      ${tab==="prompt" && html`
        <div className="card">
          <div className="form-section-title">Reporting Prompt Versions</div>
          <div className="field-hint" style=${{marginBottom:12}}>
            Default versions load from reporting.py. New versions are saved in the Reporting Lab database and can be replayed against the same captures.
            <br />Reporting Lab uses the DEFAULT LLM setting and does not respect the overriden setting in the scan the data came from.
            <br />Set the Version name BEFORE clicking new version!
            <br />Batch reporting has {url} and {results} placeholders. 
            <br />During-scan writeups have {source}, {base_url}, {finding_json}, {evidence_json}.
          </div>
          <div className="form-row">
            <label className="form-label">Prompt</label>
            <select className="form-input" value=${promptKey}
              onChange=${e=>{ setPromptKey(e.target.value); setPromptSaved(false); }}>
              <option value="reporting.analyse">Final reporting batch</option>
              <option value="reporting.writeup">During-scan writeup replay</option>
            </select>
          </div>
          <div className="form-row">
            <label className="form-label">Version</label>
            <select className="form-input" value=${selectedPromptVersionId}
              onChange=${e=>{
                const v = promptVersions.find(p=>String(p.id)===String(e.target.value));
                setEditorVersion(v);
                setPromptSaved(false);
              }}>
              ${promptKeyVersions.map(v=>html`
                <option key=${v.id} value=${String(v.id)}>
                  ${v.name}${v.is_builtin ? " (from reporting.py)" : ""}
                </option>`)}
            </select>
          </div>
          <div className="form-row">
            <label className="form-label">Version name</label>
            <input className="form-input" value=${promptVersionName}
              disabled=${promptSaving}
              onInput=${e=>{ setPromptSaved(false); setPromptVersionName(e.target.value); }} />
          </div>
          ${selectedPromptVersion && html`
            <div className="row" style=${{gap:8,marginBottom:8}}>
              <span className="source-badge">${selectedPromptVersion.is_builtin ? "from reporting.py" : "DB version"}</span>
              ${selectedPromptVersion.updated_at && html`<span className="subtle">Updated ${fmtDate(selectedPromptVersion.updated_at)}</span>`}
            </div>`}
          <textarea className="form-input mono" style=${{minHeight:520,whiteSpace:"pre",fontSize:12}}
            value=${promptText}
            disabled=${promptSaving}
            onInput=${e=>{ setPromptSaved(false); setPromptText(e.target.value); }} />
          <div className="row" style=${{gap:8,marginTop:12}}>
            <button className="btn" onClick=${savePrompt} disabled=${promptSaving || !promptText.trim() || selectedPromptVersion?.is_builtin}>
              ${promptSaving ? "Saving…" : "Save Prompt"}
            </button>
            <button className="btn secondary" onClick=${createPromptVersion} disabled=${promptSaving || !promptText.trim()}>
              New Version
            </button>
            <button className="btn danger-outline" onClick=${deletePromptVersion} disabled=${promptSaving || selectedPromptVersion?.is_builtin}>
              Delete Version
            </button>
            ${promptSaved && html`<span className="save-confirm"><${IconCheck}/> Saved</span>`}
          </div>
        </div>`}

      ${tab==="replay" && html`
        <div className="card">
          <div className="form-section-title">Replay Captured Reporting Batch</div>
          <div className="field-hint" style=${{marginBottom:12}}>
            Captures are read from <span className="mono">${captureDbPath || "reporting debug DB"}</span>.
          </div>
          <div className="row" style=${{gap:8,alignItems:"center",marginBottom:12}}>
            <select className="form-input" style=${{maxWidth:520}} value=${selectedCaptureId}
              onChange=${e=>{ setSelectedCaptureId(e.target.value); setSelectedReplayVersionId(""); }}>
              <option value="">Select a capture…</option>
              ${captures.map(c=>html`
                <option key=${c.id} value=${String(c.id)}>
                  #${c.id} · ${c.kind === "writeup" ? "during-scan writeup" : "final reporting"} · ${fmtDate(c.created_at)} · ${truncUrl(c.url, 52)} · ${c.finding_count} findings
                </option>`)}
            </select>
            <select className="form-input" style=${{maxWidth:300}} value=${selectedReplayVersionId}
              onChange=${e=>setSelectedReplayVersionId(e.target.value)}>
              <option value="">Select prompt version…</option>
              ${replayPromptVersions.map(v=>html`
                <option key=${v.id} value=${String(v.id)}>
                  ${v.name}${v.is_builtin ? " (default)" : ""}
                </option>`)}
            </select>
            <button className="btn secondary" onClick=${()=>loadCaptures().catch(e=>setError(e.message))}>Refresh</button>
            <button className="btn" onClick=${startReplay} disabled=${replayBusy || !selectedCaptureId || !selectedReplayVersion?.id}>
              ${replayBusy ? "Replaying…" : "Replay"}
            </button>
          </div>
          ${selectedCapture && html`
            <div className="settings-list-row" style=${{marginBottom:8}}>
              <div>
                <strong>Capture #${selectedCapture.id}</strong>
                <div className="mono" style=${{fontSize:11,wordBreak:"break-all"}}>${selectedCapture.url}</div>
                <div className="subtle">
                  ${selectedCapture.kind === "writeup" ? `Source ${selectedCapture.source || "unknown"}` : `Model ${selectedCapture.llm?.model || "unknown"} · ${selectedCapture.llm?.provider || "unknown"}`}
                </div>
                <div className="subtle">Prompt version ${selectedReplayVersion?.name || "unknown"}</div>
              </div>
              <div><span className="finding-count-badge">${selectedCapture.finding_count}</span></div>
            </div>
            ${selectedCaptureDetail?.findings?.length > 0 && html`
              <div style=${{marginBottom:12}}>
                <div className="subtle" style=${{fontSize:11,fontWeight:600,marginBottom:6,textTransform:"uppercase",letterSpacing:"0.05em"}}>Original findings in this capture</div>
                <${DebugFindingsTable}
                  findings=${selectedCaptureDetail.findings}/>
              </div>`}
          `}
          ${replay && html`
            <div className="activity-token-bar" style=${{cursor:"default"}}>
              ${["queued","running"].includes(replay.status) && html`<span className="inline-spinner"></span>`}
              <span className="token-bar-label">${replay.status}</span>
              <span>${replay.progress_message || ""}</span>
              ${replay.prompt_version_name && html`<span className="source-badge">${replay.prompt_version_name}</span>`}
              ${replay.error && html`<span className="alert error" style=${{marginLeft:8}}>${replay.error}</span>`}
            </div>
            ${replay.status==="complete" && html`
              <div className="row" style=${{gap:8,marginTop:12}}>
                <button className="btn" onClick=${()=>setTab("findings")}>
                  View ${replay.finding_count} Debug Finding${replay.finding_count===1?"":"s"}
                </button>
              </div>`}
          `}
        </div>`}

      ${tab==="findings" && html`
        <div className="card">
          <div className="form-section-title">Debug Reporter Findings</div>
          <div className="row" style=${{gap:8,alignItems:"center",marginBottom:12}}>
            <select className="form-input" style=${{maxWidth:460}} value=${selectedReplayId}
              onChange=${e=>setSelectedReplayId(e.target.value)}>
              <option value="">Select a replay…</option>
              ${replays.map(r=>html`
                <option key=${r.id} value=${String(r.id)}>
                  Replay #${r.id} · ${r.prompt_version_name || "unknown version"} · ${r.status} · ${fmtDate(r.started_at)} · ${r.finding_count} findings
                </option>`)}
            </select>
            <select className="form-input" style=${{maxWidth:460}} value=${compareReplayId}
              onChange=${e=>setCompareReplayId(e.target.value)}>
              <option value="">Compare with…</option>
              ${replays.filter(r=>String(r.id)!==String(selectedReplayId)).map(r=>html`
                <option key=${r.id} value=${String(r.id)}>
                  Replay #${r.id} · ${r.prompt_version_name || "unknown version"} · ${r.status} · ${fmtDate(r.started_at)}
                </option>`)}
            </select>
            <button className="btn secondary" onClick=${()=>loadReplays().catch(e=>setError(e.message))}>Refresh</button>
          </div>
          ${compareReplay
            ? html`
              <div style=${{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(360px,1fr))",gap:16}}>
                <div>
                  <div className="form-section-title">Replay #${replay?.id || "—"} · ${replay?.prompt_version_name || "unknown version"}</div>
                  ${currentFindings.length === 0
                    ? html`<div className="subtle" style=${{padding:24,textAlign:"center"}}>No debug findings for this replay.</div>`
                    : html`<${DebugFindingsTable} findings=${currentFindings}/>`}
                </div>
                <div>
                  <div className="form-section-title">Replay #${compareReplay.id} · ${compareReplay.prompt_version_name || "unknown version"}</div>
                  ${compareFindings.length === 0
                    ? html`<div className="subtle" style=${{padding:24,textAlign:"center"}}>No debug findings for this replay.</div>`
                    : html`<${DebugFindingsTable} findings=${compareFindings}/>`}
                </div>
              </div>`
            : currentFindings.length === 0
              ? html`<div className="subtle" style=${{padding:24,textAlign:"center"}}>No debug findings for this replay.</div>`
              : html`<${DebugFindingsTable} findings=${currentFindings}/>`}
        </div>`}
    </div>`;
}

function DebugFindingsTable({ findings }) {
  const [expandedFinding, setExpandedFinding] = useState(null);
  const SEV_ORDER = {critical:0,high:1,medium:2,low:3,info:4};
  const sorted = [...findings].sort((a,b)=>(SEV_ORDER[a.severity]??99)-(SEV_ORDER[b.severity]??99));
  return html`
    <div className="findings-table-wrap">
      <table className="findings-table" style=${{tableLayout:"fixed",width:"100%"}}>
        <colgroup><col style=${{width:80}}/><col/></colgroup>
        <thead>
          <tr><th>Sev</th><th>Title</th></tr>
        </thead>
        <tbody>
          ${sorted.map((f,idx)=>html`
            <tr key=${idx} className="finding-group-row"
              onClick=${()=>setExpandedFinding(expandedFinding===idx?null:idx)}>
              <td><span className=${"sev-badge sev-"+(f.severity||"info")}>${f.severity||"info"}</span></td>
              <td className="finding-title" style=${{width:"100%"}}>
                <div className="row" style=${{alignItems:"flex-start",gap:8}}>
                  <div style=${{flex:1,minWidth:0}}>
                    <span className="group-chevron">${expandedFinding===idx?"▾":"▸"}</span>
                    ${f.title || "Untitled finding"}
                    <div className="mono" style=${{fontSize:11,wordBreak:"break-all",marginTop:4}}>${f.affected_url || ""}</div>
                  </div>
                  ${f.cvss_score != null && html`<span className="subtle" style=${{whiteSpace:"nowrap",fontSize:11,paddingTop:2}}>${f.cvss_score}</span>`}
                </div>
              </td>
            </tr>
            ${expandedFinding===idx && html`
              <tr className="finding-evidence-row">
                <td colSpan="2">
                  <div className="finding-description">
                    <div><strong>Description</strong></div><div>${f.description || "—"}</div>
                    <div style=${{marginTop:8}}><strong>Impact</strong></div><div>${f.impact || "—"}</div>
                    <div style=${{marginTop:8}}><strong>Likelihood</strong></div><div>${f.likelihood || "—"}</div>
                    <div style=${{marginTop:8}}><strong>Recommendation</strong></div><div>${f.recommendation || "—"}</div>
                    <div style=${{marginTop:8}}><strong>CVSS 3.1</strong></div>
                    <div>${f.cvss_score ?? "—"} ${f.cvss_vector && html`<span className="mono" style=${{marginLeft:8,fontSize:11}}>${f.cvss_vector}</span>`}</div>
                  </div>
                  ${f.evidence && html`<pre className="finding-evidence">${f.evidence}</pre>`}
                </td>
              </tr>`}
          `)}
        </tbody>
      </table>
    </div>`;
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function parseDate(val) {
  if (!val) return new Date(val);
  if (val instanceof Date) return val;
  let s = String(val).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(s) && !/[Zz]|[+-]\d{2}:?\d{2}$/.test(s)) {
    s = s.replace(" ", "T");
    if (!s.endsWith("Z")) {
      s += "Z";
    }
  }
  return new Date(s);
}

function fmtDate(iso) {
  return iso ? parseDate(iso).toLocaleString(undefined, {dateStyle:"short",timeStyle:"short"}) : "—";
}

function truncUrl(url, maxLen=40) {
  try {
    const u = new URL(url);
    const s = u.hostname + u.pathname + u.hash;
    return s.length > maxLen ? s.slice(0, maxLen-1) + "…" : s;
  } catch { return url.slice(0, maxLen); }
}

function sourceLabel(source) {
  const labels = {
    alice: "A.L.I.C.E",
    dynamic_scan: "Dynamic",
    burp_active_scan: "Burp",
    burp_mcp: "Burp MCP",
    deterministic_probe: "Deterministic",
    manual_import: "Imported",
    debug_reporter: "Debug Reporter",
    unknown: "Unknown",
  };
  return labels[source] || String(source || "Unknown").replace(/_/g, " ");
}

function apiTranscriptText(text) {
  if (!text) return "";
  const value = String(text).trim();
  return value.includes("REQUEST\n") && value.includes("RESPONSE\n") ? value : "";
}

function markdownText(value) {
  return String(value ?? "").trim();
}

function markdownListValue(value) {
  const text = markdownText(value);
  return text || "—";
}

function markdownCodeBlock(value) {
  const text = markdownText(value);
  if (!text) return "—";
  const fence = text.includes("```") ? "````" : "```";
  return `${fence}\n${text}\n${fence}`;
}

function slugForFilename(value) {
  return String(value || "issues")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "issues";
}

function markdownExportFilename(run, siteName) {
  const base = slugForFilename(run?.name || siteName || `run-${run?.id || "issues"}`);
  const date = new Date().toISOString().slice(0, 10);
  return `${base}-issues-${date}.md`;
}

function downloadTextFile(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function findingsToMarkdown(findings, meta = {}) {
  const sevOrder = {critical:0,high:1,medium:2,low:3,info:4};
  const valOrder = {confirmed:0,validating:1,unvalidated:2,unconfirmed:3,false_positive:4,low_confidence:4};
  const sorted = [...(findings || [])].sort((a, b) => {
    const sev = (sevOrder[a.severity] ?? 99) - (sevOrder[b.severity] ?? 99);
    if (sev !== 0) return sev;
    const val = (valOrder[a.validation_status] ?? 99) - (valOrder[b.validation_status] ?? 99);
    if (val !== 0) return val;
    return String(a.title || "").localeCompare(String(b.title || ""));
  });
  const lines = [
    `# Issue Export${meta.runName ? `: ${meta.runName}` : ""}`,
    "",
  ];
  if (meta.siteName) lines.push(`- Site: ${meta.siteName}`);
  if (meta.generatedAt) lines.push(`- Exported: ${meta.generatedAt.toLocaleString()}`);
  lines.push(`- Total findings: ${sorted.length}`, "");
  lines.push(
    "<!-- aespa-findings-json",
    encodeURIComponent(JSON.stringify(sorted.map(findingImportPayload))),
    "-->",
    "",
  );

  sorted.forEach((f, idx) => {
    lines.push(
      `## ${idx + 1}. ${markdownListValue(f.title)}`,
      "",
      `- Severity: ${markdownListValue(f.severity)}`,
      `- OWASP: ${markdownListValue(f.owasp_category)}`,
      `- Source: ${markdownListValue(sourceLabel(f.finding_source))}`,
      `- Validation: ${markdownListValue(f.validation_status)}`,
      `- Affected URL: ${markdownListValue(f.affected_url)}`,
      `- CVSS: ${markdownListValue(f.cvss_score)}${f.cvss_vector ? ` (${f.cvss_vector})` : ""}`,
      "",
      "### Description",
      markdownListValue(f.description),
      "",
      "### Impact",
      markdownListValue(f.impact),
      "",
      "### Likelihood",
      markdownListValue(f.likelihood),
      "",
      "### Recommendation",
      markdownListValue(f.recommendation),
      "",
      "### Evidence",
      markdownCodeBlock(f.evidence || f.response_evidence || f.request_evidence),
      "",
    );
    if (f.request_evidence) {
      lines.push("### Request Evidence", markdownCodeBlock(f.request_evidence), "");
    }
    if (f.response_evidence) {
      lines.push("### Response Evidence", markdownCodeBlock(f.response_evidence), "");
    }
    if (f.validation_note) {
      lines.push("### Validation Note", markdownListValue(f.validation_note), "");
    }
    const mergedInstances = (() => {
      try { return JSON.parse(f.merged_instances || "[]"); } catch (_) { return []; }
    })();
    if (mergedInstances.length > 0) {
      lines.push("### Additional Instances", "");
      mergedInstances.forEach((inst, idx) => {
        lines.push(`- **Instance ${idx + 2}:** \`${inst.url || "\u2014"}\``);
        const ev = inst.request_evidence || inst.evidence;
        if (ev) lines.push("", markdownCodeBlock(ev), "");
      });
      lines.push("");
    }
  });

  return lines.join("\n");
}

function findingImportPayload(f) {
  return {
    owasp_category: f.owasp_category || "A00",
    severity: f.severity || "info",
    title: f.title || "Imported finding",
    description: f.description || "",
    impact: f.impact || "",
    likelihood: f.likelihood || "",
    recommendation: f.recommendation || "",
    cvss_score: Number(f.cvss_score) || 0,
    cvss_vector: f.cvss_vector || "",
    affected_url: f.affected_url || "",
    evidence: f.evidence || "",
    request_evidence: f.request_evidence || "",
    response_evidence: f.response_evidence || "",
    finding_source: f.finding_source || "manual_import",
    validation_status: f.validation_status || "unvalidated",
    validation_note: f.validation_note || null,
    merged_instances: f.merged_instances || "[]",
  };
}

function parseFindingsMarkdown(markdown) {
  const text = String(markdown || "");
  const embedded = text.match(/<!--\s*aespa-findings-json\s+([\s\S]*?)\s+-->/);
  if (embedded) {
    const parsed = JSON.parse(decodeURIComponent(embedded[1].trim()));
    if (Array.isArray(parsed)) return parsed.map(findingImportPayload);
  }
  return parseFindingsMarkdownSections(text);
}

function parseFindingsMarkdownSections(markdown) {
  const matches = [...markdown.matchAll(/^##\s+\d+\.\s+(.+)$/gm)];
  return matches.map((match, idx) => {
    const start = match.index + match[0].length;
    const end = idx + 1 < matches.length ? matches[idx + 1].index : markdown.length;
    const block = markdown.slice(start, end);
    const cvss = markdownBullet(block, "CVSS");
    const cvssMatch = cvss.match(/^([0-9.]+)(?:\s+\((.*)\))?$/);
    return findingImportPayload({
      title: match[1],
      severity: markdownBullet(block, "Severity"),
      owasp_category: markdownBullet(block, "OWASP"),
      finding_source: markdownBullet(block, "Source") || "manual_import",
      validation_status: markdownBullet(block, "Validation"),
      affected_url: markdownBullet(block, "Affected URL"),
      cvss_score: cvssMatch ? parseFloat(cvssMatch[1]) : 0,
      cvss_vector: cvssMatch?.[2] || "",
      description: markdownSection(block, "Description"),
      impact: markdownSection(block, "Impact"),
      likelihood: markdownSection(block, "Likelihood"),
      recommendation: markdownSection(block, "Recommendation"),
      evidence: stripMarkdownFence(markdownSection(block, "Evidence")),
      request_evidence: stripMarkdownFence(markdownSection(block, "Request Evidence")),
      response_evidence: stripMarkdownFence(markdownSection(block, "Response Evidence")),
      validation_note: markdownSection(block, "Validation Note") || null,
    });
  });
}

function markdownBullet(block, label) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = block.match(new RegExp(`^- ${escaped}: (.*)$`, "m"));
  const value = match?.[1]?.trim() || "";
  return value === "—" ? "" : value;
}

function markdownSection(block, title) {
  const escaped = title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = block.match(new RegExp(`### ${escaped}\\n([\\s\\S]*?)(?=\\n### |$)`));
  const value = match?.[1]?.trim() || "";
  return value === "—" ? "" : value;
}

function stripMarkdownFence(value) {
  const text = markdownText(value);
  const match = text.match(/^(`{3,4})\n([\s\S]*)\n\1$/);
  return match ? match[2] : text;
}

createRoot(document.getElementById("root")).render(html`<${App}/>`);
