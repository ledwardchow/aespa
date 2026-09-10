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
  const [comparisons, setComparisons] = useState([]);
  const [showComparisonForm, setShowComparisonForm] = useState(false);
  const [comparisonName, setComparisonName] = useState("");
  const [selectedEvaluations, setSelectedEvaluations] = useState([]);
  const [minRecall, setMinRecall] = useState("");
  const [maxDuplicateRate, setMaxDuplicateRate] = useState("");
  const load = useCallback(async () => {
    try {
      const [evaluationRows, comparisonRows] = await Promise.all([
        benchmarkApi.listBenchmarkEvaluations(),
        benchmarkApi.listBenchmarkComparisons(),
      ]);
      setEvaluations(asArray(evaluationRows));
      setComparisons(asArray(comparisonRows));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  const createComparison = async (event) => {
    event.preventDefault();
    const chosen = evaluations.filter((evaluation) => selectedEvaluations.includes(evaluation.id));
    if (
      chosen.length < 2 ||
      new Set(chosen.map((evaluation) => evaluation.dataset_id)).size !== 1
    ) {
      setError("Select at least two completed evaluations that use the same dataset.");
      return;
    }
    try {
      const created = await benchmarkApi.createBenchmarkComparison({
        name: comparisonName,
        dataset_id: chosen[0].dataset_id,
        evaluation_ids: chosen.map((evaluation) => evaluation.id),
        thresholds: {
          ...(minRecall === "" ? {} : { inclusive_recall: { min: Number(minRecall) } }),
          ...(maxDuplicateRate === "" ? {} : { duplicate_rate: { max: Number(maxDuplicateRate) } }),
        },
        include_contaminated: false,
      });
      nav(`#/benchmark-lab/comparisons/${created.id}`);
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <>
      <PageHeader
        title="Benchmark Lab"
        actions={
          <>
            <button
              className="btn ghost sm"
              onClick={() => setShowComparisonForm((value) => !value)}
            >
              New Comparison
            </button>
            <button
              className="btn primary sm"
              onClick={() => nav("#/benchmark-lab/evaluations/new")}
            >
              New Evaluation
            </button>
          </>
        }
      />
      <div className="content scroll-content benchmark-page">
        {error && <div className="alert error">{error}</div>}
        {showComparisonForm && (
          <form className="card benchmark-comparison-form" onSubmit={createComparison}>
            <h2>Compare repeated runs</h2>
            <label>
              Name
              <input
                value={comparisonName}
                onChange={(event) => setComparisonName(event.target.value)}
                required
              />
            </label>
            <div className="benchmark-evaluation-picker">
              {evaluations
                ?.filter((evaluation) => evaluation.status === "completed")
                .map((evaluation) => (
                  <label key={evaluation.id}>
                    <input
                      type="checkbox"
                      checked={selectedEvaluations.includes(evaluation.id)}
                      onChange={(event) =>
                        setSelectedEvaluations((current) =>
                          event.target.checked
                            ? [...current, evaluation.id]
                            : current.filter((id) => id !== evaluation.id),
                        )
                      }
                    />
                    {evaluation.name} · dataset #{evaluation.dataset_id}
                  </label>
                ))}
            </div>
            <div className="form-grid two-col">
              <label>
                Minimum inclusive recall (0–1)
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  value={minRecall}
                  onChange={(event) => setMinRecall(event.target.value)}
                />
              </label>
              <label>
                Maximum duplicate rate (0–1)
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  value={maxDuplicateRate}
                  onChange={(event) => setMaxDuplicateRate(event.target.value)}
                />
              </label>
            </div>
            <button className="btn primary sm" type="submit">
              Create comparison
            </button>
          </form>
        )}
        {comparisons.length > 0 && (
          <section className="benchmark-comparisons">
            <h2>Comparisons</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Runs</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {comparisons.map((comparison) => {
                    const metrics = asObject(comparison.metrics_json);
                    return (
                      <tr key={comparison.id}>
                        <td>{comparison.name}</td>
                        <td>{metrics.eligible_count ?? comparison.evaluation_ids?.length ?? 0}</td>
                        <td>
                          <StatusBadge status={comparison.status} />
                        </td>
                        <td>
                          <a
                            className="btn ghost sm"
                            href={`#/benchmark-lab/comparisons/${comparison.id}`}
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
          </section>
        )}
        {evaluations === null && !error && <div className="subtle">Loading…</div>}
        {evaluations?.length === 0 && (
          <EmptyState icon="◎" title="No evaluations" sub="Create an evaluation to get started." />
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
