import { useCallback, useEffect, useState } from "react";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import { EmptyState } from "../../shared/ui/EmptyState.jsx";
import { PageHeader } from "../../shared/ui/PageHeader.jsx";
import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";
import { nav } from "../../shared/navigation/router.js";

function asArray(value) {
  if (Array.isArray(value)) return value;
  return value?.items || value?.evaluations || value?.data || [];
}

function asObject(value) {
  if (value && typeof value === "object") return value;
  try {
    return JSON.parse(value || "{}");
  } catch {
    return {};
  }
}

export function BenchmarkLabPage() {
  const [evaluations, setEvaluations] = useState(null);
  const [error, setError] = useState(null);
  const load = useCallback(async () => {
    try {
      setEvaluations(asArray(await benchmarkApi.listBenchmarkEvaluations()));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  return (
    <>
      <PageHeader
        title="Benchmark Lab"
        actions={
          <button className="btn primary sm" onClick={() => nav("#/benchmark-lab/evaluations/new")}>
            New Evaluation
          </button>
        }
      />
      <div className="content scroll-content benchmark-page">
        {error && <div className="alert error">{error}</div>}
        {evaluations === null && !error && <div className="subtle">Loading…</div>}
        {evaluations?.length === 0 && (
          <EmptyState
            icon="◎"
            title="No evaluations"
            sub="Create an evaluation to get started."
          />
        )}
        {evaluations?.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Run</th>
                  <th>Status</th>
                  <th>Recall</th>
                  <th>Created</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {evaluations.map((evaluation) => {
                  const metrics = asObject(evaluation.metrics_json || evaluation.metrics);
                  const recall = metrics.full_recall ?? metrics.recall;
                  return (
                    <tr key={evaluation.id}>
                      <td>
                        <a
                          className="benchmark-name"
                          href={`#/benchmark-lab/evaluations/${evaluation.id}`}
                        >
                          {evaluation.name || `Evaluation #${evaluation.id}`}
                        </a>
                        <div className="subtle">{evaluation.match_mode || "assisted"} matching</div>
                      </td>
                      <td>
                        {evaluation.sast_run_id ? (
                          <a href={`#/sast-runs/${evaluation.sast_run_id}/coverage`}>
                            SAST run #{evaluation.sast_run_id}
                          </a>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>
                        <StatusBadge status={evaluation.status || "pending"} />
                      </td>
                      <td>
                        {recall === undefined
                          ? "—"
                          : `${Number(recall) <= 1 ? Math.round(Number(recall) * 100) : Math.round(Number(recall))}%`}
                      </td>
                      <td>
                        {evaluation.created_at
                          ? new Date(evaluation.created_at).toLocaleString()
                          : "—"}
                      </td>
                      <td>
                        <a
                          className="btn ghost sm"
                          href={`#/benchmark-lab/evaluations/${evaluation.id}`}
                        >
                          Open →
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
