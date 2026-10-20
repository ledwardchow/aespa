import { fmtDate } from "../../shared/lib/dates.js";
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
  const [query, setQuery] = useState("");
  const [applicationId, setApplicationId] = useState("");
  const [statusFilter, setStatusFilter] = useState("pending");
  const [sort, setSort] = useState("newest");
  const [setupOpen, setSetupOpen] = useState(false);
  const showApplication = category !== "sast";
  const label = category === "site" ? "Sites" : category === "api" ? "API" : "SAST";
  const runs = (
    category === "sast"
      ? targets.sast_runs.map((run) => ({ ...run, targetName: "Source scan" }))
      : targets[category === "site" ? "sites" : "apis"].flatMap((target) =>
          target.runs.map((run) => ({ ...run, targetId: target.id, targetName: target.name })),
        )
  )
    .filter((run) =>
      (category === "sast"
        ? ["completed"]
        : ["complete", "completed", "incomplete", "stopped"]
      ).includes(run.status),
    )
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
  const visibleRuns = runs
    .filter((run) =>
      `${run.name} ${run.targetName} ${scanModelLabel(category, run.result?.scan_models || run.scan_models)}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
    )
    .filter((run) => !showApplication || !applicationId || String(run.targetId) === applicationId)
    .filter((run) =>
      statusFilter === "all"
        ? true
        : statusFilter === "pending"
          ? !run.result && !run.evaluation
          : !!run.result || !!run.evaluation,
    )
    .sort((left, right) => {
      const order =
        new Date(right.completed_at || 0) - new Date(left.completed_at || 0) || right.id - left.id;
      return sort === "oldest" ? -order : order;
    });
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
      setSetupOpen(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className={styles.section} aria-label={`${label} finished scans`}>
      <h2>{category === "site" ? "DAST scans" : `${label} scans`}</h2>
      <p className="subtle">
        {runs.length} finished scans · {pending.length} need a benchmark. The selected ground truth
        applies to the selected scans.
      </p>
      <div
        className={`${styles.filters} ${!showApplication ? styles.filtersWithoutApplication : ""}`}
      >
        <label>
          Search scans
          <input
            className="input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={showApplication ? "Scan, application, or model" : "Scan or model"}
          />
        </label>
        {showApplication && (
          <label>
            Application
            <select
              className="select"
              value={applicationId}
              onChange={(event) => setApplicationId(event.target.value)}
            >
              <option value="">All applications</option>
              {applications.map((application) => (
                <option key={application.id} value={application.id}>
                  {application.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Benchmark status
          <select
            className="select"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="pending">Needs benchmark</option>
            <option value="done">Benchmarked</option>
            <option value="all">All scans</option>
          </select>
        </label>
        <label>
          Sort
          <select className="select" value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </label>
      </div>
      {setupOpen && (
        <button
          className={styles.backdrop}
          type="button"
          aria-label="Close benchmark setup"
          onClick={() => setSetupOpen(false)}
        />
      )}
      {setupOpen && (
        <form className={`card ${styles.controls} ${styles.setup}`} onSubmit={apply}>
          <div className={styles.setupHeading}>
            <h3>Benchmark {selectedRuns.length} selected scans</h3>
            <button type="button" className="btn ghost sm" onClick={() => setSetupOpen(false)}>
              Close setup
            </button>
          </div>
          <label>
            Ground truth for bulk benchmarks
            <select
              className="select"
              aria-label="Ground truth for bulk benchmarks"
              value={datasetId}
              disabled={busy}
              onChange={(event) => setDatasetId(event.target.value)}
            >
              <option value="">Select a saved file…</option>
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
            {busy ? "Working…" : `Benchmark ${selectedRuns.length} selected scans`}
          </button>
          {!!selectedRuns.length && !datasetId && (
            <p className="subtle">Pick a ground truth file above to turn this on.</p>
          )}
        </form>
      )}
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
        <p className="subtle">No finished scans in this category.</p>
      ) : !visibleRuns.length ? (
        <p className="subtle">No scans match these filters.</p>
      ) : (
        <div className="table-wrap">
          <label className={styles.mobileSelectAll}>
            <ScanSelection
              ids={visibleRuns.filter((run) => !run.result && !run.evaluation).map((run) => run.id)}
              selectedIds={selectedIds}
              onToggle={toggle}
              disabled={busy}
              label="Select all visible scans"
            />{" "}
            Select all visible scans
          </label>
          <table className={`${styles.table} ${styles.scanTable}`}>
            <thead>
              <tr>
                <th scope="col">
                  <ScanSelection
                    ids={visibleRuns
                      .filter((run) => !run.result && !run.evaluation)
                      .map((run) => run.id)}
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
                <th>Finished</th>
                <th>Benchmark</th>
              </tr>
            </thead>
            <tbody>
              {visibleRuns.map((run) => (
                <tr key={run.id}>
                  <td data-label="Select">
                    <ScanSelection
                      ids={run.result || run.evaluation ? [] : [run.id]}
                      selectedIds={selectedIds}
                      onToggle={toggle}
                      disabled={busy}
                      label={`Select ${run.name}`}
                    />
                  </td>
                  <td data-label="Scan">
                    <a
                      href={runHref({
                        runKind: category === "site" ? "web" : category,
                        runId: run.id,
                      })}
                    >
                      {run.name}
                    </a>
                  </td>
                  <td data-label="Type">
                    {scanType(category, run.scan_models || run.result?.scan_models)}
                  </td>
                  <td data-label="Scan model">
                    {scanModelLabel(category, run.result?.scan_models || run.scan_models)}
                  </td>
                  <td data-label="Target">{run.targetName}</td>
                  <td data-label="Finished">
                    {run.completed_at ? fmtDate(run.completed_at) : "—"}
                  </td>
                  <td data-label="Benchmark">
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
      {selectedRuns.length > 0 && (
        <div className={styles.selectionBar}>
          <span>{selectedRuns.length} scans selected</span>
          <button
            className="btn ghost sm"
            type="button"
            onClick={() => {
              setSelectedIds(new Set());
              setSetupOpen(false);
            }}
          >
            Clear selection
          </button>
          <button
            className="btn primary"
            type="button"
            disabled={!selectedRuns.length || busy}
            onClick={() => setSetupOpen(true)}
          >
            Benchmark selected
          </button>
        </div>
      )}
    </section>
  );
}
