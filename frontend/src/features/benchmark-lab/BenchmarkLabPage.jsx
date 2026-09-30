import { useCallback, useEffect, useMemo, useState } from "react";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import * as settingsApi from "../../shared/api/settings.js";
import { PageHeader } from "../../shared/ui/PageHeader.jsx";
import { parseGroundTruthText } from "./groundTruthImport.js";
import { CompletedScanBenchmarks } from "./CompletedScanBenchmarks.jsx";
import { SiteSummary, modelName, money } from "./SiteSummary.jsx";

const EMPTY = { sites: [], apis: [], sast_runs: [] };
const modelLabel = (model) => {
  if (!model) return "Unavailable";
  if (model.name && model.model && model.name !== model.model)
    return `${model.name} (${model.model})`;
  return model.model || model.name || "Unavailable";
};

export function BenchmarkLabPage() {
  const [tab, setTab] = useState("site");
  const [siteTab, setSiteTab] = useState("summary");
  const [targets, setTargets] = useState(EMPTY);
  const [datasets, setDatasets] = useState([]);
  const [results, setResults] = useState([]);
  const [legacy, setLegacy] = useState([]);
  const [models, setModels] = useState([]);
  const [targetId, setTargetId] = useState("");
  const [runId, setRunId] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [uploadedDatasetId, setUploadedDatasetId] = useState(null);
  const [evaluationModel, setEvaluationModel] = useState("");
  const [selectedResultId, setSelectedResultId] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [edit, setEdit] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [targetData, datasetData, resultData, oldData, modelData] = await Promise.all([
        benchmarkApi.listBenchmarkTargets(),
        benchmarkApi.listBenchmarkDatasets(),
        benchmarkApi.listBenchmarkResults(),
        benchmarkApi.listBenchmarkEvaluations(),
        settingsApi.listLLMModels(),
      ]);
      setTargets(targetData);
      setDatasets(datasetData);
      setResults(resultData);
      setLegacy(oldData);
      setModels(Array.isArray(modelData) ? modelData : []);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const entries = tab === "site" ? targets.sites : tab === "api" ? targets.apis : targets.sast_runs;
  const target = entries.find((item) => String(item.id) === String(targetId));
  const selectedRun =
    tab === "sast" ? target : target?.runs.find((item) => String(item.id) === String(runId));
  const selectedResult = results.find((item) => item.id === selectedResultId);
  const relevantResults = useMemo(
    () =>
      results.filter((item) =>
        tab === "site"
          ? (item.target_kind === "site" && String(item.target_id) === String(targetId)) ||
            (item.run_kind === "sast" &&
              item.target_id == null &&
              target?.dataset?.id != null &&
              item.dataset_id === target?.dataset?.id &&
              [...targets.sites, ...targets.apis].filter(
                (entry) => entry.dataset?.id === item.dataset_id,
              ).length === 1)
          : item.run_kind === tab &&
            (tab === "sast" || String(item.target_id) === String(targetId)),
      ),
    [results, tab, targetId, target, targets],
  );
  const findingsById = new Map((selectedResult?.findings || []).map((item) => [item.id, item]));
  const savedDatasetIds = new Set(
    [...targets.sites, ...targets.apis].map((item) => item.dataset?.id).filter(Boolean),
  );

  const changeTab = (next) => {
    setTab(next);
    setTargetId("");
    setRunId("");
    setDatasetId("");
    setUploadedDatasetId(null);
    setEvaluationModel("");
    setSelectedResultId(null);
    setEdit(null);
    setError(null);
  };
  const upload = async (file) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const parsed = parseGroundTruthText(await file.text(), file.name);
      const dataset = await benchmarkApi.createBenchmarkDataset({
        name: parsed.name || file.name,
        ground_truth: parsed,
      });
      if (tab === "sast") {
        setUploadedDatasetId(dataset.id);
        setDatasetId(String(dataset.id));
      } else await benchmarkApi.saveBenchmarkGroundTruth(tab, Number(targetId), dataset.id);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  const compare = async () => {
    if (!runId) return;
    setBusy(true);
    setError(null);
    try {
      const result = await benchmarkApi.createBenchmarkResult({
        run_kind: tab,
        run_id: Number(runId),
        ...(tab === "sast" ? { dataset_id: Number(datasetId) } : {}),
        ...(evaluationModel ? { evaluation_model_id: Number(evaluationModel) } : {}),
      });
      await load();
      setResults((current) => [result, ...current.filter((item) => item.id !== result.id)]);
      setSelectedResultId(result.id);
      if (tab === "site") setSiteTab("analyses");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  const deleteResult = async () => {
    if (!selectedResult || !confirm(`Delete the saved result for "${selectedResult.run_name}"?`))
      return;
    setBusy(true);
    setError(null);
    try {
      await benchmarkApi.deleteBenchmarkResult(selectedResult.id);
      setResults((current) => current.filter((result) => result.id !== selectedResult.id));
      setSelectedResultId(null);
      setEdit(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  const saveReview = async (item) => {
    setBusy(true);
    setError(null);
    try {
      const updated = await benchmarkApi.reviewBenchmarkResult(
        selectedResult.id,
        item.external_id,
        {
          disposition: edit.disposition,
          finding_ids: edit.disposition === "missing" ? [] : edit.finding_ids,
          note: edit.note,
        },
      );
      setResults((current) =>
        current.map((result) => (result.id === updated.id ? updated : result)),
      );
      setEdit(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Benchmark Lab" />
      <div className="tab-bar benchmark-top-tabs" role="tablist" aria-label="Scan type">
        {[
          ["site", "Sites"],
          ["api", "APIs"],
          ["sast", "SAST"],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className={`tab-btn${tab === key ? " active" : ""}`}
            onClick={() => changeTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "site" && (
        <div
          className="tab-bar benchmark-site-tabs"
          role="tablist"
          aria-label="Site benchmark views"
        >
          {[
            ["summary", "Summary"],
            ["analyses", "Analyses"],
            ["new", "New"],
          ].map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={siteTab === key}
              className={`tab-btn${siteTab === key ? " active" : ""}`}
              onClick={() => {
                setSiteTab(key);
                setSelectedResultId(null);
                setEdit(null);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      <div className="content scroll-content benchmark-page benchmark-simple">
        <CompletedScanBenchmarks
          key={tab}
          category={tab}
          targets={targets}
          results={results}
          legacy={legacy}
          datasets={datasets}
          models={models}
          onChange={load}
          onOpen={(id) => {
            const result = results.find((item) => item.id === id);
            if (result) setTargetId(String(result.target_id ?? result.run_id));
            setSelectedResultId(id);
            if (tab === "site") setSiteTab("analyses");
          }}
        />
        {error && <div className="alert error">{error}</div>}
        {tab === "site" && (
          <label className="benchmark-site-picker">
            Site
            <select
              className="select"
              value={targetId}
              onChange={(event) => {
                setTargetId(event.target.value);
                setRunId("");
                setEvaluationModel("");
                setSelectedResultId(null);
              }}
            >
              <option value="">Select an application...</option>
              {targets.sites.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
        )}
        {tab === "site" && target && siteTab === "summary" && (
          <SiteSummary
            results={relevantResults}
            onOpen={(id) => {
              const result = results.find((item) => item.id === id);
              if (result) setTargetId(String(result.target_id ?? result.run_id));
              setSelectedResultId(id);
              setSiteTab("analyses");
            }}
          />
        )}
        {tab === "site" && target && siteTab === "analyses" && (
          <section className="card benchmark-analyses">
            <h2>Saved analyses</h2>
            {relevantResults.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Scan</th>
                      <th>Type</th>
                      <th>Model</th>
                      <th>Scan cost</th>
                      <th>Full + partial</th>
                      <th>Created</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {relevantResults.map((result) => (
                      <tr key={result.id}>
                        <td>{result.run_name}</td>
                        <td>{result.run_kind === "sast" ? "SAST" : "DAST"}</td>
                        <td>{modelName(result)}</td>
                        <td>{money(result.scan_cost_usd)}</td>
                        <td>{result.summary.full + result.summary.partial}</td>
                        <td>{new Date(result.created_at).toLocaleString()}</td>
                        <td>
                          <button
                            type="button"
                            className="btn ghost sm"
                            onClick={() => {
                              setSelectedResultId(result.id);
                              setExpanded(null);
                              setEdit(null);
                            }}
                          >
                            Open {result.run_name}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="subtle">No analyses have been saved for this Site.</p>
            )}
          </section>
        )}
        {(tab !== "site" || siteTab === "new") && (
          <section className="card benchmark-setup">
            {tab !== "site" && (
              <>
                <label>
                  {tab === "site" ? "Site" : tab === "api" ? "API" : "Completed SAST scan"}
                  <select
                    className="select"
                    value={targetId}
                    onChange={(event) => {
                      setTargetId(event.target.value);
                      setRunId(tab === "sast" ? event.target.value : "");
                      setEvaluationModel("");
                      setSelectedResultId(null);
                    }}
                  >
                    <option value="">
                      Select {tab === "sast" ? "a scan" : "an application"}...
                    </option>
                    {entries.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            )}
            {target && (
              <>
                {tab !== "sast" ? (
                  <>
                    <div className="benchmark-ground-truth-choice">
                      <div>
                        <strong>Ground truth</strong>
                        <div className="subtle">
                          {target.dataset
                            ? `${target.dataset.name} - ${target.dataset.item_count} findings`
                            : "No file uploaded"}
                        </div>
                      </div>
                      <label className="btn secondary" htmlFor="benchmark-ground-truth-file">
                        {target.dataset ? "Replace file" : "Upload file"}
                      </label>
                      <input
                        id="benchmark-ground-truth-file"
                        type="file"
                        accept=".json,.md,.markdown"
                        onChange={(event) => {
                          upload(event.target.files?.[0]);
                          event.target.value = "";
                        }}
                      />
                    </div>
                    <label>
                      Completed scan
                      <select
                        className="select"
                        value={runId}
                        onChange={(event) => {
                          setRunId(event.target.value);
                          setEvaluationModel("");
                        }}
                      >
                        <option value="">Select a scan...</option>
                        {target.runs.map((run) => (
                          <option key={run.id} value={run.id}>
                            {run.name} ({run.status})
                          </option>
                        ))}
                      </select>
                    </label>
                  </>
                ) : (
                  <>
                    <div className="benchmark-sast-ground-truth">
                      <label>
                        Ground truth
                        <select
                          className="select"
                          value={datasetId}
                          onChange={(event) => setDatasetId(event.target.value)}
                        >
                          <option value="">Select a saved file...</option>
                          {datasets
                            .filter(
                              (dataset) =>
                                savedDatasetIds.has(dataset.id) || dataset.id === uploadedDatasetId,
                            )
                            .map((dataset) => (
                              <option key={dataset.id} value={dataset.id}>
                                {dataset.name} ({dataset.item_count} findings)
                              </option>
                            ))}
                        </select>
                      </label>
                      <label className="btn secondary" htmlFor="benchmark-sast-file">
                        Upload another file
                      </label>
                      <input
                        id="benchmark-sast-file"
                        type="file"
                        accept=".json,.md,.markdown"
                        onChange={(event) => {
                          upload(event.target.files?.[0]);
                          event.target.value = "";
                        }}
                      />
                    </div>
                  </>
                )}
                <label>
                  Evaluation model
                  <select
                    className="select"
                    value={evaluationModel}
                    onChange={(event) => setEvaluationModel(event.target.value)}
                  >
                    <option value="">
                      {selectedRun?.default_evaluation_model
                        ? `Scan's Test Lead model: ${selectedRun.default_evaluation_model.name}`
                        : "Choose a model..."}
                    </option>
                    {models.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="btn primary benchmark-compare-button"
                  type="button"
                  onClick={compare}
                  disabled={
                    busy ||
                    !runId ||
                    (!evaluationModel && !selectedRun?.default_evaluation_model) ||
                    (tab === "sast" ? !datasetId : !target.dataset)
                  }
                >
                  {busy ? "Working..." : "Compare scan"}
                </button>
              </>
            )}
          </section>
        )}
        {tab !== "site" && relevantResults.length > 0 && (
          <label className="benchmark-result-picker">
            Saved results
            <select
              className="select"
              value={selectedResultId || ""}
              onChange={(event) => setSelectedResultId(Number(event.target.value) || null)}
            >
              <option value="">Select a result...</option>
              {relevantResults.map((result) => (
                <option key={result.id} value={result.id}>
                  {result.run_name} - {new Date(result.created_at).toLocaleString()}
                </option>
              ))}
            </select>
          </label>
        )}
        {selectedResult && (tab !== "site" || siteTab === "analyses") && (
          <section className="benchmark-results">
            <div className="benchmark-result-heading">
              <h2>{selectedResult.run_name}</h2>
              <button
                className="btn secondary"
                type="button"
                onClick={deleteResult}
                disabled={busy}
              >
                Delete result
              </button>
            </div>
            <p className="subtle">
              Compared with {selectedResult.ground_truth.name || "ground truth"} on{" "}
              {new Date(selectedResult.created_at).toLocaleString()}
            </p>
            <p className="subtle">
              {selectedResult.comparison?.method === "model"
                ? `Compared by ${selectedResult.comparison.model?.name}`
                : selectedResult.comparison?.fallback_reason
                  ? `Rules-only fallback${selectedResult.comparison.model?.name ? ` after ${selectedResult.comparison.model.name}` : ""}: ${selectedResult.comparison.fallback_reason}`
                  : selectedResult.comparison?.method === "rules"
                    ? "Rules-only comparison"
                    : "Comparison method was not recorded for this older result"}
            </p>
            {selectedResult.scan_models ? (
              <div className="benchmark-scan-models">
                {selectedResult.run_kind !== "sast" && (
                  <p className="subtle">
                    Test Lead model: {modelLabel(selectedResult.scan_models.test_lead)}
                  </p>
                )}
                {(selectedResult.scan_models.sast || []).map((source) => (
                  <p className="subtle" key={source.run_id}>
                    SAST model
                    {selectedResult.run_kind !== "sast" && source.run_name
                      ? ` (${source.run_name})`
                      : ""}
                    : {modelLabel(source.model)}
                  </p>
                ))}
              </div>
            ) : (
              <p className="subtle">Scan model details were not saved for this older result.</p>
            )}
            <div className="benchmark-summary-grid benchmark-counts">
              {["full", "partial", "missing"].map((status) => (
                <div className="benchmark-stat" key={status}>
                  <span>{status}</span>
                  <strong>{selectedResult.summary[status]}</strong>
                </div>
              ))}
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Ground truth finding</th>
                    <th>Result</th>
                    <th>Matching scan finding</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedResult.ground_truth.items.map((item) => {
                    const row = selectedResult.rows.find(
                      (candidate) => candidate.external_id === item.external_id,
                    );
                    const open = expanded === item.external_id;
                    return (
                      <tr key={item.external_id}>
                        <td>
                          <button
                            className="benchmark-row-toggle"
                            type="button"
                            onClick={() => setExpanded(open ? null : item.external_id)}
                          >
                            {open ? "▾" : "▸"} {item.external_id} -{" "}
                            {item.title || item.description || "Untitled finding"}
                          </button>
                          {open && (
                            <div className="benchmark-expanded-row">
                              <p>
                                {item.description || item.root_cause || "No description supplied."}
                              </p>
                              <p>{row?.reason}</p>
                              {edit?.external_id === item.external_id ? (
                                <div className="benchmark-review-form">
                                  <label>
                                    Result{" "}
                                    <select
                                      className="select"
                                      value={edit.disposition}
                                      onChange={(event) =>
                                        setEdit({ ...edit, disposition: event.target.value })
                                      }
                                    >
                                      <option value="full">Full</option>
                                      <option value="partial">Partial</option>
                                      <option value="missing">Missing</option>
                                    </select>
                                  </label>
                                  {edit.disposition !== "missing" && (
                                    <fieldset>
                                      <legend>Matching findings</legend>
                                      {selectedResult.findings.map((finding) => (
                                        <label key={finding.id}>
                                          <input
                                            type="checkbox"
                                            checked={edit.finding_ids.includes(finding.id)}
                                            onChange={(event) =>
                                              setEdit({
                                                ...edit,
                                                finding_ids: event.target.checked
                                                  ? [...edit.finding_ids, finding.id]
                                                  : edit.finding_ids.filter(
                                                      (id) => id !== finding.id,
                                                    ),
                                              })
                                            }
                                          />{" "}
                                          {finding.reference} - {finding.title}
                                        </label>
                                      ))}
                                    </fieldset>
                                  )}
                                  <label>
                                    Reason{" "}
                                    <textarea
                                      value={edit.note}
                                      onChange={(event) =>
                                        setEdit({ ...edit, note: event.target.value })
                                      }
                                    />
                                  </label>
                                  <button
                                    className="btn primary sm"
                                    type="button"
                                    disabled={busy}
                                    onClick={() => saveReview(item)}
                                  >
                                    Save
                                  </button>
                                  <button
                                    className="btn ghost sm"
                                    type="button"
                                    onClick={() => setEdit(null)}
                                  >
                                    Cancel
                                  </button>
                                </div>
                              ) : (
                                <button
                                  className="btn ghost sm"
                                  type="button"
                                  onClick={() =>
                                    setEdit({
                                      external_id: item.external_id,
                                      disposition: row.disposition,
                                      finding_ids: row.finding_ids,
                                      note: row.review_note || "",
                                    })
                                  }
                                >
                                  Review result
                                </button>
                              )}
                            </div>
                          )}
                        </td>
                        <td>
                          <span
                            className={`benchmark-disposition ${row?.disposition || "missing"}`}
                          >
                            {row?.disposition || "missing"}
                            {row?.reviewed ? " (reviewed)" : ""}
                          </span>
                        </td>
                        <td>
                          {row?.finding_ids
                            .map((id) => findingsById.get(id)?.reference || `#${id}`)
                            .join(", ") || "-"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}
        {tab === "sast" && legacy.length > 0 && (
          <details className="card">
            <summary>Earlier SAST evaluations ({legacy.length})</summary>
            <ul>
              {legacy.map((item) => (
                <li key={item.id}>
                  <a href={`#/benchmark-lab/evaluations/${item.id}`}>
                    {item.name || `Evaluation #${item.id}`}
                  </a>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </>
  );
}
