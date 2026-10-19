import { useState, useRef, useEffect } from "react";
import { truncUrl } from "../../shared/lib/urls.js";
import {
  buildRefusalTraces,
  logEventTypes,
  LOG_EVENT_TYPES,
  visibleLogEntries,
} from "./activityLogFilters.js";

const TRACE_OUTCOMES = {
  succeeded: { label: "Retry succeeded", description: "The provider accepted the retry." },
  skipped: {
    label: "Retry refused · test skipped",
    description: "The retry was refused and AESPA left this test unresolved.",
  },
  stopped: { label: "Scan stopped", description: "The provider refusal stopped the scan." },
  pending: { label: "No outcome recorded", description: "The log has no retry result yet." },
};

function OriginalLogEvent({ entry }) {
  const [showData, setShowData] = useState(false);
  return (
    <div className="activity-refusal-trace-event">
      <time>{entry._ts}</time>
      <span>{entry.message}</span>
      {entry.data && Object.keys(entry.data).length > 0 && (
        <details onToggle={(event) => setShowData(event.currentTarget.open)}>
          <summary>View event data</summary>
          {showData && <pre>{JSON.stringify(entry.data, null, 2)}</pre>}
        </details>
      )}
    </div>
  );
}

function RefusalTrace({ trace }) {
  const outcome = TRACE_OUTCOMES[trace.outcome];
  const [copiedPrompt, setCopiedPrompt] = useState(null);
  const [copyError, setCopyError] = useState("");
  const copyPrompt = async (prompt, index) => {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopiedPrompt(index);
      setCopyError("");
    } catch {
      setCopyError("Could not copy the prompt.");
    }
  };
  return (
    <article className="activity-refusal-trace">
      <div className="activity-refusal-trace-heading">
        <strong>Step {trace.step}</strong>
        <span className="activity-refusal-trace-time">{trace.time}</span>
        <span
          className={`activity-refusal-trace-outcome activity-refusal-trace-outcome--${trace.outcome}`}
        >
          {outcome.label}
        </span>
      </div>
      <p>{outcome.description}</p>
      <div className="activity-refusal-trace-context">
        <span>Last test before refusal</span>
        {trace.precedingTest ? (
          <>
            <strong>{trace.precedingTest.purpose || trace.precedingTest.action}</strong>
            {trace.precedingTest.purpose && <div>{trace.precedingTest.action}</div>}
            {trace.precedingTest.target && <code>{trace.precedingTest.target}</code>}
          </>
        ) : (
          <div>No preceding test was recorded for this step.</div>
        )}
      </div>
      <ol className="activity-refusal-trace-timeline">
        {trace.attempts.map((attempt, index) => (
          <li
            className={`activity-refusal-trace-point activity-refusal-trace-point--${attempt.outcome}`}
            key={`${attempt.startedAt}-${index}`}
          >
            <strong>Try {index + 1}</strong>
            <span>{attempt.label}</span>
            <b>{attempt.outcome === "pending" ? "Waiting for result" : attempt.outcome}</b>
            <time>
              {attempt.startedAt}
              {attempt.finishedAt &&
                attempt.finishedAt !== attempt.startedAt &&
                ` → ${attempt.finishedAt}`}
            </time>
          </li>
        ))}
      </ol>
      <div className="activity-refusal-trace-after">
        <span>What happened after</span>
        <span>{trace.nextAction?.message ?? "No later action recorded"}</span>
        {trace.nextAction?.time && <time>{trace.nextAction.time}</time>}
      </div>
      <div className="activity-refusal-trace-prompts">
        {trace.rejectedPrompts.length > 0 ? (
          trace.rejectedPrompts.map((prompt, index) => {
            const label =
              trace.rejectedPrompts.length === 1
                ? "Rejected prompt"
                : `Rejected prompt ${index + 1}`;
            return (
              <div className="activity-refusal-trace-prompt" key={`${prompt.time}-${index}`}>
                <div className="activity-refusal-trace-prompt-heading">
                  <strong>{label}</strong>
                  <button
                    type="button"
                    className="btn ghost sm"
                    onClick={() => copyPrompt(prompt.text, index)}
                  >
                    {copiedPrompt === index ? "Copied" : "Copy prompt"}
                  </button>
                </div>
                <details>
                  <summary>View full prompt</summary>
                  <pre>{prompt.text}</pre>
                </details>
              </div>
            );
          })
        ) : (
          <div className="activity-refusal-trace-prompt-missing">
            The full prompt was not saved for this refusal.
          </div>
        )}
        {copyError && <div role="alert">{copyError}</div>}
      </div>
      <details className="activity-refusal-trace-events">
        <summary>Show original log events</summary>
        {trace.events.map((entry, index) => (
          <OriginalLogEvent entry={entry} key={`${entry._id}-${index}`} />
        ))}
      </details>
    </article>
  );
}
export function ActivityLog({
  runId,
  activityLog,
  sitePlanData,
  active,
  onClearLog,
  onError,
  view = "log",
}) {
  const [clearBusy, setClearBusy] = useState("");
  const [expandedLogIds, setExpandedLogIds] = useState(new Set());
  const [showDisplayOptions, setShowDisplayOptions] = useState(false);
  const displayOptionsRef = useRef(null);
  const displayOptionsButtonRef = useRef(null);
  const [newestFirst, setNewestFirst] = useState(true);
  const [selectedTypes, setSelectedTypes] = useState(new Set());
  const traceView = view === "errors";
  const refusalData = traceView ? buildRefusalTraces(activityLog) : null;
  const otherLlmErrors = traceView
    ? activityLog.filter(
        (entry, index) =>
          !refusalData.usedIndices.has(index) && logEventTypes(entry).has("llm-errors"),
      )
    : [];
  if (traceView && newestFirst) otherLlmErrors.reverse();
  const displayedEntries = traceView
    ? otherLlmErrors
    : visibleLogEntries(activityLog, selectedTypes, newestFirst);
  const refusalTraces = traceView
    ? newestFirst
      ? [...refusalData.traces].reverse()
      : refusalData.traces
    : [];
  const traceCounts = { succeeded: 0, failed: 0, pending: 0 };
  for (const trace of refusalTraces) {
    const skippedRequests = trace.events.filter((entry) => entry.data?.refusal_skips).length;
    traceCounts.failed += skippedRequests;
    if (trace.outcome === "succeeded") traceCounts.succeeded += 1;
    else if (trace.outcome === "pending") traceCounts.pending += 1;
    else if (!skippedRequests) traceCounts.failed += 1;
  }
  const toggleLogId = (id) =>
    setExpandedLogIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const activityFeedRef = useRef(null);
  useEffect(() => {
    if (!showDisplayOptions) return;
    const onPointerDown = (event) => {
      if (!displayOptionsRef.current?.contains(event.target)) setShowDisplayOptions(false);
    };
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        setShowDisplayOptions(false);
        displayOptionsButtonRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [showDisplayOptions]);
  useEffect(() => {
    if (!active || !activityFeedRef.current) return;
    activityFeedRef.current.scrollTop = newestFirst ? 0 : activityFeedRef.current.scrollHeight;
  }, [activityLog.length, active, newestFirst, selectedTypes, traceView]);

  return (
    <div className="activity-log">
      <div className="activity-log-toolbar">
        <span className="activity-count-label">
          {traceView ? (
            <>
              Refusals: {traceCounts.succeeded} succeeded · {traceCounts.failed} failed
              {traceCounts.pending > 0 && <> · {traceCounts.pending} pending</>} ·{" "}
              {otherLlmErrors.length} other LLM error{otherLlmErrors.length !== 1 ? "s" : ""}
            </>
          ) : (
            <>
              {displayedEntries.length} of {activityLog.length} event
              {activityLog.length !== 1 ? "s" : ""}
            </>
          )}
        </span>
        {!traceView && activityLog.some((e) => e.data?.mode === "agentic") && (
          <span className="activity-mode-badge">Continuous session</span>
        )}
        <div className="activity-log-display-anchor" ref={displayOptionsRef}>
          <button
            ref={displayOptionsButtonRef}
            className="btn ghost sm"
            aria-expanded={showDisplayOptions}
            aria-controls="activity-log-display-options"
            onClick={() => setShowDisplayOptions((value) => !value)}
          >
            Display options
          </button>
          {showDisplayOptions && (
            <div
              id="activity-log-display-options"
              className="activity-log-display-options"
              role="group"
              aria-label="Display options"
            >
              <label className="activity-log-option">
                <input
                  type="checkbox"
                  checked={newestFirst}
                  onChange={(event) => setNewestFirst(event.target.checked)}
                />
                Newest first
              </label>
              {!traceView && <div className="activity-log-filter-title">Event type</div>}
              {!traceView && (
                <div className="activity-log-filter-options">
                  <label className="activity-log-option">
                    <input
                      type="checkbox"
                      checked={selectedTypes.size === 0}
                      onChange={() => setSelectedTypes(new Set())}
                    />
                    All
                  </label>
                  {LOG_EVENT_TYPES.map(([type, label]) => (
                    <label className="activity-log-option" key={type}>
                      <input
                        type="checkbox"
                        checked={selectedTypes.has(type)}
                        onChange={() =>
                          setSelectedTypes((previous) => {
                            const next = new Set(previous);
                            if (next.has(type)) next.delete(type);
                            else next.add(type);
                            return next;
                          })
                        }
                      />
                      {label}
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        {!traceView && (
          <a className="btn ghost sm" href={`/api/test-runs/${runId}/thinking-log/export`} download>
            Export log ↓
          </a>
        )}
        {!traceView && activityLog.length > 0 && (
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
      <div className="activity-feed" ref={activityFeedRef}>
        {!traceView && sitePlanData && (
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
        {activityLog.length === 0 && !traceView && (
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
        {displayedEntries.length === 0 &&
          refusalTraces.length === 0 &&
          (traceView || activityLog.length > 0) && (
            <div className="activity-log-empty">
              {traceView ? "No LLM errors recorded." : "No events match these filters."}
            </div>
          )}
        {traceView && refusalTraces.length > 0 && (
          <div className="activity-refusal-traces">
            {refusalTraces.map((trace) => (
              <RefusalTrace key={trace.id} trace={trace} />
            ))}
          </div>
        )}
        {traceView && otherLlmErrors.length > 0 && (
          <div className="activity-refusal-other-heading">Other LLM errors</div>
        )}
        {(traceView ? otherLlmErrors : displayedEntries).map((entry) => {
          const PHASE_META = {
            crawl: {
              label: "Crawl",
              cls: "phase-sweep",
            },
            crawl_workflow: {
              label: "Workflows",
              cls: "phase-sweep",
            },
            crawl_workflow_retry: {
              label: "Workflow retry",
              cls: "phase-sweep",
            },
            crawl_note: {
              label: "Workflow result",
              cls: entry.status === "complete" ? "phase-ok" : "phase-other",
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
    </div>
  );
}
