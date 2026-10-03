import { scanType, scanModelLabel } from "./scanPresentation.js";
import { useState } from "react";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import { benchmarkUnbenchmarked } from "../../shared/api/benchmarkBulk.ts";
import { runHref } from "../../shared/navigation/links.ts";
import { parseGroundTruthText } from "./groundTruthImport.js";
import styles from "./CompletedScanBenchmarks.module.css";

function ScanSelection({ ids, selectedIds, onToggle, disabled, label }) {
  const count = ids.filter((id) => selectedIds.has(id)).length;
  return (
    <input
      type="checkbox"
      aria-label={label}
      checked={ids.length > 0 && count === ids.length}
      ref={(element) => {
        if (element) element.indeterminate = count > 0 && count < ids.length;
      }}
      disabled={disabled || !ids.length}
      onChange={(event) => onToggle(ids, event.target.checked)}
    />
  );
}

export function CompletedScanBenchmarks({
  category,
  targets,
  results,
  legacy,
  datasets,
  defaultModel,
  onChange,
  onOpen,
}) {
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [datasetId, setDatasetId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [outcome, setOutcome] = useState(null);
  const label = category === "site" ? "Sites" : category === "api" ? "API" : "SAST";
  const runs = (
    category === "sast"
      ? targets.sast_runs.map((run) => ({ ...run, targetName: "Source scan" }))
      : targets[category === "site" ? "sites" : "apis"].flatMap((target) =>
          target.runs.map((run) => ({ ...run, targetId: target.id, targetName: target.name })),
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
  const selectedRuns = pending.filter((run) => selectedIds.has(run.id));
  const applications = category === "sast" ? [] : targets[category === "site" ? "sites" : "apis"];
  const toggle = (ids, checked) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      ids.forEach((id) => (checked ? next.add(id) : next.delete(id)));
      return next;
    });
  };
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
    if (busy || !defaultModel || !datasetId || !selectedRuns.length) return;
    setBusy(true);
    setError(null);
    setOutcome(null);
    try {
      const result = await benchmarkUnbenchmarked({
        run_kind: category,
        run_ids: selectedRuns.map((run) => run.id),
        dataset_id: Number(datasetId),
      });
      setOutcome(result);
      toggle([...result.completed, ...result.skipped], false);
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
        applies to the selected scans.
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
                {dataset.label ? `${dataset.label} (${dataset.name})` : dataset.name} (
                {dataset.item_count} findings)
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
        <p className="subtle">
          {defaultModel
            ? `Benchmark model: ${defaultModel.name}`
            : "Choose a default benchmark model in Settings first."}
        </p>
        <button
          className="btn primary"
          disabled={busy || !defaultModel || !datasetId || !selectedRuns.length}
        >
          {busy ? "Working..." : `Benchmark ${selectedRuns.length} selected scans`}
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
      {applications.length > 0 && (
        <fieldset className={styles.applications}>
          <legend>Select by application</legend>
          {applications.map((application) => (
            <label key={application.id}>
              <ScanSelection
                ids={pending.filter((run) => run.targetId === application.id).map((run) => run.id)}
                selectedIds={selectedIds}
                onToggle={toggle}
                disabled={busy}
                label={`Select all scans from ${application.name}`}
              />
              {application.name}
            </label>
          ))}
        </fieldset>
      )}
      {!runs.length ? (
        <p className="subtle">No completed scans in this category.</p>
      ) : (
        <div className="table-wrap">
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">
                  <ScanSelection
                    ids={pending.map((run) => run.id)}
                    selectedIds={selectedIds}
                    onToggle={toggle}
                    disabled={busy}
                    label="Select all unbenchmarked scans"
                  />
                </th>
                <th>Scan</th>
                <th>Type</th>
                <th>Scan model</th>
                <th>Target</th>
                <th>Completed</th>
                <th>Benchmark</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>
                    <ScanSelection
                      ids={run.result || run.evaluation ? [] : [run.id]}
                      selectedIds={selectedIds}
                      onToggle={toggle}
                      disabled={busy}
                      label={`Select ${run.name}`}
                    />
                  </td>
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
                  <td>{scanType(category, run.scan_models || run.result?.scan_models)}</td>
                  <td>{scanModelLabel(category, run.result?.scan_models || run.scan_models)}</td>
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
