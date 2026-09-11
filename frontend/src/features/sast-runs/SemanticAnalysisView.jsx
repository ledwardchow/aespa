import { useMemo, useState } from "react";

const asArray = (value) => (Array.isArray(value) ? value : []);
const asObject = (value) => (value && typeof value === "object" ? value : {});
const titleCase = (value) => String(value || "unknown").replaceAll("_", " ");
const percent = (value) => `${Math.round(Number(value || 0) * 100)}%`;

function displayValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.map(displayValue).join(", ");
  if (typeof value === "object") {
    return value.name || value.title || value.path || value.id || JSON.stringify(value);
  }
  return String(value);
}

function countBy(items, field) {
  const counts = {};
  for (const item of items) {
    const key = String(item?.[field] || "unknown");
    counts[key] = (counts[key] || 0) + 1;
  }
  return counts;
}

function semanticEmptyState(label, status) {
  if (status === "running" || status === "scanning") {
    return {
      label: `${label} is not ready yet.`,
      message: "This analysis will appear as the scan progresses.",
    };
  }
  if (status === "pending") {
    return {
      label: `${label} has not been generated yet.`,
      message: "Start the SAST scan to generate this analysis.",
    };
  }
  if (status === "paused") {
    return {
      label: `${label} is waiting for the scan to continue.`,
      message: "Resume the scan to continue generating this analysis.",
    };
  }
  if (status === "failed" || status === "cancelled") {
    return {
      label: `${label} was not generated.`,
      message: "The scan ended before this analysis was ready.",
    };
  }
  return {
    label: `${label} is not available for this run.`,
    message: "Run the scan again with the current SAST workflow to generate this analysis.",
  };
}

function EmptySemanticState({ label, status }) {
  const emptyState = semanticEmptyState(label, status);
  return (
    <div className="sast-semantic-empty">
      <strong>{emptyState.label}</strong>
      <span>{emptyState.message}</span>
    </div>
  );
}

function MetricCards({ values }) {
  return (
    <div className="sast-semantic-metrics">
      {values.map(([label, value, hint]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
          {hint ? <small>{hint}</small> : null}
        </div>
      ))}
    </div>
  );
}

function ChipList({ title, values }) {
  const items = asArray(values);
  return (
    <section className="sast-panel">
      <div className="sast-panel-title">{title}</div>
      {items.length ? (
        <div className="sast-semantic-chips">
          {items.map((item, index) => (
            <span key={`${displayValue(item)}-${index}`}>{displayValue(item)}</span>
          ))}
        </div>
      ) : (
        <div className="subtle">None recorded.</div>
      )}
    </section>
  );
}

export function RepositoryModelView({ model, status }) {
  const normalized = asObject(model);
  const nodes = asArray(normalized.nodes);
  const warnings = [...asArray(normalized.warnings)];
  const reconciliation = asObject(normalized.reconciliation);
  if (reconciliation.status === "failed") {
    warnings.push({
      key: "model_reconciliation",
      status: "unresolved",
      message: reconciliation.warning || "Model reconciliation failed.",
    });
  }
  const [query, setQuery] = useState("");
  const visibleNodes = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return nodes.slice(0, 250);
    return nodes
      .filter((node) =>
        [node.kind, node.type, node.name, node.path, node.component_key, ...asArray(node.evidence)]
          .join(" ")
          .toLowerCase()
          .includes(needle),
      )
      .slice(0, 250);
  }, [nodes, query]);
  if (!nodes.length && !warnings.length)
    return <EmptySemanticState label="Repository model" status={status} />;
  const kinds = countBy(nodes, "kind");
  const unresolved = warnings.filter((warning) => warning.status !== "resolved").length;
  return (
    <div className="sast-semantic-layout">
      <MetricCards
        values={[
          ["Repository facts", nodes.length, `${Object.keys(kinds).length} kinds`],
          ["Components", new Set(nodes.map((node) => node.component_key).filter(Boolean)).size],
          ["Model warnings", warnings.length, `${unresolved} unresolved`],
          ["Files inventoried", normalized.stats?.production_files || 0],
        ]}
      />
      {warnings.length ? (
        <section className="sast-panel">
          <div className="sast-panel-header">
            <div>
              <div className="sast-panel-title">Completeness warnings</div>
              <div className="sast-panel-sub">Unresolved warnings prevent full coverage.</div>
            </div>
          </div>
          <div className="sast-semantic-list">
            {warnings.map((warning, index) => (
              <div key={warning.key || index}>
                <span
                  className={`sast-state sast-state-${warning.status === "resolved" ? "confirmed" : "inconclusive"}`}
                >
                  {warning.status || "unresolved"}
                </span>
                <strong>{titleCase(warning.key)}</strong>
                <p>{warning.message || "No explanation recorded."}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}
      <section className="sast-panel">
        <div className="sast-panel-header">
          <div>
            <div className="sast-panel-title">Repository facts</div>
            <div className="sast-panel-sub">
              {Object.entries(kinds)
                .map(([kind, count]) => `${titleCase(kind)} ${count}`)
                .join(" · ")}
            </div>
          </div>
          <input
            className="form-input sast-semantic-search"
            type="search"
            placeholder="Filter facts"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <div className="table-wrap">
          <table className="sast-semantic-table">
            <thead>
              <tr>
                <th>Kind</th>
                <th>Fact</th>
                <th>Component</th>
                <th>Evidence</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {visibleNodes.map((node) => (
                <tr key={node.id || node.fingerprint}>
                  <td>{titleCase(node.kind)}</td>
                  <td>
                    <strong>{node.name || node.path || titleCase(node.type)}</strong>
                    <small>{titleCase(node.type)}</small>
                  </td>
                  <td>
                    <code>{node.component_key || "—"}</code>
                  </td>
                  <td>{asArray(node.evidence).join(", ") || "—"}</td>
                  <td>{percent(node.confidence)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {nodes.length > 250 && !query ? (
          <div className="sast-table-limit">
            Showing the first 250 of {nodes.length} facts. Use the filter to narrow the list.
          </div>
        ) : null}
      </section>
    </div>
  );
}

export function ThreatModelView({ threatModel, status }) {
  const model = asObject(threatModel);
  const scenarios = asArray(model.scenarios);
  const quality = asObject(model.quality);
  if (!model.summary && !scenarios.length)
    return <EmptySemanticState label="Threat model" status={status} />;
  const statuses = countBy(scenarios, "status");
  return (
    <div className="sast-semantic-layout">
      <section className="sast-panel">
        <div className="sast-panel-title">Threat analysis</div>
        <p className="sast-semantic-summary">{model.summary || "No summary recorded."}</p>
        <MetricCards
          values={[
            ["Scenarios", scenarios.length],
            ["High priority", scenarios.filter((item) => item.priority === "high").length],
            ["Resolved", statuses.resolved || 0],
            ["Open questions", asArray(model.open_questions).length],
            ["Source files reviewed", model.files_reviewed || 0],
            ["Model coverage", titleCase(quality.status || "unknown")],
          ]}
        />
        {asArray(quality.reasons).length ? (
          <div className="sast-semantic-warning">
            {asArray(quality.reasons).map((reason) => (
              <p key={reason}>{reason}</p>
            ))}
          </div>
        ) : null}
      </section>
      <div className="sast-semantic-two-column">
        <ChipList title="Assets" values={model.assets} />
        <ChipList title="Data stores" values={model.stores} />
        <ChipList title="Trust boundaries" values={model.trust_boundaries} />
        <ChipList title="Attacker capabilities" values={model.attacker_capabilities} />
        <ChipList title="Security objectives" values={model.security_objectives} />
        <ChipList title="Assumptions" values={model.assumptions} />
        <ChipList title="Open questions" values={model.open_questions} />
      </div>
      <section className="sast-panel">
        <div className="sast-panel-title">Threat scenarios</div>
        <div className="sast-semantic-card-list">
          {scenarios.map((scenario) => (
            <details key={scenario.scenario_key}>
              <summary>
                <span
                  className={`sast-state sast-state-${scenario.status === "resolved" ? "confirmed" : "inconclusive"}`}
                >
                  {titleCase(scenario.status)}
                </span>
                <strong>{scenario.title}</strong>
                <small>
                  {titleCase(scenario.priority)} priority · {percent(scenario.confidence)}
                </small>
              </summary>
              <dl className="sast-semantic-details">
                <dt>Actor</dt>
                <dd>{displayValue(scenario.actor)}</dd>
                <dt>Controlled input or state</dt>
                <dd>{displayValue(scenario.controlled_input_or_state)}</dd>
                <dt>Security objective</dt>
                <dd>{displayValue(scenario.security_objective)}</dd>
                <dt>Capability gain</dt>
                <dd>{displayValue(scenario.capability_gain)}</dd>
                <dt>Impact</dt>
                <dd>{displayValue(scenario.impact)}</dd>
                <dt>Evidence</dt>
                <dd>{asArray(scenario.evidence).join(", ") || "—"}</dd>
              </dl>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}

export function ObligationsView({ planning, closure, report, status }) {
  const plan = asObject(planning);
  const obligations = asArray(plan.obligations);
  const closureState = asObject(closure);
  if (!obligations.length && !closureState.status)
    return <EmptySemanticState label="Security check analysis" status={status} />;
  const statuses = countBy(obligations, "status");
  const unresolved = obligations.filter((item) =>
    ["pending", "in_review", "blocked", "unreviewed"].includes(item.status),
  );
  return (
    <div className="sast-semantic-layout">
      <MetricCards
        values={[
          ["Security checks", obligations.length, `${Object.keys(statuses).length} states`],
          ["Unresolved", unresolved.length],
          [
            "Closure",
            titleCase(closureState.status || "pending"),
            `${closureState.closure_candidates_created || 0} candidates recovered`,
          ],
          [
            "Reconciled candidates",
            asObject(report?.semantic?.reconciliation).unique || report?.candidates || 0,
          ],
        ]}
      />
      <section className="sast-panel">
        <div className="sast-panel-header">
          <div>
            <div className="sast-panel-title">Discovery and closure</div>
            <div className="sast-panel-sub">
              {report?.candidates || 0} candidates · {report?.reportable || 0} reportable ·{" "}
              {unresolved.length} unresolved security checks
            </div>
          </div>
          <span
            className={`sast-state sast-state-${closureState.status === "full" ? "confirmed" : "inconclusive"}`}
          >
            {closureState.status || "pending"}
          </span>
        </div>
        {report?.discovery_summary ? (
          <details className="sast-semantic-narrative">
            <summary>Show discovery summary</summary>
            <p>{report.discovery_summary}</p>
          </details>
        ) : null}
        {asArray(closureState.reasons).length ? (
          <ul className="sast-semantic-reasons">
            {closureState.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        ) : (
          <div className="subtle">No closure gaps recorded.</div>
        )}
      </section>
      <section className="sast-panel">
        <div className="sast-panel-title">Required security checks</div>
        <div className="sast-semantic-card-list">
          {obligations.map((item) => (
            <details key={item.obligation_key}>
              <summary>
                <span
                  className={`sast-state sast-state-${["candidate", "assessed_safe", "not_applicable"].includes(item.status) ? "confirmed" : "inconclusive"}`}
                >
                  {titleCase(item.status)}
                </span>
                <strong>{item.title || item.security_question}</strong>
                <small>
                  {titleCase(item.obligation_type)} · {titleCase(item.priority)} priority
                </small>
              </summary>
              <dl className="sast-semantic-details">
                <dt>Security question</dt>
                <dd>{item.security_question || "—"}</dd>
                <dt>Disposition</dt>
                <dd>{item.disposition || "—"}</dd>
                <dt>Reasoning</dt>
                <dd>{item.reasoning || "—"}</dd>
                <dt>Evidence</dt>
                <dd>{asArray(item.evidence).join(", ") || "—"}</dd>
                <dt>Open questions</dt>
                <dd>{asArray(item.open_questions).join("; ") || "—"}</dd>
              </dl>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}

function efficiencyEmptyState(status) {
  if (status === "running" || status === "scanning") {
    return {
      label: "Efficiency telemetry is being collected.",
      message: "This analysis will appear after the scan finishes and the final report is ready.",
    };
  }
  if (status === "pending") {
    return {
      label: "Efficiency telemetry has not been collected yet.",
      message: "Start the SAST scan to generate this analysis.",
    };
  }
  if (status === "paused") {
    return {
      label: "Efficiency telemetry is waiting for the scan to finish.",
      message: "Resume the scan to continue collecting this analysis.",
    };
  }
  if (status === "failed" || status === "cancelled") {
    return {
      label: "Efficiency telemetry was not generated.",
      message: "The scan ended before the final report was ready.",
    };
  }
  return {
    label: "Efficiency telemetry is not available for this run.",
    message: "Run the scan again with the current SAST workflow to generate this analysis.",
  };
}

function formatDuration(milliseconds) {
  const seconds = Math.max(0, Number(milliseconds || 0)) / 1000;
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 2 : 1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

function readSummary(row) {
  const files = Number(row.files_read || 0);
  const spans = Number(row.unique_spans_read || 0);
  if (!files && !spans) return null;
  return `${files} ${files === 1 ? "file" : "files"}, ${spans} ${spans === 1 ? "span" : "spans"}`;
}

function phaseWork(row) {
  const reads = readSummary(row);
  switch (row.phase) {
    case "scope":
      return ["Archive extracted and source inventory built"];
    case "repository_model":
      return [
        Number(row.facts_created || 0)
          ? `${row.facts_created} repository facts recorded`
          : "Repository model built",
      ];
    case "threat_model":
      return [reads, "Threat model built"].filter(Boolean);
    case "planning":
      return [`${row.obligations_created || 0} security checks planned`];
    case "discovery":
      return [reads, `${row.candidates_emitted || 0} candidates found`].filter(Boolean);
    case "reconciliation": {
      const merged = Number(row.candidates_merged || 0);
      const split = Number(row.candidates_split || 0);
      return merged || split
        ? [`${merged} merged`, `${split} split`]
        : ["No duplicate candidates needed changes"];
    }
    case "validation": {
      const confirmed = Number(row.candidates_confirmed || 0);
      const dismissed = Number(row.candidates_dismissed || 0);
      return [
        reads,
        confirmed || dismissed
          ? `${confirmed} confirmed, ${dismissed} dismissed`
          : "No candidates required a decision",
      ].filter(Boolean);
    }
    case "closure":
      return [
        reads,
        Number(row.adjacent_concerns || 0)
          ? `${row.adjacent_concerns} adjacent concerns reviewed`
          : "Coverage gaps reviewed",
      ].filter(Boolean);
    case "attack_path":
      return [reads, "Reportable candidates checked for reachability"].filter(Boolean);
    case "report":
      return ["Final candidate and coverage report assembled"];
    default:
      return [reads || "Phase completed"];
  }
}

function buildPhaseTimeline(rows, phaseState) {
  const intervals = rows
    .map((row) => {
      const state = asObject(phaseState?.[row.phase]);
      const start = Date.parse(state.first_started_at || state.started_at || "");
      const end = Date.parse(state.completed_at || "");
      if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return null;
      const activeIntervals = asArray(state.active_intervals)
        .map((interval) => ({
          start: Date.parse(interval?.started_at || ""),
          end: Date.parse(interval?.ended_at || ""),
        }))
        .filter(
          (interval) =>
            Number.isFinite(interval.start) &&
            Number.isFinite(interval.end) &&
            interval.end >= interval.start,
        );
      return {
        phase: row.phase,
        start,
        end,
        activeIntervals: activeIntervals.length ? activeIntervals : [{ start, end }],
      };
    })
    .filter(Boolean);
  if (!intervals.length) return new Map();
  const runStart = Math.min(...intervals.map((interval) => interval.start));
  const runEnd = Math.max(...intervals.map((interval) => interval.end));
  const runSpan = Math.max(1, runEnd - runStart);
  return new Map(
    intervals.map((interval) => {
      const segments = interval.activeIntervals.map((segment) => {
        const left = ((segment.start - runStart) / runSpan) * 100;
        const exactWidth = ((segment.end - segment.start) / runSpan) * 100;
        return {
          left,
          width: Math.max(1.5, Math.min(100 - left, exactWidth)),
        };
      });
      return [interval.phase, { segments, elapsed: interval.end - interval.start }];
    }),
  );
}

export function EfficiencyView({ telemetry, report, status, phaseState = {} }) {
  const rows = asArray(telemetry);
  if (!rows.length) {
    const emptyState = efficiencyEmptyState(status);
    return (
      <div className="sast-semantic-empty">
        <strong>{emptyState.label}</strong>
        <span>{emptyState.message}</span>
      </div>
    );
  }
  const totals = rows.reduce(
    (result, row) => {
      result.elapsed_ms += Number(row.elapsed_ms || 0);
      result.files_read += Number(row.files_read || 0);
      result.unique_spans_read += Number(row.unique_spans_read || 0);
      result.candidates_emitted += Number(row.candidates_emitted || 0);
      return result;
    },
    { elapsed_ms: 0, files_read: 0, unique_spans_read: 0, candidates_emitted: 0 },
  );
  const timeline = buildPhaseTimeline(rows, phaseState);
  const hasPauseAwareTiming = rows.every((row) => {
    const state = asObject(phaseState?.[row.phase]);
    return (
      Object.prototype.hasOwnProperty.call(state, "active_elapsed_ms") &&
      Array.isArray(state.active_intervals)
    );
  });
  return (
    <div className="sast-semantic-layout">
      <MetricCards
        values={[
          [
            hasPauseAwareTiming ? "Recorded active time" : "Recorded phase time",
            formatDuration(totals.elapsed_ms),
            hasPauseAwareTiming
              ? "Phases can overlap; paused time is excluded"
              : "Saved before pause-aware timing; pauses may be included",
          ],
          ["Files reviewed", totals.files_read, "Counted once in each phase"],
          ["Source spans reviewed", totals.unique_spans_read, "Counted once in each phase"],
          ["Candidates found", totals.candidates_emitted, `${report?.reportable || 0} reportable`],
        ]}
      />
      <section className="sast-panel">
        <div className="sast-panel-title">Phase activity</div>
        <div className="table-wrap">
          <table className="sast-semantic-table sast-efficiency-table">
            <colgroup>
              <col className="sast-phase-column" />
              <col className="sast-active-time-column" />
              <col className="sast-run-timeline-column" />
              <col className="sast-work-completed-column" />
            </colgroup>
            <thead>
              <tr>
                <th>Phase</th>
                <th>{hasPauseAwareTiming ? "Active time" : "Recorded time"}</th>
                <th>
                  <span className="sast-timeline-heading">
                    Run timeline
                    <small>
                      {hasPauseAwareTiming ? "gaps show pauses" : "pause gaps unavailable"}
                    </small>
                  </span>
                </th>
                <th>Work completed</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => {
                let caps = [];
                try {
                  caps = JSON.parse(row.caps_json || "[]");
                } catch {}
                const work = [
                  ...phaseWork(row),
                  ...(row.strategy ? [`Strategy: ${titleCase(row.strategy)}`] : []),
                  ...asArray(caps).map((cap) => `Limit: ${cap}`),
                ];
                const timing = timeline.get(row.phase);
                return (
                  <tr key={`${row.phase}-${row.strategy}-${index}`}>
                    <td>
                      <strong>{titleCase(row.phase)}</strong>
                    </td>
                    <td>{formatDuration(row.elapsed_ms)}</td>
                    <td className="sast-timeline-cell">
                      {timing ? (
                        <div
                          className="sast-phase-timeline"
                          role="img"
                          aria-label={`${titleCase(row.phase)} spanned ${formatDuration(timing.elapsed)} on the recorded run timeline`}
                          title={`${titleCase(row.phase)}: ${formatDuration(timing.elapsed)} from start to finish`}
                        >
                          {timing.segments.map((segment, segmentIndex) => (
                            <span
                              key={segmentIndex}
                              style={{
                                "--timeline-left": `${segment.left}%`,
                                "--timeline-width": `${segment.width}%`,
                              }}
                            />
                          ))}
                        </div>
                      ) : (
                        <span className="sast-timeline-unavailable">Timing unavailable</span>
                      )}
                    </td>
                    <td>
                      <div className="sast-phase-work">
                        {work.map((item) => (
                          <span key={item}>{item}</span>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
