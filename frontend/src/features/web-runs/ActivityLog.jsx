import { useState, useRef, useEffect } from "react";
import { truncUrl } from "../../shared/lib/urls.js";
export function ActivityLog({ runId, activityLog, sitePlanData, active, onClearLog, onError }) {
  const [clearBusy, setClearBusy] = useState("");
  const [expandedLogIds, setExpandedLogIds] = useState(new Set());
  const toggleLogId = (id) =>
    setExpandedLogIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const activityFeedRef = useRef(null);
  // Auto-scroll activity feed when new entries arrive
  useEffect(() => {
    if (!active || !activityFeedRef.current) return;
    activityFeedRef.current.scrollTop = activityFeedRef.current.scrollHeight;
  }, [activityLog.length, active]);

  return (
    <div className="activity-feed" ref={activityFeedRef}>
      <div className="activity-log-toolbar">
        <span className="activity-count-label">
          {activityLog.length} event{activityLog.length !== 1 ? "s" : ""}
        </span>
        {activityLog.some((e) => e.data?.mode === "agentic") && (
          <span className="activity-mode-badge">Continuous session</span>
        )}
        <a className="btn ghost sm" href={`/api/test-runs/${runId}/thinking-log/export`} download>
          Export log ↓
        </a>
        {activityLog.length > 0 && (
          <button
            className="btn danger-outline sm"
            disabled={clearBusy === "activity"}
            onClick={async () => {
              if (!confirm("Clear all activity log entries for this run?")) return;
              setClearBusy("activity");
              onError(null);
              try {
                await onClearLog();
              } catch (e) {
                onError(e.message);
              } finally {
                setClearBusy("");
              }
            }}
          >
            {clearBusy === "activity" ? "Clearing…" : "Clear"}
          </button>
        )}
      </div>
      {sitePlanData && (
        <div className="site-plan-card">
          <div className="site-plan-header">
            <span className="site-plan-label">Site Test Plan</span>
            <span className="site-plan-badge">LLM Analysis</span>
          </div>
          <div className="site-plan-summary">{sitePlanData.app_summary}</div>
          {(sitePlanData.hypotheses || []).length > 0 && (
            <div className="site-plan-section">
              <div className="site-plan-section-title">Attack Hypotheses</div>
              <div className="hypotheses-list">
                {(sitePlanData.hypotheses || []).map((h, i) => (
                  <div key={i} className="hypothesis-row">
                    <span className="owasp-badge">{h.owasp || "?"}</span>
                    <div className="hypothesis-body">
                      <div className="hypothesis-label">{h.hypothesis}</div>
                      <div className="hypothesis-desc">{h.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {(sitePlanData.critical_areas || []).length > 0 && (
            <div className="site-plan-section">
              <div className="site-plan-section-title">Critical Areas</div>
              <div className="critical-areas-list">
                {(sitePlanData.critical_areas || []).map((a, i) => (
                  <span key={i} className="critical-area-tag">
                    {a}
                  </span>
                ))}
              </div>
            </div>
          )}
          {sitePlanData.test_notes && (
            <div className="site-plan-section">
              <div className="site-plan-section-title">Test Notes</div>
              <div className="site-plan-notes">{sitePlanData.test_notes}</div>
            </div>
          )}
        </div>
      )}
      {activityLog.length === 0 && (
        <div
          className="subtle"
          style={{
            padding: "24px",
            textAlign: "center",
          }}
        >
          No activity yet. Start a Crawl or Dynamic Scan to begin.
        </div>
      )}
      {activityLog.map((entry) => {
        const PHASE_META = {
          crawl: {
            label: "Crawl",
            cls: "phase-sweep",
          },
          auth: {
            label: "Auth",
            cls: "phase-plan",
          },
          reconcile: {
            label: "Access",
            cls: "phase-followup",
          },
          site_plan: {
            label: "Plan",
            cls: "phase-plan",
          },
          page_plan: {
            label: "Probes",
            cls: "phase-probes",
          },
          page_followup: {
            label: "Follow-up",
            cls: "phase-followup",
          },
          page_analysis: {
            label: "Finding",
            cls: entry.data?.finding_count > 0 ? "phase-finding" : "phase-ok",
          },
          sweep: {
            label: "Sweep",
            cls: "phase-sweep",
          },
          llm_request: {
            label: "LLM ►",
            cls: "phase-llm-req",
          },
          llm_response: {
            label: "LLM ◄",
            cls: "phase-llm-resp",
          },
          llm_heartbeat: {
            label: "LLM ⟳",
            cls: "phase-llm-wait",
          },
          llm_protocol: {
            label: "⚠ LLM",
            cls: "phase-warning",
          },
          llm_pacing: {
            label: "LLM pacing",
            cls: "phase-llm-wait",
          },
          credential_warning: {
            label: "⚠ Auth",
            cls: "phase-warning",
          },
          thinking_step: {
            label: entry.status === "deciding" ? "···" : "Step",
            cls: "phase-thinking",
          },
          thinking_analysis: {
            label: "Report",
            cls: "phase-reporting",
          },
          reporting_turn: {
            label: "Turn",
            cls: entry.data?.findings_this_turn > 0 ? "phase-finding" : "phase-ok",
          },
          post_scan_review: {
            label: "Review",
            cls: "phase-reporting",
          },
          post_review_turn: {
            label: "Review",
            cls: entry.data?.low_confidence > 0 ? "phase-warning" : "phase-ok",
          },
          execution_monitor: {
            label: "Execution Monitor",
            cls: "phase-warning",
          },
          mentor_guidance: {
            label: "Mentor Guidance",
            cls: "phase-warning",
          },
          session_validator: {
            label: "Session Validator",
            cls: "phase-warning",
          },
          test_lead_completion_policy: {
            label: "Test Lead Completion Gate",
            cls: "phase-other",
          },
        };
        const _baseMeta = PHASE_META[entry.phase] || {
          label: entry.phase,
          cls: "phase-other",
        };
        const meta =
          entry.status === "error"
            ? {
                label: _baseMeta.label,
                cls: "phase-finding",
              }
            : entry.status === "warning"
              ? {
                  label: _baseMeta.label,
                  cls: "phase-warning",
                }
              : _baseMeta;
        const suffix =
          entry.status === "complete"
            ? " ✓"
            : entry.status === "start"
              ? " …"
              : entry.status === "error"
                ? " ✗"
                : entry.status === "warning"
                  ? " ⚠"
                  : "";
        // Augment llm_request message to surface agentic context count
        const displayMessage =
          entry.phase === "llm_request" && entry.data?.message_count != null
            ? entry.message.replace(
                /\(.*messages in context\)/,
                `(${entry.data.message_count} msgs in context)`,
              )
            : entry.message;
        const hasThinkingDetail =
          entry.phase === "thinking_step" &&
          !!(
            entry.data?.observation ||
            entry.data?.hypothesis ||
            entry.data?.payload_purpose ||
            entry.data?.payload_summary ||
            entry.data?.tool_input ||
            entry.data?.tool_output
          );
        const hasReportingDetail =
          entry.phase === "reporting_turn" && entry.data?.titles?.length > 0;
        const hasLlmDiagnostics = !!(
          entry.data?.native_stop_reason ||
          entry.data?.provider_diagnostics?.length ||
          entry.data?.termination_reason
        );
        const hasInterventionDetail =
          entry.phase === "execution_monitor" ||
          entry.phase === "mentor_guidance" ||
          entry.phase === "session_validator" ||
          entry.phase === "test_lead_completion_policy";
        const hasPayload = !!(
          entry.data?.prompt ||
          entry.data?.raw_response ||
          hasThinkingDetail ||
          hasReportingDetail ||
          hasLlmDiagnostics ||
          hasInterventionDetail
        );
        const isExpanded = expandedLogIds.has(entry._id);
        return (
          <div key={entry._id}>
            <div
              className={"activity-entry" + (hasPayload ? " activity-entry--expandable" : "")}
              onClick={hasPayload ? () => toggleLogId(entry._id) : undefined}
            >
              <span className="activity-ts">{entry._ts}</span>
              <span className={"activity-badge " + meta.cls}>
                {meta.label}
                {suffix}
              </span>
              {entry.page_url && (
                <span className="activity-url mono" title={entry.page_url}>
                  {truncUrl(entry.page_url, 42)}
                </span>
              )}
              <span className="activity-msg">{displayMessage}</span>
              {hasPayload && (
                <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
              )}
            </div>
            {isExpanded && (
              <div className="activity-payload">
                {entry.data?.prompt && (
                  <>
                    <div className="activity-payload-label">Prompt</div>
                    <pre>{entry.data.prompt}</pre>
                  </>
                )}
                {entry.data?.raw_response && (
                  <>
                    <div
                      className="activity-payload-label"
                      style={{
                        marginTop: entry.data?.prompt ? 8 : 0,
                      }}
                    >
                      Response
                    </div>
                    <pre>{entry.data.raw_response}</pre>
                  </>
                )}
                {hasLlmDiagnostics && (
                  <>
                    <div
                      className="activity-payload-label"
                      style={{ marginTop: entry.data?.raw_response ? 8 : 0 }}
                    >
                      LLM diagnostics
                    </div>
                    <pre>
                      {JSON.stringify(
                        {
                          provider: entry.data?.provider,
                          model: entry.data?.model,
                          native_stop_reason: entry.data?.native_stop_reason,
                          no_usable_content: entry.data?.no_usable_content,
                          retry: entry.data?.no_tool_retry,
                          retry_limit: entry.data?.no_tool_retry_limit,
                          message_count: entry.data?.message_count,
                          context_chars: entry.data?.context_chars,
                          termination_reason: entry.data?.termination_reason,
                          explicit_done: entry.data?.explicit_done,
                          provider_diagnostics: entry.data?.provider_diagnostics,
                        },
                        null,
                        2,
                      )}
                    </pre>
                  </>
                )}
                {hasInterventionDetail && (
                  <>
                    <div className="activity-payload-label">
                      {entry.data?.emitter || "Scan supervisor"} details
                    </div>
                    <pre>{JSON.stringify(entry.data, null, 2)}</pre>
                  </>
                )}
                {hasThinkingDetail && (
                  <>
                    {entry.data?.observation && (
                      <>
                        <div className="activity-payload-label">Observation</div>
                        <pre>{entry.data.observation}</pre>
                      </>
                    )}
                    {entry.data?.hypothesis && (
                      <>
                        <div
                          className="activity-payload-label"
                          style={{
                            marginTop: 6,
                          }}
                        >
                          Hypothesis
                        </div>
                        <pre>{entry.data.hypothesis}</pre>
                      </>
                    )}
                    {entry.data?.payload_purpose && (
                      <>
                        <div
                          className="activity-payload-label"
                          style={{
                            marginTop: 6,
                          }}
                        >
                          Payload purpose
                        </div>
                        <pre>{entry.data.payload_purpose}</pre>
                      </>
                    )}
                    {entry.data?.payload_summary && (
                      <>
                        <div
                          className="activity-payload-label"
                          style={{
                            marginTop: 6,
                          }}
                        >
                          Payload
                        </div>
                        <pre>{entry.data.payload_summary}</pre>
                      </>
                    )}
                    {entry.data?.tool_input && (
                      <>
                        <div
                          className="activity-payload-label"
                          style={{
                            marginTop: 6,
                          }}
                        >
                          Sub-tool Input ({entry.data.tool})
                        </div>
                        <pre>{JSON.stringify(entry.data.tool_input, null, 2)}</pre>
                      </>
                    )}
                    {entry.data?.tool_output && (
                      <>
                        <div
                          className="activity-payload-label"
                          style={{
                            marginTop: 6,
                          }}
                        >
                          Sub-tool Output
                        </div>
                        <pre>{JSON.stringify(entry.data.tool_output, null, 2)}</pre>
                      </>
                    )}
                  </>
                )}
                {entry.phase === "reporting_turn" && entry.data?.titles?.length > 0 && (
                  <>
                    <div className="activity-payload-label">Issues identified this turn</div>
                    <ul
                      style={{
                        margin: "4px 0 0 0",
                        paddingLeft: 18,
                      }}
                    >
                      {entry.data.titles.map((t, i) => (
                        <li key={i}>{t}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
