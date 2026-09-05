import * as apiRunsApi from "../../shared/api/apiRuns.js";
import { useState, useEffect } from "react";

import { nav } from "../../shared/navigation/router.js";
import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";
import { PageHeader, Crumb, Sep } from "../../shared/ui/PageHeader.jsx";
import { formatPhase, formatTerminalReason } from "../../shared/runs/presentation.jsx";
import { ApiRunStatusTab } from "./ApiRunStatusTab.jsx";
import { ApiRunFindingsTab } from "./ApiRunFindingsTab.jsx";
import { ApiRunLeadsTab } from "./ApiRunLeadsTab.jsx";
import { ApiRunSessionsTab } from "./ApiRunSessionsTab.jsx";
import { ApiRunTrafficTab } from "./ApiRunTrafficTab.jsx";
import { ApiRunEndpointsTab } from "./ApiRunEndpointsTab.jsx";
import { ApiRunWorkProgramTab } from "./ApiRunWorkProgramTab.jsx";

const API_RUN_TABS = [
  {
    key: "status",
    label: "Status",
  },
  {
    key: "findings",
    label: "Findings",
  },
  {
    key: "leads",
    label: "SAST Leads",
  },
  {
    key: "sessions",
    label: "Sessions",
  },
  {
    key: "traffic",
    label: "Traffic Log",
  },
  {
    key: "endpoints",
    label: "Endpoints",
  },
  {
    key: "workprogram",
    label: "OWASP Coverage",
  },
];

// Reuse the same alice session management infrastructure as TestRunDetail but
// bound to the /api/api-test-runs/{id}/* alias routes.

export function ApiTestRunDetail({ runId, initialTab, initialFindingRef }) {
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);
  const [scanStatus, setScanStatus] = useState(null);
  const [scanBusy, setScanBusy] = useState(false);
  const [coverageMode, setCoverageMode] = useState("track");
  const tab = API_RUN_TABS.some((item) => item.key === initialTab) ? initialTab : "status";
  useEffect(() => {
    apiRunsApi
      .getApiRun(runId)
      .then((r) => {
        setRun(r);
        setCoverageMode(r.coverage_mode || "track");
      })
      .catch((e) => setError(e.message));
    apiRunsApi
      .getApiScanStatus(runId)
      .then(setScanStatus)
      .catch(() => {});
  }, [runId]);

  // Poll scan status while scanning.
  useEffect(() => {
    if (!scanStatus?.running) return;
    const t = setInterval(() => {
      apiRunsApi
        .getApiScanStatus(runId)
        .then((st) => {
          setScanStatus(st);
          // Refresh the full run record too — phase/outcome/terminal_reason only
          // live there, and would otherwise stay stuck at whatever they were when
          // the scan started until it finishes.
          apiRunsApi
            .getApiRun(runId)
            .then(setRun)
            .catch(() => {});
        })
        .catch(() => {});
    }, 3000);
    return () => clearInterval(t);
  }, [scanStatus?.running, runId]);
  const onStartScan = async () => {
    setScanBusy(true);
    try {
      await apiRunsApi.startApiScan(runId, coverageMode);
      const st = await apiRunsApi.getApiScanStatus(runId);
      setScanStatus(st);
      apiRunsApi
        .getApiRun(runId)
        .then((r) => {
          setRun(r);
          setCoverageMode(r.coverage_mode || "track");
        })
        .catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setScanBusy(false);
    }
  };
  const onStopScan = async () => {
    setScanBusy(true);
    try {
      await apiRunsApi.stopApiScan(runId);
      const st = await apiRunsApi.getApiScanStatus(runId);
      setScanStatus(st);
      apiRunsApi
        .getApiRun(runId)
        .then(setRun)
        .catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setScanBusy(false);
    }
  };
  const onResumeScan = async () => {
    setScanBusy(true);
    try {
      await apiRunsApi.resumeApiScan(runId);
      setScanStatus(await apiRunsApi.getApiScanStatus(runId));
      setRun(await apiRunsApi.getApiRun(runId));
    } catch (e) {
      setError(e.message);
    } finally {
      setScanBusy(false);
    }
  };
  const onDelete = async () => {
    if (!run) return;
    if (!confirm(`Delete test run "${run.name}"?`)) return;
    try {
      await apiRunsApi.deleteApiRun(runId);
      nav(`#/apis/${run.collection_id}`);
    } catch (e) {
      setError(e.message);
    }
  };
  const scanRunning = scanStatus?.running === true;
  if (!run) {
    return (
      <div className="content scroll-content">
        {error ? (
          <div className="alert error">{error}</div>
        ) : (
          <div className="subtle">Loading…</div>
        )}
      </div>
    );
  }
  return (
    <>
      <PageHeader
        title={
          <>
            <Crumb href={run ? `#/apis/${run.collection_id}` : "#/apis"}>API collection</Crumb>
            <Sep />
            {run ? run.name : "…"}
            {run && (
              <>
                {" "}
                <StatusBadge status={run.status} />
                {run.phase && run.phase !== "created" && (
                  <span className="run-status-badge" style={{ marginLeft: 6, opacity: 0.85 }}>
                    phase: {formatPhase(run.phase)}
                  </span>
                )}
                {run.terminal_reason && (
                  <span
                    className="run-status-badge"
                    style={{
                      marginLeft: 6,
                      color: run.outcome === "complete" ? "var(--ok)" : "var(--warn)",
                    }}
                  >
                    reason: {formatTerminalReason(run.terminal_reason)}
                  </span>
                )}
              </>
            )}
          </>
        }
        actions={
          <>
            {scanRunning ? (
              <button className="btn danger-outline" disabled={scanBusy} onClick={onStopScan}>
                {scanBusy ? "Stopping…" : "Stop Scan"}
              </button>
            ) : run.status === "paused" ? (
              <button className="btn" disabled={scanBusy} onClick={onResumeScan}>
                {scanBusy ? "Resuming…" : "Resume Scan"}
              </button>
            ) : (
              <>
                <label
                  className="subtle"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: 12,
                  }}
                  title="Quick: observe coverage as the scan runs. Standard: require the configured percentage of applicable coverage cells. Full: drive every applicable endpoint × category to covered or skipped-with-reason. SAST Validate: validate only imported SAST leads."
                >
                  Scan mode:
                  <select
                    value={coverageMode}
                    disabled={scanBusy}
                    onChange={(e) => setCoverageMode(e.target.value)}
                  >
                    <option value="track">Quick</option>
                    <option value="standard">Standard</option>
                    <option value="enforce">Full</option>
                    <option value="sast_validate">SAST Validate</option>
                  </select>
                </label>
                <button className="btn" disabled={scanBusy} onClick={onStartScan}>
                  {scanBusy ? "Starting…" : "Start Scan"}
                </button>
              </>
            )}
            {run && (
              <button className="btn danger-outline" onClick={onDelete}>
                Delete
              </button>
            )}
          </>
        }
      />
      <div className="tab-bar">
        {API_RUN_TABS.map((t) => (
          <button
            key={t.key}
            className={"tab-btn" + (tab === t.key ? " active" : "")}
            onClick={() => nav(`#/api-runs/${runId}/${t.key}`)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div
        className={
          "content no-padding" + (tab === "status" ? " flex-fill-noscroll" : " scroll-content")
        }
      >
        {error && <div className="alert error">{error}</div>}
        {tab === "status" && <ApiRunStatusTab runId={runId} scanRunning={scanRunning} />}
        {tab === "findings" && (
          <ApiRunFindingsTab
            runId={runId}
            scanRunning={scanRunning}
            run={run}
            initialFindingRef={initialFindingRef}
          />
        )}
        {tab === "leads" && <ApiRunLeadsTab runId={runId} scanRunning={scanRunning} />}
        {tab === "sessions" && <ApiRunSessionsTab runId={runId} scanRunning={scanRunning} />}
        {tab === "traffic" && <ApiRunTrafficTab runId={runId} scanRunning={scanRunning} />}
        {tab === "endpoints" && <ApiRunEndpointsTab run={run} />}
        {tab === "workprogram" && (
          <ApiRunWorkProgramTab runId={runId} scanRunning={scanRunning} run={run} />
        )}
      </div>
    </>
  );
}
