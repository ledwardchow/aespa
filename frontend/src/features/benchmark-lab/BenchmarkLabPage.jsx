import { fmtDate } from "../../shared/lib/dates.js";
import { useCallback, useEffect, useMemo, useState } from "react";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import * as settingsApi from "../../shared/api/settings.js";
import { nav } from "../../shared/navigation/router.js";
import { useHashTab } from "../../shared/navigation/useHashTab.js";
import { Crumb, PageHeader, Sep } from "../../shared/ui/PageHeader.jsx";
import { parseGroundTruthText } from "./groundTruthImport.js";
import { BenchmarkModelSettings } from "./BenchmarkModelSettings.jsx";
import { BenchmarkPublishing } from "./BenchmarkPublishing.jsx";
import { BenchmarkTransfer } from "./BenchmarkTransfer.jsx";
import { GroundTruthDatasets } from "./GroundTruthDatasets.jsx";
import { CompletedScanBenchmarks } from "./CompletedScanBenchmarks.jsx";
import { BenchmarkFindingReview } from "./BenchmarkFindingReview.jsx";
import { SiteSummary, modelName, money } from "./SiteSummary.jsx";
import { BenchmarkResultComment } from "./BenchmarkResultComment.jsx";
import { modelBadges } from "./modelBadges.js";

import styles from "./BenchmarkSettings.module.css";
import { scanType } from "./scanPresentation.js";
import { PageError } from "../../shared/ui/Notice.jsx";

const EMPTY = { sites: [], apis: [], sast_runs: [] };
const modelLabel = (model) => {
  if (!model) return "Unavailable";
  if (model.name && model.model && model.name !== model.model)
    return `${model.name} (${model.model})`;
  return model.model || model.name || "Unavailable";
};
export function BenchmarkLabPage({ initialResultId }) {
  const [routeTab] = useHashTab("tab", ["site", "dast", "api", "sast", "datasets"], "site");
  const [routeSiteTab, setSiteTab] = useHashTab(
    "subtab",
    ["summary", "analyses", "new"],
    initialResultId ? "analyses" : "summary",
  );
  const [benchmarkView, setBenchmarkView] = useHashTab("view", ["scans", "results"], "scans");
  const [targets, setTargets] = useState(EMPTY);
  const [datasets, setDatasets] = useState([]);
  const [results, setResults] = useState([]);
  const [legacy, setLegacy] = useState([]);
  const [models, setModels] = useState([]);
  const [targetId, setTargetId] = useState("");
  const [runId, setRunId] = useState("");
  const [benchmarkSettings, setBenchmarkSettings] = useState({ default_model_id: null });
  const [selectedResultId, setSelectedResultId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const selectedResult = results.find((item) => item.id === selectedResultId);
  const resultBackHref = `#/benchmark-lab?tab=${selectedResult?.run_kind === "site" ? "dast" : selectedResult?.run_kind || "site"}&view=results`;
  const tab = initialResultId && selectedResult ? selectedResult.run_kind : routeTab;
  const siteTab = initialResultId && selectedResult ? "analyses" : routeSiteTab;

  const load = useCallback(async () => {
    try {
      const [targetData, datasetData, resultData, oldData, modelData, savedSettings] =
        await Promise.all([
          benchmarkApi.listBenchmarkTargets(),
          benchmarkApi.listBenchmarkDatasets(),
          benchmarkApi.listBenchmarkResults(),
          benchmarkApi.listBenchmarkEvaluations(),
          settingsApi.listLLMModels(),
          benchmarkApi.getBenchmarkSettings(),
        ]);
      setTargets(targetData);
      setDatasets(datasetData);
      setResults(resultData);
      const linkedResult = resultData.find((item) => item.id === initialResultId);
      if (linkedResult) {
        setTargetId(String(linkedResult.target_id || ""));
        setSelectedResultId(linkedResult.id);
      }
      setBenchmarkSettings(savedSettings);
      setLegacy(oldData);
      setModels(Array.isArray(modelData) ? modelData : []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoaded(true);
    }
  }, [initialResultId]);
  useEffect(() => {
    load();
  }, [load]);

  const category = tab === "dast" ? "site" : tab;
  const target = targets.sites.find((item) => String(item.id) === String(targetId));
  const defaultModel = models.find((item) => item.id === benchmarkSettings?.default_model_id);
  const relevantResults = useMemo(
    () =>
      results.filter((item) =>
        tab === "site"
          ? !targetId ||
            (targetId.startsWith("dataset:") && item.dataset_id === Number(targetId.slice(8))) ||
            (item.target_kind === "site" && String(item.target_id) === String(targetId)) ||
            ((item.imported || item.run_kind === "sast") &&
              item.target_id == null &&
              target?.dataset?.id != null &&
              item.dataset_id === target?.dataset?.id &&
              [...targets.sites, ...targets.apis].filter(
                (entry) => entry.dataset?.id === item.dataset_id,
              ).length === 1)
          : item.run_kind === category,
      ),
    [results, tab, category, targetId, target, targets],
  );
  const openResult = (id) => nav(`#/benchmark-lab/results/${id}`);
  const changeTab = (next) => {
    nav(`#/benchmark-lab?tab=${next}&subtab=${routeSiteTab}`);
    setTargetId("");
    setRunId("");
    setSelectedResultId(null);
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
      await benchmarkApi.saveBenchmarkGroundTruth("site", Number(targetId), dataset.id);
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
        run_kind: "site",
        run_id: Number(runId),
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
      if (initialResultId != null) nav(resultBackHref);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  const siteSelector = (
    <label className="benchmark-site-picker">
      Site
      <select
        aria-label="Site"
        className="select"
        value={targetId}
        onChange={(event) => {
          setTargetId(event.target.value);
          setRunId("");
          setSelectedResultId(null);
        }}
      >
        <option value="">
          {siteTab === "new" ? "Select an application…" : "All applications"}
        </option>
        {siteTab !== "new" &&
          datasets.map((item) => (
            <option key={`dataset:${item.id}`} value={`dataset:${item.id}`}>
              Dataset: {item.label || item.name}
            </option>
          ))}
        {targets.sites.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </select>
    </label>
  );

  const resultDetails = selectedResult ? (
    <section className="benchmark-results">
      <div className="benchmark-result-heading">
        <h2>{selectedResult.run_name}</h2>
        <button className="btn secondary" type="button" onClick={deleteResult} disabled={busy}>
          Delete result
        </button>
      </div>
      <p className="subtle">
        Compared with {selectedResult.ground_truth.name || "ground truth"} on{" "}
        {fmtDate(selectedResult.created_at)}
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
              Scan model: {modelLabel(selectedResult.scan_models.primary)}{" "}
              {modelBadges(selectedResult.scan_models.primary).map((label) => (
                <span
                  className={`benchmark-model-badge${label === "Glasswing" ? " benchmark-model-badge-glasswing" : ""}`}
                  key={label}
                >
                  {label}
                </span>
              ))}
            </p>
          )}
          {(selectedResult.scan_models.sast || []).map((source) => (
            <p className="subtle" key={source.run_id}>
              SAST model
              {selectedResult.run_kind !== "sast" && source.run_name ? ` (${source.run_name})` : ""}
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
      <BenchmarkFindingReview
        key={selectedResult.id}
        result={selectedResult}
        onSaved={(updated) =>
          setResults((current) =>
            current.map((result) => (result.id === updated.id ? updated : result)),
          )
        }
      />
      <BenchmarkResultComment
        key={`comment-${selectedResult.id}`}
        result={selectedResult}
        onSaved={(updated) =>
          setResults((current) =>
            current.map((result) => (result.id === updated.id ? updated : result)),
          )
        }
      />
    </section>
  ) : null;

  if (initialResultId != null) {
    return (
      <>
        <PageHeader
          title={
            <>
              <Crumb href="#/benchmark-lab">Benchmark Lab</Crumb>
              <Sep />
              Analysis
            </>
          }
          actions={
            <>
              <a className="btn ghost" href="#/benchmark-lab/scoring-guide">
                How scoring and matching work
              </a>
              <a className="btn secondary" href={resultBackHref}>
                Back to results
              </a>
            </>
          }
        />
        <div className="content scroll-content benchmark-page benchmark-simple">
          <PageError error={error} inline={!loaded} onDismiss={() => setError(null)} />
          {loaded && !error && !selectedResult && <p className="subtle">Analysis not found.</p>}
          {!loaded && <p className="subtle">Loading analysis…</p>}
          {resultDetails}
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Benchmark Lab"
        actions={
          <a className="btn ghost" href="#/benchmark-lab/scoring-guide">
            How scoring and matching work
          </a>
        }
      />
      <div className="tab-bar benchmark-top-tabs" role="tablist" aria-label="Scan type">
        {[
          ["site", "Results"],
          ["dast", "DAST"],
          ["api", "APIs"],
          ["sast", "SAST"],
          ["datasets", "Settings"],
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
              }}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      {["dast", "api", "sast"].includes(tab) && (
        <div
          className="tab-bar benchmark-site-tabs"
          role="tablist"
          aria-label={`${tab === "dast" ? "DAST" : tab === "api" ? "API" : "SAST"} benchmark views`}
        >
          {[
            ["scans", "Scans"],
            ["results", "Saved results"],
          ].map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={benchmarkView === key}
              className={`tab-btn${benchmarkView === key ? " active" : ""}`}
              onClick={() => setBenchmarkView(key)}
            >
              {label}
              {key === "results"
                ? ` (${relevantResults.length + (tab === "sast" ? legacy.filter((item) => item.status === "completed").length : 0)})`
                : ""}
            </button>
          ))}
        </div>
      )}
      <div
        className={`content scroll-content benchmark-page benchmark-simple${tab === "site" && siteTab === "summary" ? " benchmark-summary-page" : ""}`}
      >
        {["dast", "api", "sast"].includes(tab) && benchmarkView === "scans" && (
          <CompletedScanBenchmarks
            key={tab}
            category={category}
            targets={targets}
            results={results}
            legacy={legacy}
            datasets={datasets}
            defaultModel={defaultModel}
            onChange={load}
            onOpen={openResult}
          />
        )}
        {tab === "datasets" && (
          <div className={styles.settings}>
            <BenchmarkPublishing datasets={datasets} results={results} />
            <BenchmarkTransfer onChange={load} />
            <BenchmarkModelSettings models={models} settings={benchmarkSettings} onChange={load} />
            <GroundTruthDatasets datasets={datasets} targets={targets} onChange={load} />
          </div>
        )}
        <PageError error={error} inline={!loaded} onDismiss={() => setError(null)} />
        {tab === "site" && siteTab !== "summary" && siteSelector}
        {tab === "site" && siteTab === "summary" && (
          <SiteSummary
            siteSelector={siteSelector}
            showChart={relevantResults.length > 0}
            results={relevantResults}
            onOpen={openResult}
          />
        )}
        {tab === "site" && siteTab === "analyses" && (
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
                        <td>
                          {result.run_name}
                          {result.imported ? " (imported)" : ""}
                        </td>
                        <td>{scanType(result.run_kind, result.scan_models)}</td>
                        <td>{modelName(result)}</td>
                        <td>{money(result.scan_cost_usd)}</td>
                        <td>{result.summary.full + result.summary.partial}</td>
                        <td>{fmtDate(result.created_at)}</td>
                        <td>
                          <a className="btn ghost sm" href={`#/benchmark-lab/results/${result.id}`}>
                            Open {result.run_name}
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="subtle">No saved analyses match this selection.</p>
            )}
          </section>
        )}
        {tab === "site" && siteTab === "new" && (
          <section className="card benchmark-setup">
            {target && (
              <>
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
                      }}
                    >
                      <option value="">Select a scan…</option>
                      {target.runs.map((run) => (
                        <option key={run.id} value={run.id}>
                          {run.name} ({run.status})
                        </option>
                      ))}
                    </select>
                  </label>
                </>
                <p className="subtle">
                  {defaultModel
                    ? `Benchmark model: ${defaultModel.name}`
                    : "Choose a default benchmark model in Settings first."}
                </p>
                <button
                  className="btn primary benchmark-compare-button"
                  type="button"
                  onClick={compare}
                  disabled={busy || !runId || !defaultModel || !target.dataset}
                >
                  {busy ? "Working…" : "Compare scan"}
                </button>
              </>
            )}
          </section>
        )}
        {["dast", "api", "sast"].includes(tab) && benchmarkView === "results" && (
          <section
            className="card benchmark-saved-list"
            aria-label={`Saved ${tab === "dast" ? "DAST" : tab === "api" ? "API" : "SAST"} results`}
          >
            <h2>
              Saved results (
              {relevantResults.length +
                (tab === "sast" ? legacy.filter((item) => item.status === "completed").length : 0)}
              )
            </h2>
            {relevantResults.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Scan</th>
                      {tab !== "sast" && <th>Application</th>}
                      <th>Ground truth</th>
                      <th>Full / partial / missing</th>
                      <th>Created</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {relevantResults.map((result) => (
                      <tr key={result.id}>
                        <td>{result.run_name}</td>
                        {tab !== "sast" && (
                          <td>
                            {targets[tab === "dast" ? "sites" : "apis"].find(
                              (target) => target.id === result.target_id,
                            )?.name || "-"}
                          </td>
                        )}
                        <td>
                          {result.ground_truth?.name ||
                            datasets.find((dataset) => dataset.id === result.dataset_id)?.name ||
                            "-"}
                        </td>
                        <td>
                          {result.summary?.full ?? 0} / {result.summary?.partial ?? 0} /{" "}
                          {result.summary?.missing ?? 0}
                        </td>
                        <td>{result.created_at ? fmtDate(result.created_at) : "-"}</td>
                        <td>
                          <a className="btn ghost sm" href={`#/benchmark-lab/results/${result.id}`}>
                            Open {result.run_name}
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="subtle">
                No saved {tab === "dast" ? "DAST" : tab === "api" ? "API" : "SAST"} results yet.
              </p>
            )}
            {tab === "sast" && legacy.filter((item) => item.status === "completed").length > 0 && (
              <div className="benchmark-legacy-results">
                <h3>Earlier SAST evaluations</h3>
                <ul>
                  {legacy
                    .filter((item) => item.status === "completed")
                    .map((item) => (
                      <li key={item.id}>
                        <a href={`#/benchmark-lab/evaluations/${item.id}`}>
                          {item.name || `Evaluation #${item.id}`}
                        </a>
                      </li>
                    ))}
                </ul>
              </div>
            )}
          </section>
        )}
        {selectedResult && tab === "site" && siteTab === "analyses" && resultDetails}
      </div>
    </>
  );
}
