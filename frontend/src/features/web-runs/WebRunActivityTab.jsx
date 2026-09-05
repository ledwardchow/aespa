import * as webRunsApi from "../../shared/api/webRuns.js";
import { TokenUsageBar } from "../../shared/ui/TokenUsageBar.jsx";

import { truncUrl } from "../../shared/lib/urls.js";
import { AliceChatPanel } from "./AliceChatPanel.jsx";
import { FindingReferenceLink } from "../../shared/ui/FindingReferenceLink.jsx";
export function WebRunActivityTab(props) {
  const {
    activityLog,
    tokenUsage,
    setTokenExpanded,
    tokenExpanded,
    activitySubTab,
    setActivitySubTab,
    agents,
    normalizeAgentForRun,
    activityFeedRef,
    runId,
    clearBusy,
    setClearBusy,
    setClearError,
    setActivityLog,
    setSitePlanData,
    setTokenUsage,
    sitePlanData,
    expandedLogIds,
    toggleLogId,
    collapsedAgentIds,
    toggleAgentId,
    defaultAgentRoster,
    representsAgent,
    aliceChats,
    activeAliceTabId,
    setActiveAliceTabId,
    deleteAliceTab,
    createAliceTab,
    aliceChatHeight,
    aliceMessages,
    aliceExpandedThinkIds,
    setAliceExpandedThinkIds,
    aliceThinkingTabId,
    aliceIsThinking,
    startAliceResize,
    aliceInputText,
    handleAliceSend,
    setAliceInputText,
    handleAliceStop,
    submitAliceDirective,
    agentRoleLabel,
    agentCurrentTask,
    agentCrawlEvents,
    agentTaskHistory,
    agentStatusLabel,
  } = props;
  return (
    <>
      <div className="activity-panel">
        {(() => {
          return (
            <>
              <TokenUsageBar
                tokenUsage={tokenUsage}
                tokenExpanded={tokenExpanded}
                setTokenExpanded={setTokenExpanded}
              />
              <div className="activity-sub-tab-bar">
                <button
                  className={
                    "activity-sub-tab-btn" + (activitySubTab === "agents" ? " active" : "")
                  }
                  onClick={() => setActivitySubTab("agents")}
                >
                  Agents
                  {agents.map(normalizeAgentForRun).some((a) => a.status === "active") ? " ●" : ""}
                </button>
                <button
                  className={
                    "activity-sub-tab-btn" + (activitySubTab === "specialists" ? " active" : "")
                  }
                  onClick={() => setActivitySubTab("specialists")}
                >
                  Specialist
                  {agents
                    .filter((a) => a.id.startsWith("specialist-"))
                    .some((a) => a.status === "active")
                    ? " ●"
                    : ""}
                </button>
                <button
                  className={"activity-sub-tab-btn" + (activitySubTab === "log" ? " active" : "")}
                  onClick={() => setActivitySubTab("log")}
                >
                  Log
                </button>
              </div>
            </>
          );
        })()}
        {activitySubTab === "log" && (
          <div className="activity-feed" ref={activityFeedRef}>
            <div className="activity-log-toolbar">
              <span className="activity-count-label">
                {activityLog.length} event{activityLog.length !== 1 ? "s" : ""}
              </span>
              {activityLog.some((e) => e.data?.mode === "agentic") && (
                <span className="activity-mode-badge">Continuous session</span>
              )}
              <a
                className="btn ghost sm"
                href={`/api/test-runs/${runId}/thinking-log/export`}
                download
              >
                Export log ↓
              </a>
              {activityLog.length > 0 && (
                <button
                  className="btn danger-outline sm"
                  disabled={clearBusy === "activity"}
                  onClick={async () => {
                    if (!confirm("Clear all activity log entries for this run?")) return;
                    setClearBusy("activity");
                    setClearError(null);
                    try {
                      await webRunsApi.clearScanLog(runId);
                      setActivityLog([]);
                      setSitePlanData(null);
                      setTokenUsage(null);
                    } catch (e) {
                      setClearError(e.message);
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
        )}
        {activitySubTab === "specialists" && (
          <div className="agents-panel">
            {(() => {
              const specialistAgents = agents
                .filter((ag) => ag.id.startsWith("specialist-"))
                .map(normalizeAgentForRun);
              if (specialistAgents.length === 0)
                return (
                  <div
                    className="subtle"
                    style={{
                      padding: "24px",
                      textAlign: "center",
                    }}
                  >
                    No specialist agents dispatched yet.
                  </div>
                );
              return specialistAgents.map((sa) => {
                const saActive = sa.status === "active";
                const saTask =
                  sa.currentTask || sa.taskHistory?.slice(-1)[0]?.task || "Initialising…";
                const saSteps = sa.stepHistory || [];
                const saExpanded = saSteps.length > 0 && !collapsedAgentIds.has(sa.id);
                const threadLabel = sa.id.replace("specialist-", "").replace(/-([0-9]+)$/, " #$1");
                return (
                  <div
                    key={sa.id}
                    className={
                      "agent-row" +
                      (saActive ? " agent-row--active" : " agent-row--complete") +
                      (saSteps.length > 0 ? " agent-row--expandable" : "")
                    }
                    onClick={saSteps.length > 0 ? () => toggleAgentId(sa.id) : undefined}
                  >
                    <span
                      className={"agent-dot" + (saActive ? " agent-dot--active" : "")}
                      aria-hidden="true"
                    ></span>
                    <span
                      className={"agent-role-name" + (saActive ? " agent-role-name--pulse" : "")}
                      style={{
                        textTransform: "capitalize",
                      }}
                    >
                      {threadLabel}
                    </span>
                    <span
                      className={
                        "agent-badge" + (saActive ? " agent-badge-active" : " agent-badge-complete")
                      }
                    >
                      {saActive ? "ACTIVE" : "DONE"}
                    </span>
                    <span className="agent-current-task" title={saTask}>
                      {saTask.length > 90 ? saTask.slice(0, 89) + "…" : saTask}
                    </span>
                    {saSteps.length > 0 && (
                      <span className="activity-expand-chevron">{saExpanded ? "▲" : "▼"}</span>
                    )}
                    {saSteps.length > 0 && saExpanded && (
                      <div className="agent-task-history">
                        {saSteps
                          .slice()
                          .reverse()
                          .map((s, i) => (
                            <div key={i} className="agent-history-entry">
                              <span className="activity-ts">{s.ts}</span>
                              <span className="agent-step-method">
                                {s.method ? (
                                  <>
                                    {s.method}{" "}
                                    {s.url ? <span title={s.url}>{truncUrl(s.url, 80)}</span> : ""}
                                  </>
                                ) : (
                                  s.action_type || "tool"
                                )}
                              </span>
                              {s.observation && (
                                <span className="agent-history-outcome" title={s.observation}>
                                  {String(s.observation).slice(0, 80)}
                                </span>
                              )}
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                );
              });
            })()}
          </div>
        )}
        {activitySubTab === "agents" && (
          <div className="agents-panel">
            {(() => {
              const roster = defaultAgentRoster();
              // Container slots (specialist/burp/validator) must always render as
              // their placeholder so the multi-agent container row fires correctly.
              const CONTAINER_IDS = new Set(["specialist", "burp", "validator"]);
              const rosterAgents = roster.map((p) =>
                CONTAINER_IDS.has(p.id) ? p : agents.find((a) => representsAgent(a, p)) || p,
              );
              const extras = agents.filter((a) => !roster.some((p) => representsAgent(a, p)));
              const shownAgents = [...rosterAgents, ...extras].map(normalizeAgentForRun);
              const renderRow = (a) => {
                // ── Specialist container row ────────────────────────────────
                if (a.id === "specialist") {
                  const specialistAgents = agents
                    .filter((ag) => ag.id.startsWith("specialist-"))
                    .map(normalizeAgentForRun);
                  const anyActive = specialistAgents.some((ag) => ag.status === "active");

                  const activeCount = specialistAgents.filter(
                    (ag) => ag.status === "active",
                  ).length;
                  const doneCount = specialistAgents.length - activeCount;
                  const summaryTask =
                    specialistAgents.length === 0
                      ? "No specialist dispatched"
                      : activeCount > 0 && doneCount > 0
                        ? `${activeCount} running, ${doneCount} complete`
                        : activeCount > 0
                          ? `${activeCount} thread${activeCount !== 1 ? "s" : ""} running`
                          : `${doneCount} thread${doneCount !== 1 ? "s" : ""} complete`;
                  const canExpand = specialistAgents.length > 0;
                  const isExpanded = canExpand && !collapsedAgentIds.has("specialist");
                  return (
                    <div
                      key="specialist"
                      className={
                        "agent-row" +
                        (anyActive ? " agent-row--active" : " agent-row--complete") +
                        (canExpand ? " agent-row--expandable" : "")
                      }
                      onClick={canExpand ? () => toggleAgentId("specialist") : undefined}
                    >
                      <span
                        className={"agent-dot" + (anyActive ? " agent-dot--active" : "")}
                        aria-hidden="true"
                      ></span>
                      <span
                        className={"agent-role-name" + (anyActive ? " agent-role-name--pulse" : "")}
                      >
                        Specialist
                      </span>
                      <span
                        className={
                          "agent-badge" +
                          (anyActive ? " agent-badge-active" : " agent-badge-complete")
                        }
                      >
                        {anyActive ? "ACTIVE" : specialistAgents.length > 0 ? "COMPLETE" : "IDLE"}
                      </span>
                      <span className="agent-current-task">{summaryTask}</span>
                      {canExpand && (
                        <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
                      )}
                      {canExpand && isExpanded && (
                        <div className="agent-task-history">
                          {specialistAgents.map((sa) => {
                            const saActive = sa.status === "active";
                            const saTask =
                              sa.currentTask ||
                              sa.taskHistory?.slice(-1)[0]?.task ||
                              "Initialising…";
                            return (
                              <div
                                key={sa.id}
                                className={
                                  "agent-thread-row" + (saActive ? " agent-thread-row--active" : "")
                                }
                              >
                                <span
                                  className={
                                    "agent-dot agent-dot--sm" +
                                    (saActive ? " agent-dot--active" : "")
                                  }
                                  aria-hidden="true"
                                ></span>
                                <span className="agent-thread-id">
                                  {sa.id.replace("specialist-", "").replace(/-([0-9]+)$/, " #$1")}
                                </span>
                                <span
                                  className={
                                    "agent-badge agent-badge--sm" +
                                    (saActive ? " agent-badge-active" : " agent-badge-complete")
                                  }
                                >
                                  {saActive ? "ACTIVE" : "DONE"}
                                </span>
                                <span className="agent-current-task" title={saTask}>
                                  {saTask.length > 90 ? saTask.slice(0, 89) + "…" : saTask}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                }
                // ── Validator container row ────────────────────────────────
                if (a.id === "validator") {
                  const validatorAgents = agents
                    .filter((ag) => ag.id.startsWith("validator-"))
                    .map(normalizeAgentForRun);
                  const anyActive = validatorAgents.some((ag) => ag.status === "active");
                  const activeCount = validatorAgents.filter((ag) => ag.status === "active").length;
                  const doneCount = validatorAgents.length - activeCount;
                  const summaryTask =
                    validatorAgents.length === 0
                      ? "No validation running"
                      : activeCount > 0 && doneCount > 0
                        ? `${activeCount} validating, ${doneCount} complete`
                        : activeCount > 0
                          ? `${activeCount} finding${activeCount !== 1 ? "s" : ""} validating`
                          : `${doneCount} finding${doneCount !== 1 ? "s" : ""} validated`;
                  const canExpand = validatorAgents.length > 0;
                  const isExpanded = canExpand && !collapsedAgentIds.has("validator");
                  return (
                    <div
                      key="validator"
                      className={
                        "agent-row" +
                        (anyActive ? " agent-row--active" : " agent-row--complete") +
                        (canExpand ? " agent-row--expandable" : "")
                      }
                      onClick={canExpand ? () => toggleAgentId("validator") : undefined}
                    >
                      <span
                        className={"agent-dot" + (anyActive ? " agent-dot--active" : "")}
                        aria-hidden="true"
                      ></span>
                      <span
                        className={"agent-role-name" + (anyActive ? " agent-role-name--pulse" : "")}
                      >
                        Validator
                      </span>
                      <span
                        className={
                          "agent-badge" +
                          (anyActive ? " agent-badge-active" : " agent-badge-complete")
                        }
                      >
                        {anyActive ? "ACTIVE" : validatorAgents.length > 0 ? "COMPLETE" : "IDLE"}
                      </span>
                      <span className="agent-current-task">{summaryTask}</span>
                      {canExpand && (
                        <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
                      )}
                      {canExpand && isExpanded && (
                        <div className="agent-task-history">
                          {validatorAgents.map((va) => {
                            const vaActive = va.status === "active";
                            const vaTask =
                              va.currentTask ||
                              va.taskHistory?.slice(-1)[0]?.task ||
                              "Initialising…";
                            const vaOutcome = va.outcome || va.taskHistory?.slice(-1)[0]?.outcome;
                            const findingNum = va.id.replace("validator-", "");
                            return (
                              <div
                                key={va.id}
                                className={
                                  "agent-thread-row" + (vaActive ? " agent-thread-row--active" : "")
                                }
                              >
                                <span
                                  className={
                                    "agent-dot agent-dot--sm" +
                                    (vaActive ? " agent-dot--active" : "")
                                  }
                                  aria-hidden="true"
                                ></span>
                                <FindingReferenceLink
                                  reference={va.findingReference || `#${findingNum}`}
                                  href={
                                    va.findingReference
                                      ? `#/runs/${runId}/findings?finding=${encodeURIComponent(va.findingReference)}`
                                      : undefined
                                  }
                                />
                                <span
                                  className={
                                    "agent-badge agent-badge--sm" +
                                    (vaActive ? " agent-badge-active" : " agent-badge-complete")
                                  }
                                >
                                  {vaActive ? "ACTIVE" : "DONE"}
                                </span>
                                <span className="agent-current-task" title={vaTask}>
                                  {vaTask.length > 90 ? vaTask.slice(0, 89) + "…" : vaTask}
                                </span>
                                {vaOutcome && !vaActive && (
                                  <span className="agent-history-outcome">{vaOutcome}</span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                }
                // ── Burp container row ──────────────────────────────────────
                if (a.id === "burp") {
                  const burpAgents = agents
                    .filter((ag) => ag.id.startsWith("burp-"))
                    .map(normalizeAgentForRun);
                  const anyActive = burpAgents.some((ag) => ag.status === "active");

                  const activeCount = burpAgents.filter((ag) => ag.status === "active").length;
                  const doneCount = burpAgents.length - activeCount;
                  const summaryTask =
                    burpAgents.length === 0
                      ? "No active scan dispatched"
                      : activeCount > 0 && doneCount > 0
                        ? `${activeCount} scanning, ${doneCount} complete`
                        : activeCount > 0
                          ? `${activeCount} scan${activeCount !== 1 ? "s" : ""} running`
                          : `${doneCount} scan${doneCount !== 1 ? "s" : ""} complete`;
                  const canExpand = burpAgents.length > 0;
                  const isExpanded = canExpand && !collapsedAgentIds.has("burp");
                  return (
                    <div
                      key="burp"
                      className={
                        "agent-row" +
                        (anyActive ? " agent-row--active" : " agent-row--complete") +
                        (canExpand ? " agent-row--expandable" : "")
                      }
                      onClick={canExpand ? () => toggleAgentId("burp") : undefined}
                    >
                      <span
                        className={"agent-dot" + (anyActive ? " agent-dot--active" : "")}
                        aria-hidden="true"
                      ></span>
                      <span
                        className={"agent-role-name" + (anyActive ? " agent-role-name--pulse" : "")}
                      >
                        Burp
                      </span>
                      <span
                        className={
                          "agent-badge" +
                          (anyActive ? " agent-badge-active" : " agent-badge-complete")
                        }
                      >
                        {anyActive ? "ACTIVE" : burpAgents.length > 0 ? "COMPLETE" : "IDLE"}
                      </span>
                      <span className="agent-current-task">{summaryTask}</span>
                      {canExpand && (
                        <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
                      )}
                      {canExpand && isExpanded && (
                        <div className="agent-task-history">
                          {burpAgents.map((ba) => {
                            const baActive = ba.status === "active";
                            const baTask =
                              ba.currentTask ||
                              ba.taskHistory?.slice(-1)[0]?.task ||
                              "Initialising…";
                            return (
                              <div
                                key={ba.id}
                                className={
                                  "agent-thread-row" + (baActive ? " agent-thread-row--active" : "")
                                }
                              >
                                <span
                                  className={
                                    "agent-dot agent-dot--sm" +
                                    (baActive ? " agent-dot--active" : "")
                                  }
                                  aria-hidden="true"
                                ></span>
                                <span className="agent-thread-id">
                                  {ba.id.replace("burp-", "")}
                                </span>
                                <span
                                  className={
                                    "agent-badge agent-badge--sm" +
                                    (baActive ? " agent-badge-active" : " agent-badge-complete")
                                  }
                                >
                                  {baActive ? "ACTIVE" : ba.status === "failed" ? "FAILED" : "DONE"}
                                </span>
                                <span className="agent-current-task" title={baTask}>
                                  {baTask.length > 90 ? baTask.slice(0, 89) + "…" : baTask}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                }
                // ── A.L.I.C.E custom row ────────────────────────────────────
                if (a.id === "alice") {
                  const isExpanded = !collapsedAgentIds.has("alice");
                  const isActive = a.status === "active";
                  const currentTask = a.currentTask;
                  return (
                    <div
                      key="alice"
                      className="agent-row agent-row--alice-chat agent-row--expandable"
                      onClick={() => toggleAgentId("alice")}
                    >
                      <span
                        className={
                          "agent-dot agent-dot--alice" + (isActive ? " agent-dot--active" : "")
                        }
                        aria-hidden="true"
                      ></span>
                      <span
                        className={"agent-role-name" + (isActive ? " agent-role-name--pulse" : "")}
                      >
                        A.L.I.C.E
                      </span>
                      <span
                        className={
                          "agent-badge" +
                          (isActive ? " agent-badge-alice-active" : " agent-badge-alice-idle")
                        }
                      >
                        {isActive ? "ACTIVE" : "STANDBY"}
                      </span>
                      <span className="agent-current-task" title={currentTask}>
                        {currentTask}
                      </span>
                      <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
                      {isExpanded && (
                        <AliceChatPanel
                          runId={runId}
                          aliceChats={aliceChats}
                          activeAliceTabId={activeAliceTabId}
                          setActiveAliceTabId={setActiveAliceTabId}
                          deleteAliceTab={deleteAliceTab}
                          createAliceTab={createAliceTab}
                          aliceChatHeight={aliceChatHeight}
                          aliceMessages={aliceMessages}
                          aliceExpandedThinkIds={aliceExpandedThinkIds}
                          setAliceExpandedThinkIds={setAliceExpandedThinkIds}
                          startAliceResize={startAliceResize}
                          aliceInputText={aliceInputText}
                          setAliceInputText={setAliceInputText}
                          isActiveThinking={aliceThinkingTabId === activeAliceTabId}
                          aliceIsThinking={aliceIsThinking}
                          handleAliceSend={handleAliceSend}
                          handleAliceStop={handleAliceStop}
                          submitAliceDirective={submitAliceDirective}
                          onPopOut={() => toggleAgentId("alice")}
                        />
                      )}
                    </div>
                  );
                }
                const isActive = a.status === "active";
                const roleLabel = agentRoleLabel(a);
                const currentTask = agentCurrentTask(a);
                const crawlEvents = agentCrawlEvents(a);
                const taskHistory = agentTaskHistory(a);
                const canExpand =
                  (a.id === "crawler" && crawlEvents.length > 0) ||
                  taskHistory.length > 1 ||
                  taskHistory.some((h) => h.outcome);
                const isExpanded = canExpand && !collapsedAgentIds.has(a.id);
                return (
                  <div
                    key={a.id}
                    className={
                      "agent-row" +
                      (isActive ? " agent-row--active" : " agent-row--complete") +
                      (canExpand ? " agent-row--expandable" : "")
                    }
                    onClick={canExpand ? () => toggleAgentId(a.id) : undefined}
                  >
                    <span
                      className={"agent-dot" + (isActive ? " agent-dot--active" : "")}
                      aria-hidden="true"
                    ></span>
                    <span
                      className={"agent-role-name" + (isActive ? " agent-role-name--pulse" : "")}
                    >
                      {roleLabel}
                      {a.id.includes("-") &&
                      !["scanner", "crawler"].includes(a.id) &&
                      !a.id.startsWith("burp-") ? (
                        <>
                          <br />
                          <span className="agent-role-sub">
                            {a.id.replace(/^[a-z]+-/, "").replace(/-/g, " ")}
                          </span>
                        </>
                      ) : (
                        ""
                      )}
                    </span>
                    <span
                      className={
                        "agent-badge" + (isActive ? " agent-badge-active" : " agent-badge-complete")
                      }
                    >
                      {agentStatusLabel(a)}
                    </span>
                    <span className="agent-current-task" title={currentTask}>
                      {currentTask}
                    </span>
                    {canExpand && (
                      <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
                    )}
                    {canExpand && isExpanded && (
                      <div className="agent-task-history">
                        {a.id === "crawler" && crawlEvents.length > 0 ? (
                          <>
                            {crawlEvents
                              .slice()
                              .reverse()
                              .map((h, i) => (
                                <div
                                  key={i}
                                  className="agent-history-entry agent-history-entry--crawl"
                                >
                                  <span className="activity-ts">{h.ts}</span>
                                  <span className="agent-history-user">
                                    {h.username || "crawler"}
                                  </span>
                                  <span className="agent-history-task mono" title={h.url || ""}>
                                    {h.task ||
                                      (h.done
                                        ? `Finished (${h.pagesVisited || 0} pg)`
                                        : `${h.stageLabel || "Crawling"} · ${truncUrl(h.url || "", 112)}`)}
                                  </span>
                                </div>
                              ))}
                          </>
                        ) : (
                          <>
                            {taskHistory
                              .slice()
                              .reverse()
                              .map((h, i) => (
                                <div key={i} className="agent-history-entry">
                                  <span className="activity-ts">{h.ts}</span>
                                  <span className="agent-history-task">{h.task}</span>
                                  {h.outcome && (
                                    <span className="agent-history-outcome">{h.outcome}</span>
                                  )}
                                </div>
                              ))}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                );
              };
              return <>{shownAgents.map(renderRow)}</>;
            })()}
          </div>
        )}
      </div>
    </>
  );
}
