import { useState } from "react";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import { benchmarkUnbenchmarked } from "../../shared/api/benchmarkBulk.ts";
import { runHref } from "../../shared/navigation/links.ts";
import { parseGroundTruthText } from "./groundTruthImport.js";
import styles from "./CompletedScanBenchmarks.module.css";

export function CompletedScanBenchmarks({
  category,
  targets,
  results,
  legacy,
  datasets,
  models,
  onChange,
  onOpen,
}) {
  const [datasetId, setDatasetId] = useState("");
  const [modelId, setModelId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [outcome, setOutcome] = useState(null);
  const label = category === "site" ? "Sites" : category === "api" ? "API" : "SAST";
  const runs = (
    category === "sast"
      ? targets.sast_runs.map((run) => ({ ...run, targetName: "Source scan" }))
      : targets[category === "site" ? "sites" : "apis"].flatMap((target) =>
          target.runs.map((run) => ({ ...run, targetName: target.name })),
        )
  )
    .filter((run) => ["complete", "completed"].includes(run.status))
    .map((run) => ({
      ...run,
      result: results.find((result) => result.run_kind === category && result.run_id === run.id),
      evaluation:
        category === "sast"
          ? legacy.find(
              (evaluation) =>
                evaluation.sast_run_id === run.id && evaluation.status === "completed",
            )
          : null,
    }));
  const pending = runs.filter((run) => !run.result && !run.evaluation);
  const upload = async (file) => {
    if (!file) return;
    setBusy(true);
    setDatasetId("");
    setError(null);
    try {
      if (file.size > 10 * 1024 * 1024)
        throw new Error("Ground truth must be smaller than 10 MiB.");
      const parsed = parseGroundTruthText(await file.text(), file.name);
      const dataset = await benchmarkApi.createBenchmarkDataset({
        name: parsed.name || file.name,
        schema_version: parsed.schema_version || 1,
        source_digest: parsed.source_digest || null,
        ground_truth: parsed,
      });
      await onChange();
      setDatasetId(String(dataset.id));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  const apply = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setOutcome(null);
    try {
      const result = await benchmarkUnbenchmarked({
        run_kind: category,
        dataset_id: Number(datasetId),
        ...(modelId ? { evaluation_model_id: Number(modelId) } : {}),
      });
      setOutcome(result);
      await onChange();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className={styles.section} aria-label={`${label} completed scans`}>
      <h2>{label} completed scans</h2>
      <p className="subtle">
        {runs.length} completed scans · {pending.length} unbenchmarked. The selected ground truth
        applies to every unbenchmarked scan in this category.
      </p>
      <form className={`card ${styles.controls}`} onSubmit={apply}>
        <label>
          Ground truth for bulk benchmarks
          <select
            className="select"
            aria-label="Ground truth for bulk benchmarks"
            value={datasetId}
            disabled={busy}
            onChange={(event) => setDatasetId(event.target.value)}
          >
            <option value="">Select a saved file...</option>
            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name} ({dataset.item_count} findings)
              </option>
            ))}
          </select>
        </label>
        <label>
          Or upload a ground truth file
          <input
            type="file"
            aria-label="Bulk ground truth file"
            accept=".json,.md,.markdown"
            disabled={busy}
            onChange={(event) => {
              upload(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
        </label>
        <label>
          Bulk evaluation model
          <select
            className="select"
            aria-label="Bulk evaluation model"
            value={modelId}
            disabled={busy}
            onChange={(event) => setModelId(event.target.value)}
          >
            <option value="">Each scan's Test Lead model</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
        </label>
        <button className="btn primary" disabled={busy || !datasetId || !pending.length}>
          {busy ? "Working..." : `Benchmark ${pending.length} unbenchmarked scans`}
        </button>
      </form>
      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}
      {outcome && (
        <div role="status">
          Benchmarked {outcome.completed.length} scans. Skipped {outcome.skipped.length}. Failed{" "}
          {outcome.failures.length}.
          {outcome.failures.map((failure) => (
            <p key={failure.run_id}>
              Scan #{failure.run_id}: {failure.error}
            </p>
          ))}
        </div>
      )}
      {!runs.length ? (
        <p className="subtle">No completed scans in this category.</p>
      ) : (
        <div className="table-wrap">
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Scan</th>
                <th>Target</th>
                <th>Completed</th>
                <th>Benchmark</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>
                    <a
                      href={runHref({
                        runKind: category === "site" ? "web" : category,
                        runId: run.id,
                      })}
                    >
                      {run.name}
                    </a>
                  </td>
                  <td>{run.targetName}</td>
                  <td>{run.completed_at ? new Date(run.completed_at).toLocaleString() : "—"}</td>
                  <td>
                    {run.result ? (
                      <button
                        type="button"
                        className="btn ghost sm"
                        onClick={() => onOpen(run.result.id)}
                      >
                        Open benchmark for {run.name}
                      </button>
                    ) : run.evaluation ? (
                      <a href={`#/benchmark-lab/evaluations/${run.evaluation.id}`}>
                        Open benchmark
                      </a>
                    ) : (
                      "No benchmark"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
