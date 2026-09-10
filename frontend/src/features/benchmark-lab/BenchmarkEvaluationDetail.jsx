import { useCallback, useEffect, useMemo, useState } from "react";
import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import { BenchmarkAuditPanel } from "./BenchmarkAuditPanel.jsx";
import { BenchmarkMetricTable, BenchmarkSummary } from "./BenchmarkSummary.jsx";
import { GroundTruthMatrix } from "./GroundTruthMatrix.jsx";
import { MatchReviewPanel } from "./MatchReviewPanel.jsx";
import { nav } from "../../shared/navigation/router.js";
import { PageHeader, Crumb, Sep } from "../../shared/ui/PageHeader.jsx";
import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";

const TABS = ["summary", "ground-truth", "additional-findings", "coverage", "efficiency", "audit"];
const normaliseTab = (tab) => (TABS.includes(tab) ? tab : "summary");
const parseObject = (value) => {
  if (value && typeof value === "object") return value;
  try {
    return JSON.parse(value || "{}");
  } catch {
    return {};
  }
};

export function BenchmarkEvaluationDetail({ evaluationId, initialTab }) {
  const [evaluation, setEvaluation] = useState(null);
  const [tab, setTab] = useState(normaliseTab(initialTab));
  const [reviewMatch, setReviewMatch] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const load = useCallback(async () => {
    try {
      const data = await benchmarkApi.getBenchmarkEvaluation(evaluationId);
      let dataset = null;
      if (data?.dataset_id) {
        try {
          dataset = await benchmarkApi.getBenchmarkDataset(data.dataset_id);
        } catch {
          // Some deployments intentionally withhold dataset contents from the detail API.
        }
      }
      setEvaluation({ ...data, dataset });
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, [evaluationId]);
  useEffect(() => {
    load();
  }, [load]);
  const metrics = useMemo(
    () => parseObject(evaluation?.metrics_json || evaluation?.metrics),
    [evaluation],
  );
  const provenance = parseObject(evaluation?.run_provenance_json || evaluation?.run_provenance);
  const policy = parseObject(evaluation?.policy_json || evaluation?.policy);
  const matches = evaluation?.matches || [];
  const run = evaluation?.sast_run || evaluation?.run;
  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      await benchmarkApi.runBenchmarkEvaluation(evaluationId);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  const saveReview = async (matchId, body) => {
    try {
      await benchmarkApi.reviewBenchmarkMatch(evaluationId, matchId, body);
      await load();
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };
  const exportEvaluation = async () => {
    try {
      const data = await benchmarkApi.getBenchmarkEvaluationExport(evaluationId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `aespa-benchmark-evaluation-${evaluationId}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  };
  if (!evaluation)
    return (
      <div className="content scroll-content">
        {error ? (
          <div className="alert error">{error}</div>
        ) : (
          <div className="subtle">Loading…</div>
        )}
      </div>
    );
  return (
    <>
      <PageHeader
        title={
          <>
            <Crumb href="#/benchmark-lab">Benchmark Lab</Crumb>
            <Sep />
            {evaluation.name || `Evaluation #${evaluation.id}`}
          </>
        }
        actions={
          <>
            <button className="btn ghost sm" onClick={exportEvaluation}>
              Export
            </button>
            <button
              className="btn primary sm"
              onClick={start}
              disabled={busy || ["running", "completed"].includes(evaluation.status)}
            >
              {busy
                ? "Running…"
                : evaluation.status === "completed"
                  ? "Completed"
                  : "Run evaluation"}
            </button>
          </>
        }
      />
      <div className="benchmark-detail">
        <div className="benchmark-detail-head">
          <div>
            <span className="eyebrow">Evaluation #{evaluation.id}</span>
            <h1>{evaluation.name || `Evaluation #${evaluation.id}`}</h1>
            <div className="benchmark-meta">
              <StatusBadge status={evaluation.status || "pending"} />
              {run?.id || evaluation.sast_run_id ? (
                <a href={`#/sast-runs/${run?.id || evaluation.sast_run_id}/coverage`}>
                  SAST run #{run?.id || evaluation.sast_run_id}
                </a>
              ) : null}
              <span>{evaluation.match_mode || "assisted"} matching</span>
            </div>
          </div>
          {evaluation.error_message && (
            <div className="alert error">{evaluation.error_message}</div>
          )}
        </div>
        <div className="benchmark-tabs" role="tablist">
          {TABS.map((value) => (
            <button
              key={value}
              className={tab === value ? "active" : ""}
              onClick={() => {
                setTab(value);
                nav(`#/benchmark-lab/evaluations/${evaluationId}/${value}`);
              }}
            >
              {value.replaceAll("-", " ")}
            </button>
          ))}
        </div>
        <div className="benchmark-detail-content">
          {error && <div className="alert error">{error}</div>}
          {tab === "summary" && (
            <>
              <BenchmarkSummary evaluation={evaluation} />
              <div className="benchmark-two-column">
                <section className="card">
                  <h2>Evaluation caveats</h2>
                  <p>
                    {evaluation.blindness_status === "contaminated"
                      ? "This evaluation is contaminated and is excluded from aggregate scorecards by default."
                      : "Review partial coverage and audit checks before comparing this run with another evaluation."}
                  </p>
                  <dl className="benchmark-provenance">
                    <dt>Source digest</dt>
                    <dd>{provenance.source_archive_digest || evaluation.source_digest || "—"}</dd>
                    <dt>Completion assurance</dt>
                    <dd>
                      {provenance.completion_assurance || evaluation.completion_assurance || "—"}
                    </dd>
                  </dl>
                </section>
                <section className="card">
                  <h2>Configuration</h2>
                  <BenchmarkMetricTable metrics={policy} />
                </section>
              </div>
            </>
          )}
          {tab === "ground-truth" && (
            <GroundTruthMatrix evaluation={evaluation} onReview={setReviewMatch} />
          )}
          {tab === "additional-findings" && (
            <AdditionalFindings matches={matches} onReview={setReviewMatch} />
          )}
          {tab === "coverage" && <CoveragePanel evaluation={evaluation} />}
          {tab === "efficiency" && (
            <div className="card">
              <h2>Efficiency telemetry</h2>
              <BenchmarkMetricTable metrics={metrics} />
            </div>
          )}
          {tab === "audit" && <BenchmarkAuditPanel evaluation={evaluation} />}
        </div>
      </div>
      {reviewMatch && (
        <MatchReviewPanel
          match={reviewMatch}
          onClose={() => setReviewMatch(null)}
          onSave={saveReview}
        />
      )}
    </>
  );
}

function AdditionalFindings({ matches, onReview }) {
  const findings = matches.filter(
    (match) =>
      !match.ground_truth_external_id ||
      ["additional_valid", "false_positive", "duplicate", "unreviewed"].includes(match.disposition),
  );
  if (!findings.length)
    return <div className="empty-state">No additional scanner findings are recorded.</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Lead</th>
            <th>Disposition</th>
            <th>Confidence</th>
            <th>Rationale</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {findings.map((match) => (
            <tr key={match.id}>
              <td>{match.scan_lead_id ? `Lead #${match.scan_lead_id}` : "Unmatched item"}</td>
              <td>
                <span className={`benchmark-disposition ${match.disposition}`}>
                  {match.disposition || "unreviewed"}
                </span>
              </td>
              <td>{match.confidence ?? "—"}</td>
              <td>{match.rationale || "—"}</td>
              <td>
                <button className="btn ghost sm" onClick={() => onReview(match)}>
                  Review
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CoveragePanel({ evaluation }) {
  const coverage = evaluation.coverage || evaluation.semantic_coverage || {};
  const reasons = evaluation.partial_coverage_reasons || coverage.partial_coverage_reasons || [];
  return (
    <div className="benchmark-two-column">
      <section className="card">
        <h2>Semantic coverage</h2>
        <BenchmarkMetricTable metrics={coverage.summary || coverage} />
      </section>
      <section className="card">
        <h2>Partial coverage reasons</h2>
        {reasons.length ? (
          <ul className="benchmark-reasons">
            {reasons.map((reason, index) => (
              <li key={index}>
                {typeof reason === "string" ? reason : reason.reason || JSON.stringify(reason)}
              </li>
            ))}
          </ul>
        ) : (
          <div className="subtle">No partial coverage reasons recorded.</div>
        )}
      </section>
    </div>
  );
}
