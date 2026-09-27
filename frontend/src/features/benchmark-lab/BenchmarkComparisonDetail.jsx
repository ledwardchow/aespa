import { useCallback, useEffect, useMemo, useState } from "react";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import { Crumb, PageHeader, Sep } from "../../shared/ui/PageHeader.jsx";
import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";

const parseObject = (value) => {
  if (value && typeof value === "object") return value;
  try {
    return JSON.parse(value || "{}");
  } catch {
    return {};
  }
};

const percent = (value) => `${Math.round(Number(value || 0) * 100)}%`;

export function BenchmarkComparisonDetail({ comparisonId }) {
  const [comparison, setComparison] = useState(null);
  const [error, setError] = useState(null);
  const load = useCallback(async () => {
    try {
      setComparison(await benchmarkApi.getBenchmarkComparison(comparisonId));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, [comparisonId]);
  useEffect(() => {
    load();
  }, [load]);
  const metrics = useMemo(() => parseObject(comparison?.metrics_json), [comparison]);
  if (!comparison) return <div className="content scroll-content">{error || "Loading…"}</div>;
  const metricRows = [
    "full_recall",
    "inclusive_recall",
    "precision",
    "duplicate_rate",
    "runtime_seconds",
    "requests",
    "estimated_cost",
  ];
  return (
    <>
      <PageHeader
        title={
          <>
            <Crumb href="#/benchmark-lab">Benchmark Lab</Crumb>
            <Sep />
            {comparison.name}
          </>
        }
        actions={
          <button
            className="btn ghost sm"
            onClick={async () => {
              await benchmarkApi.recalculateBenchmarkComparison(comparisonId);
              await load();
            }}
          >
            Recalculate
          </button>
        }
      />
      <div className="content scroll-content benchmark-page">
        {error && <div className="alert error">{error}</div>}
        <div className="benchmark-meta">
          <StatusBadge status={comparison.status} />
          <span>{metrics.eligible_count || 0} eligible runs</span>
          <span>{metrics.excluded_count || 0} excluded</span>
        </div>
        {metrics.threshold_failures?.length > 0 && (
          <div className="alert error">{metrics.threshold_failures.join("; ")}</div>
        )}
        <section className="card">
          <h2>Median and range</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Median</th>
                  <th>Range</th>
                </tr>
              </thead>
              <tbody>
                {metricRows
                  .filter((key) => metrics[key])
                  .map((key) => (
                    <tr key={key}>
                      <td>{key.replaceAll("_", " ")}</td>
                      <td>
                        {key.includes("recall") || key.includes("precision") || key.includes("rate")
                          ? percent(metrics[key].median)
                          : metrics[key].median}
                      </td>
                      <td>
                        {metrics[key].min} – {metrics[key].max}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="card">
          <h2>Per-item detection frequency</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ground truth</th>
                  <th>Detected</th>
                  <th>Frequency</th>
                  <th>Full / partial / missed</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(metrics.detection_frequency || {}).map(([id, row]) => (
                  <tr key={id}>
                    <td>{id}</td>
                    <td>
                      {row.detected} / {row.runs}
                    </td>
                    <td>{percent(row.frequency)}</td>
                    <td>
                      {row.full} / {row.partial} / {row.missed}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </>
  );
}
