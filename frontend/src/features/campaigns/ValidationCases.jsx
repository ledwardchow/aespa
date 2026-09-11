import { useMemo, useState } from "react";

const READINESS_LABELS = {
  pending: "Pending",
  resolved: "Runnable",
  static_complete: "Static path complete",
  ambiguous: "Ambiguous route",
  missing_frontend_hop: "Missing browser route",
  missing_backend_hop: "Missing backend route",
  missing_prerequisite: "Missing prerequisite",
  wrong_target: "Wrong target",
  crawl_failed: "Crawl failed",
  legacy_unresolved: "Legacy path needs review",
};

const EXECUTION_LABELS = {
  not_queued: "Not queued",
  queued: "Queued",
  running: "Running",
  confirmed: "Confirmed",
  dismissed: "Dismissed",
  inconclusive: "Inconclusive",
  skipped: "Skipped",
};

const HOP_LABELS = {
  ui_route: "Page",
  ui_action: "UI action",
  browser_request: "Browser request",
  http_call: "HTTP request",
  server_ingress: "Server request",
  server_egress: "Server-to-server request",
  route: "Server route",
  handler: "Handler",
  service: "Service",
  lead_anchor: "SAST lead",
  vulnerability_anchor: "SAST lead",
};

function parseMaybeJson(value, fallback) {
  if (value == null || value === "") return fallback;
  if (typeof value !== "string") return value;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function referenceValue(value) {
  if (value == null) return null;
  if (typeof value === "object") return value.reference || value.value || value.label || null;
  return String(value);
}

export function validationCasesFromResponse(value) {
  if (Array.isArray(value)) return value;
  if (value && Array.isArray(value.cases)) return value.cases;
  if (value && Array.isArray(value.validation_cases)) return value.validation_cases;
  return [];
}

export function caseSourceLead(validationCase) {
  const lead =
    validationCase?.source_lead ||
    validationCase?.source_lead_context ||
    validationCase?.lead ||
    {};
  return {
    id: lead.id ?? validationCase?.origin_lead_id,
    reference:
      referenceValue(lead.reference) ||
      referenceValue(lead.origin_reference) ||
      referenceValue(validationCase?.source_lead_reference) ||
      referenceValue(validationCase?.lead_reference) ||
      referenceValue(validationCase?.origin_lead_reference),
    title: lead.title || validationCase?.source_lead_title || validationCase?.lead_title,
    severity:
      lead.severity || validationCase?.source_lead_severity || validationCase?.lead_severity,
  };
}

function nodeFrom(value, fallbackKind) {
  if (!value || typeof value !== "object") return null;
  const detail = value.detail && typeof value.detail === "object" ? value.detail : {};
  const merged = { ...detail, ...value };
  const kind = merged.kind || merged.request_role || merged.role || fallbackKind;
  if (
    !merged.path &&
    !merged.route &&
    !merged.url &&
    !merged.location &&
    !merged.action &&
    !merged.label &&
    !merged.component_name &&
    !merged.component_id
  )
    return null;
  return { ...merged, kind };
}

export function orderedHops(staticPathValue, legacyPathValue) {
  const staticPath = parseMaybeJson(staticPathValue, {});
  const legacyPath = parseMaybeJson(legacyPathValue, {});
  if (Array.isArray(staticPath)) return staticPath.map((hop) => nodeFrom(hop)).filter(Boolean);
  if (Array.isArray(staticPath?.hops)) {
    return staticPath.hops.map((hop) => nodeFrom(hop)).filter(Boolean);
  }

  const surface = staticPath?.frontend_surface || {};
  const hops = [
    nodeFrom(surface.ui_route || surface.page_route || surface.route, "ui_route"),
    nodeFrom(surface.ui_action || surface.action, "ui_action"),
    nodeFrom(surface.browser_request || surface.request, "browser_request"),
  ];
  const serviceHops = Array.isArray(staticPath?.service_hops) ? staticPath.service_hops : [];
  hops.push(...serviceHops.map((hop) => nodeFrom(hop)).filter(Boolean));
  hops.push(nodeFrom(staticPath?.vulnerability_anchor || staticPath?.lead_anchor, "lead_anchor"));
  const result = hops.filter(Boolean);
  if (result.length > 0) return result;

  // Version 1/2 mappings are still readable. These fields are display-only
  // and are never used to claim that a legacy path is live.
  if (legacyPath?.frontend_entrypoint || legacyPath?.backend_route) {
    return [
      nodeFrom(legacyPath.frontend_entrypoint, "http_call"),
      nodeFrom(legacyPath.backend_route, "route"),
    ].filter(Boolean);
  }
  return [];
}

export function liveBindingFor(validationCase) {
  return (
    parseMaybeJson(validationCase?.live_binding || validationCase?.live_binding_json, {}) || {}
  );
}

export function blockersFor(validationCase) {
  const blockers = validationCase?.blocker_codes || validationCase?.blocker_codes_json;
  const parsed = parseMaybeJson(blockers, []);
  if (Array.isArray(parsed)) return parsed.filter(Boolean);
  if (typeof parsed === "string" && parsed) return [parsed];
  return [];
}

export function readinessLabel(status) {
  return READINESS_LABELS[status] || status || "Readiness unknown";
}

function readinessVariant(status) {
  if (status === "resolved") return "success";
  if (["pending", "static_complete", "ambiguous", "missing_prerequisite"].includes(status))
    return "warning";
  if (status) return "danger";
  return "neutral";
}

export function ReadinessBadge({ status }) {
  return <span className={`badge ${readinessVariant(status)}`}>{readinessLabel(status)}</span>;
}

export function ExecutionBadge({ status }) {
  const variant =
    status === "confirmed"
      ? "success"
      : ["running", "queued"].includes(status)
        ? "running"
        : ["dismissed", "skipped"].includes(status)
          ? "neutral"
          : status === "inconclusive"
            ? "warning"
            : "neutral";
  return (
    <span className={`badge ${variant}`}>{EXECUTION_LABELS[status] || status || "Not run"}</span>
  );
}

function hopText(hop) {
  const method = hop.method ? String(hop.method).toUpperCase() : "";
  const path = hop.path || hop.route || hop.url || hop.endpoint;
  if (path) return `${method}${method ? " " : ""}${path}`;
  return hop.action || hop.label || hop.name || hop.location || "Evidence recorded";
}

function hopRole(hop) {
  return HOP_LABELS[hop.request_role] || HOP_LABELS[hop.kind] || hop.kind || "Path step";
}

export function TypedHops({ staticPath, legacyPath, compact = false }) {
  const hops = orderedHops(staticPath, legacyPath);
  if (hops.length === 0) return <div className="subtle">No path evidence recorded.</div>;
  return (
    <ol className={`validation-hop-list${compact ? " compact" : ""}`}>
      {hops.map((hop, index) => (
        <li key={`${hop.fact_id || hop.kind || "hop"}-${index}`} className="validation-hop">
          <span className="validation-hop-index">{index + 1}</span>
          <div className="validation-hop-content">
            <div className="validation-hop-heading">
              <strong>{hopRole(hop)}</strong>
              {hop.component_name && <span className="subtle">{hop.component_name}</span>}
            </div>
            <div className="mono validation-hop-value">{hopText(hop)}</div>
            {hop.evidence_location && (
              <div className="subtle validation-hop-evidence">{hop.evidence_location}</div>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function candidateText(candidate) {
  const method = candidate.method ? `${String(candidate.method).toUpperCase()} ` : "";
  return `${method}${candidate.path || candidate.url || candidate.request_path || "request"}`;
}

export function LiveBinding({ validationCase, compact = false }) {
  const binding = liveBindingFor(validationCase);
  const observedRequest =
    binding.observed_request && typeof binding.observed_request === "object"
      ? binding.observed_request
      : {};
  const requestMethod = binding.method || observedRequest.method;
  const requestPath = binding.path || binding.url || observedRequest.path || observedRequest.url;
  const candidates = Array.isArray(binding.candidates)
    ? binding.candidates
    : Array.isArray(binding.request_candidates)
      ? binding.request_candidates
      : [];
  if (!Object.keys(binding).length) {
    return <div className="subtle">No live crawl binding recorded.</div>;
  }
  const evidenceIds = Array.isArray(binding.evidence_ids) ? binding.evidence_ids : [];
  return (
    <div className="validation-live-binding">
      <div className="validation-binding-meta">
        <strong>
          {binding.status === "resolved" ? "Matched crawl evidence" : "Crawl evidence"}
        </strong>
        {binding.page_id != null && <span>page #{binding.page_id}</span>}
        {binding.action_id != null && <span>action #{binding.action_id}</span>}
        {binding.traffic_id != null && <span>request #{binding.traffic_id}</span>}
        {binding.interaction_id && <span>interaction {binding.interaction_id}</span>}
        {binding.session_label && <span>session {binding.session_label}</span>}
      </div>
      {requestMethod && requestPath && (
        <div className="mono validation-bound-request">
          {String(requestMethod).toUpperCase()} {requestPath}
        </div>
      )}
      {candidates.length > 0 && (
        <div className="validation-candidates">
          <span className="subtle">
            {candidates.length} evidenced candidate{candidates.length === 1 ? "" : "s"}
          </span>
          {candidates.map((candidate, index) => (
            <div
              className="validation-candidate"
              key={candidate.id ?? candidate.traffic_id ?? index}
            >
              <span className="validation-candidate-marker">
                {candidate.id ?? candidate.traffic_id ?? `#${index + 1}`}
              </span>
              <span className="mono">{candidateText(candidate)}</span>
              {(candidate.page_route || candidate.interaction_id || candidate.session_label) && (
                <span className="subtle">
                  {[candidate.page_route, candidate.interaction_id, candidate.session_label]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
      {!compact && evidenceIds.length > 0 && (
        <div className="subtle">Evidence: {evidenceIds.join(", ")}</div>
      )}
    </div>
  );
}

export function ValidationCaseStatus({ validationCase, compact = false }) {
  const blockers = blockersFor(validationCase);
  return (
    <div className={`validation-case-status${compact ? " compact" : ""}`}>
      <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
        <ReadinessBadge status={validationCase.readiness_status} />
        <ExecutionBadge status={validationCase.execution_status} />
      </div>
      {blockers.length > 0 && (
        <div className="validation-blockers">
          <strong>Why it cannot run:</strong> {blockers.join(", ")}
        </div>
      )}
      {referenceValue(validationCase.copied_lead_reference) && (
        <div className="subtle">
          Copied lead: {referenceValue(validationCase.copied_lead_reference)}
        </div>
      )}
      {referenceValue(validationCase.finding_reference) && (
        <div className="subtle">Finding: {referenceValue(validationCase.finding_reference)}</div>
      )}
    </div>
  );
}

function assertionText(validationCase) {
  const assertion = validationCase.validation_assertion || validationCase.assertion || {};
  return (
    assertion.claim || assertion.title || validationCase.assertion_key || "Validation assertion"
  );
}

export function ValidationCaseCard({ validationCase, showPath = true, compact = false }) {
  const lead = caseSourceLead(validationCase);
  const [expanded, setExpanded] = useState(!compact);
  return (
    <article className="validation-case-card">
      <div className="validation-case-heading">
        <div>
          <div className="row" style={{ gap: 7, flexWrap: "wrap" }}>
            {lead.reference && (
              <span className="mono validation-case-reference">{lead.reference}</span>
            )}
            {lead.severity && <span className="subtle">{lead.severity}</span>}
          </div>
          <strong>{lead.title || assertionText(validationCase)}</strong>
          {lead.title && validationCase.assertion_key && (
            <div className="subtle validation-assertion">{assertionText(validationCase)}</div>
          )}
        </div>
        {compact && (
          <button className="btn ghost sm" onClick={() => setExpanded((value) => !value)}>
            {expanded ? "Hide path" : "View path"}
          </button>
        )}
      </div>
      <ValidationCaseStatus validationCase={validationCase} compact={compact} />
      {expanded && showPath && (
        <div className="validation-case-details">
          <div>
            <div className="validation-detail-label">Static path</div>
            <TypedHops
              staticPath={
                validationCase.static_path || validationCase.static_path_json || validationCase.path
              }
              legacyPath={validationCase.lead_attack_path_json || validationCase.path_json}
              compact={compact}
            />
          </div>
          <div>
            <div className="validation-detail-label">Live binding</div>
            <LiveBinding validationCase={validationCase} compact={compact} />
          </div>
        </div>
      )}
    </article>
  );
}

export function ValidationCaseList({
  cases,
  emptyText = "No validation cases have been compiled yet.",
}) {
  if (!cases || cases.length === 0) return <div className="subtle">{emptyText}</div>;
  return (
    <div className="validation-case-list">
      {cases.map((validationCase) => (
        <ValidationCaseCard
          key={validationCase.id ?? `${validationCase.mapping_id}-${validationCase.assertion_key}`}
          validationCase={validationCase}
          compact
        />
      ))}
    </div>
  );
}

export function ValidationCaseSummary({ cases }) {
  const counts = useMemo(() => {
    const result = { total: cases?.length || 0, runnable: 0, blocked: 0, confirmed: 0 };
    for (const validationCase of cases || []) {
      if (validationCase.readiness_status === "resolved") result.runnable += 1;
      else result.blocked += 1;
      if (validationCase.execution_status === "confirmed") result.confirmed += 1;
    }
    return result;
  }, [cases]);
  if (!counts.total) return null;
  return (
    <div className="validation-case-summary">
      <span>
        {counts.total} case{counts.total === 1 ? "" : "s"}
      </span>
      <span className="summary-ok">{counts.runnable} runnable</span>
      <span className="summary-warn">{counts.blocked} blocked</span>
      {counts.confirmed > 0 && <span className="summary-ok">{counts.confirmed} confirmed</span>}
    </div>
  );
}

export function ValidationCaseResults({ cases }) {
  const groups = useMemo(() => {
    const byLead = new Map();
    for (const validationCase of cases || []) {
      const lead = caseSourceLead(validationCase);
      const key = lead.id ?? lead.reference ?? validationCase.origin_lead_id ?? "unknown";
      if (!byLead.has(key)) byLead.set(key, { lead, cases: [] });
      byLead.get(key).cases.push(validationCase);
    }
    return [...byLead.values()];
  }, [cases]);
  if (groups.length === 0) return null;
  return (
    <section className="campaign-validation-results">
      <div className="row spread" style={{ gap: 10, flexWrap: "wrap", marginBottom: 10 }}>
        <div>
          <div className="form-section-title" style={{ margin: 0 }}>
            Validation case results
          </div>
          <div className="subtle" style={{ fontSize: 12, marginTop: 4 }}>
            Cases stay grouped under the original source finding, including cases that could not run
            on this target.
          </div>
        </div>
        <ValidationCaseSummary cases={cases} />
      </div>
      <div className="validation-result-groups">
        {groups.map((group, index) => (
          <div
            className="validation-result-group"
            key={group.lead.id ?? group.lead.reference ?? index}
          >
            <div className="validation-result-group-heading">
              <strong>{group.lead.reference || "Source finding"}</strong>
              <span>{group.lead.title || "Untitled source finding"}</span>
            </div>
            <ValidationCaseList cases={group.cases} />
          </div>
        ))}
      </div>
    </section>
  );
}
