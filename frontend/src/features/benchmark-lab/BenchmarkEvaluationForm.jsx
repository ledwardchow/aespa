import { useEffect, useMemo, useState } from "react";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import * as sastApi from "../../shared/api/sastRuns.js";
import { nav } from "../../shared/navigation/router.js";
import { PageHeader, Crumb, Sep } from "../../shared/ui/PageHeader.jsx";
import { parseGroundTruthText } from "./groundTruthImport.js";

const TERMINAL = new Set(["completed"]);
const asArray = (value, key) =>
  Array.isArray(value) ? value : value?.[key] || value?.items || value?.data || [];

export function BenchmarkEvaluationForm() {
  const [runs, setRuns] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [runId, setRunId] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [runDetails, setRunDetails] = useState(null);
  const [datasetFile, setDatasetFile] = useState(null);
  const [datasetName, setDatasetName] = useState("");
  const [parsedDataset, setParsedDataset] = useState(null);
  const [form, setForm] = useState({
    name: "",
    notes: "",
    match_mode: "assisted",
    severity_tolerance: "same_or_higher",
    location_tolerance: "file_and_line",
    include_conditional: true,
    include_hardening: false,
  });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  useEffect(() => {
    Promise.all([sastApi.listAllSastRuns(), benchmarkApi.listBenchmarkDatasets()])
      .then(([runResult, datasetResult]) => {
        setRuns(asArray(runResult, "runs").filter((run) => TERMINAL.has(run.status)));
        setDatasets(asArray(datasetResult, "datasets"));
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);
  const selectedRun = useMemo(
    () => runDetails || runs.find((run) => String(run.id) === String(runId)),
    [runDetails, runs, runId],
  );
  const chooseRun = async (value) => {
    setRunId(value);
    setRunDetails(null);
    if (!value) return;
    try {
      setRunDetails(await sastApi.getSastRun(value));
    } catch (err) {
      setError(err.message);
    }
  };
  const readDataset = async (file) => {
    setDatasetFile(file);
    setParsedDataset(null);
    setError(null);
    if (!file) return;
    try {
      const parsed = parseGroundTruthText(await file.text(), file.name);
      setParsedDataset(parsed);
      setDatasetName(parsed.name || file.name.replace(/\.(?:json|md|markdown)$/i, ""));
    } catch (err) {
      setError(err.message);
    }
  };
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      let selectedDatasetId = datasetId;
      if (datasetFile) {
        if (!parsedDataset) throw new Error("The uploaded ground truth could not be parsed.");
        const parsed = parsedDataset;
        const created = await benchmarkApi.createBenchmarkDataset({
          name: datasetName || parsed.name || datasetFile.name,
          schema_version: parsed.schema_version || 1,
          source_digest: parsed.source_digest || null,
          ground_truth: parsed,
        });
        selectedDatasetId = created.id;
      }
      if (!runId || !selectedDatasetId)
        throw new Error("Choose a completed SAST run and a ground-truth dataset.");
      const {
        severity_tolerance,
        location_tolerance,
        include_conditional,
        include_hardening,
        ...evaluationForm
      } = form;
      const created = await benchmarkApi.createBenchmarkEvaluation({
        ...evaluationForm,
        sast_run_id: Number(runId),
        dataset_id: Number(selectedDatasetId),
        policy: { severity_tolerance, location_tolerance, include_conditional, include_hardening },
      });
      nav(`#/benchmark-lab/evaluations/${created.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageHeader
        title={
          <>
            <Crumb href="#/benchmark-lab">Benchmark Lab</Crumb>
            <Sep />
            New Evaluation
          </>
        }
      />
      <div className="content scroll-content benchmark-page">
        <form className="benchmark-form" onSubmit={submit}>
          <section className="card">
            <h2>Evaluation setup</h2>
            <p className="field-hint">
              Only terminal ordinary SAST runs can be evaluated. Ground truth is stored separately
              from source snapshots and scanner artifacts.
            </p>
            {error && <div className="alert error">{error}</div>}
            {loading ? (
              <div className="subtle">Loading runs and datasets…</div>
            ) : (
              <>
                <label className="form-label">
                  Completed SAST run
                  <select
                    className="form-input"
                    value={runId}
                    onChange={(event) => chooseRun(event.target.value)}
                  >
                    <option value="">Select a run…</option>
                    {runs.map((run) => (
                      <option value={run.id} key={run.id}>
                        {run.name || `Run #${run.id}`} — {run.status}
                      </option>
                    ))}
                  </select>
                </label>
                {selectedRun && (
                  <div className="benchmark-provenance-card">
                    <strong>Run provenance</strong>
                    <span>
                      {selectedRun.source_archive_digest ||
                        selectedRun.source_digest ||
                        "Source digest unavailable"}
                    </span>
                    <span>
                      {selectedRun.started_at
                        ? new Date(selectedRun.started_at).toLocaleString()
                        : "Start time unavailable"}{" "}
                      →{" "}
                      {selectedRun.completed_at
                        ? new Date(selectedRun.completed_at).toLocaleString()
                        : "Completion time unavailable"}
                    </span>
                  </div>
                )}
                <label className="form-label">
                  Saved ground-truth dataset
                  <select
                    className="form-input"
                    value={datasetId}
                    onChange={(event) => {
                      setDatasetId(event.target.value);
                      setDatasetFile(null);
                      setParsedDataset(null);
                    }}
                  >
                    <option value="">Select a dataset…</option>
                    {datasets.map((dataset) => (
                      <option value={dataset.id} key={dataset.id}>
                        {dataset.name || `Dataset #${dataset.id}`} ({dataset.schema_version || 1})
                      </option>
                    ))}
                  </select>
                </label>
                <div className="benchmark-upload">
                  <span className="field-hint">
                    Upload canonical JSON or numbered vulnerability Markdown.
                  </span>
                  <input
                    type="file"
                    accept=".json,.md,.markdown,application/json,text/markdown,text/plain"
                    onChange={(event) => readDataset(event.target.files?.[0])}
                  />
                  {datasetFile && (
                    <>
                      {parsedDataset && (
                        <div className="field-hint">
                          Parsed {parsedDataset.items.length}{" "}
                          {parsedDataset.items.length === 1 ? "vulnerability" : "vulnerabilities"}.
                        </div>
                      )}
                      <label className="form-label">
                        Dataset name
                        <input
                          className="form-input"
                          value={datasetName}
                          onChange={(event) => setDatasetName(event.target.value)}
                        />
                      </label>
                    </>
                  )}
                </div>
              </>
            )}
          </section>
          <section className="card">
            <h2>Matching policy</h2>
            <div className="form-grid two">
              <label className="form-label">
                Evaluation name
                <input
                  className="form-input"
                  value={form.name}
                  required
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                />
              </label>
              <label className="form-label">
                Match mode
                <select
                  className="form-input"
                  value={form.match_mode}
                  onChange={(event) => setForm({ ...form, match_mode: event.target.value })}
                >
                  <option value="deterministic">Deterministic only</option>
                  <option value="assisted">Assisted</option>
                  <option value="human_reviewed">Human reviewed</option>
                </select>
              </label>
              <label className="form-label">
                Severity tolerance
                <select
                  className="form-input"
                  value={form.severity_tolerance}
                  onChange={(event) => setForm({ ...form, severity_tolerance: event.target.value })}
                >
                  <option value="same_or_higher">Same or higher</option>
                  <option value="exact">Exact</option>
                </select>
              </label>
              <label className="form-label">
                Location tolerance
                <select
                  className="form-input"
                  value={form.location_tolerance}
                  onChange={(event) => setForm({ ...form, location_tolerance: event.target.value })}
                >
                  <option value="file_and_line">File and line</option>
                  <option value="file">File</option>
                  <option value="operation">Operation</option>
                </select>
              </label>
            </div>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={form.include_conditional}
                onChange={(event) =>
                  setForm({ ...form, include_conditional: event.target.checked })
                }
              />{" "}
              Include conditional items
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={form.include_hardening}
                onChange={(event) => setForm({ ...form, include_hardening: event.target.checked })}
              />{" "}
              Include hardening items
            </label>
            <label className="form-label" style={{ marginTop: 12 }}>
              Notes
              <textarea
                className="form-input"
                rows={3}
                value={form.notes}
                onChange={(event) => setForm({ ...form, notes: event.target.value })}
              />
            </label>
            <div className="form-actions">
              <button type="button" className="btn ghost" onClick={() => nav("#/benchmark-lab")}>
                Cancel
              </button>
              <button className="btn primary" disabled={busy || loading}>
                {busy ? "Creating…" : "Create evaluation"}
              </button>
            </div>
          </section>
        </form>
      </div>
    </>
  );
}
