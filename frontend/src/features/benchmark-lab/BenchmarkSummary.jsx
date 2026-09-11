function metricValue(metrics, ...keys) {
  for (const key of keys) {
    if (metrics?.[key] !== undefined && metrics?.[key] !== null) return metrics[key];
  }
  return "—";
}

function metricObject(value) {
  if (value && typeof value === "object") return value;
  try {
    return JSON.parse(value || "{}");
  } catch {
    return {};
  }
}

function percent(value) {
  if (value === "—") return value;
  const number = Number(value);
  if (!Number.isFinite(number)) return value;
  return `${number <= 1 ? Math.round(number * 100) : Math.round(number)}%`;
}

export function BenchmarkSummary({ evaluation }) {
  const metrics = metricObject(evaluation?.metrics_json || evaluation?.metrics);
  const cards = [
    [
      "Full recall",
      percent(metricValue(metrics, "full_recall", "recall")),
      "Expected items found fully",
    ],
    [
      "Inclusive recall",
      percent(metricValue(metrics, "inclusive_recall")),
      "Full + partial detections",
    ],
    ["Precision", percent(metricValue(metrics, "precision")), "Adjudicated reportable findings"],
    [
      "Duplicate rate",
      percent(metricValue(metrics, "duplicate_rate")),
      "Consolidated duplicate leads",
    ],
    [
      "Unique root causes",
      metricValue(metrics, "unique_validated_root_causes", "unique_root_causes"),
      "After reconciliation",
    ],
    [
      "Partial / unresolved",
      `${metricValue(metrics, "partial_count", "partial")} / ${metricValue(metrics, "unresolved_count", "unresolved")}`,
      "Needs review",
    ],
    [
      "Runtime",
      metricValue(metrics, "runtime_seconds", "elapsed_seconds") === "—"
        ? "—"
        : `${metricValue(metrics, "runtime_seconds", "elapsed_seconds")}s`,
      "Evaluation telemetry",
    ],
    ["Requests", metricValue(metrics, "requests", "llm_requests"), "Evaluator requests"],
  ];
  return (
    <div className="benchmark-summary-grid">
      {cards.map(([label, value, hint]) => (
        <div className="benchmark-stat" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
          <small>{hint}</small>
        </div>
      ))}
    </div>
  );
}

export function BenchmarkMetricTable({ metrics }) {
  const entries = Object.entries(metrics || {}).filter(([, value]) => typeof value !== "object");
  if (!entries.length) return <div className="subtle">No efficiency metrics recorded yet.</div>;
  return (
    <div className="table-wrap">
      <table className="benchmark-metric-table">
        <tbody>
          {entries.map(([key, value]) => (
            <tr key={key}>
              <th>{key.replaceAll("_", " ")}</th>
              <td>{String(value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
