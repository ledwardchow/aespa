import { useState, useCallback } from "react";
import { truncUrl, fmtDate } from "../lib/utilities";
import { api } from "../lib/api";
import { nav } from "../lib/router";
import { EmptyState } from "../components/EmptyState";
import { usePolling } from "../hooks/usePolling";

// ── Active jobs ───────────────────────────────────────────────────────────────

function activeJobBadge(job) {
  const status = job.status || "running";
  const key = status === "failed" ? "danger" : status === "stopping" ? "stopping" : status === "complete" ? "ok" : ["running", "analysing"].includes(status) ? "running" : "neutral";
  return <span className={"badge " + key}>{status}</span>;
}
function activeJobProgress(job) {
  if (job.total_pages !== null && job.total_pages !== undefined) {
    return `${job.pages_done || 0} / ${job.total_pages}`;
  }
  if (job.pages_done !== null && job.pages_done !== undefined) return job.pages_done;
  return "—";
}
export function ActiveJobsPage() {
  const [jobs, setJobs] = useState(null);
  const [error, setError] = useState(null);
  const [stopping, setStopping] = useState({}); // keyed by `${job_type}-${run_id}`

  const load = useCallback(async () => {
    try {
      setError(null);
      setJobs(await api.listActiveJobs());
    } catch (e) {
      setError(e.message);
    }
  }, []);
  usePolling(load, { intervalMs: 5000 });
  const stopJob = async j => {
    const key = `${j.job_type}-${j.run_id}`;
    setStopping(prev => ({
      ...prev,
      [key]: true
    }));
    try {
      if (j.run_type === "sast") {
        await api.stopSastScan(j.run_id);
      } else if (j.run_type === "api") {
        if (j.job_type === "A.L.I.C.E.") {
          await api.stopApiAliceRun(j.run_id);
        } else {
          await api.stopApiScan(j.run_id);
        }
      } else {
        if (j.job_type === "A.L.I.C.E.") {
          await api.stopAliceRun(j.run_id);
        } else {
          await api.stopRun(j.run_id);
        }
      }
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setStopping(prev => {
        const n = {
          ...prev
        };
        delete n[key];
        return n;
      });
    }
  };
  const stopAll = async () => {
    if (!jobs || jobs.length === 0) return;
    const promises = jobs.map(j => stopJob(j));
    await Promise.allSettled(promises);
  };
  return <>
    <div className="topbar">
      <div className="topbar-title">Active Jobs</div>
      <div className="topbar-actions">
        <button className="btn secondary" onClick={load}>Refresh</button>
        {jobs && jobs.length > 0 && <button className="btn danger" onClick={stopAll}>Stop All</button>}
      </div>
    </div>
    <div className="content scroll-content">
      {error && <div className="alert error" style={{
        marginBottom: 16
      }}>{error}</div>}
      {jobs === null && <div className="subtle">Loading…</div>}
      {jobs !== null && jobs.length === 0 && <EmptyState icon="▶"
        title="No active jobs"
        sub="Running crawls and scans will appear here." />}
      {jobs && jobs.length > 0 && <div className="table-wrap">
          <table>
            <colgroup>
              <col style={{
              width: "18%"
            }} /><col style={{
              width: "14%"
            }} /><col style={{
              width: "14%"
            }} /><col style={{
              width: "10%"
            }} /><col style={{
              width: "10%"
            }} /><col style={{
              width: "7%"
            }} /><col style={{
              width: "13%"
            }} /><col style={{
              width: "14%"
            }} />
            </colgroup>
            <thead><tr><th>Run</th><th>Site</th><th>Job</th><th>Status</th><th>Progress</th><th>Findings</th><th>Started</th><th></th></tr></thead>
            <tbody>{jobs.map(j => {
              const key = `${j.job_type}-${j.run_id}`;
              const isStopping = !!stopping[key];
              return <tr key={key}>
                <td>
                  <a href={j.run_type === "sast" ? `#/sast-runs/${j.run_id}/progress` : j.run_type === "api" ? `#/api-runs/${j.run_id}/status` : `#/runs/${j.run_id}`} style={{
                    fontWeight: 600
                  }}>{j.run_name}</a>
                  {j.current_url && <div className="url" style={{
                    marginTop: 3
                  }}>{truncUrl(j.current_url, 54)}</div>}
                </td>
                <td>{j.run_type === "sast" || j.run_type === "api" ? <a href={`#/apis/${j.collection_id}`}>{j.collection_name}</a> : <a href={`#/sites/${j.site_id}`}>{j.site_name}</a>}</td>
                <td>{j.job_type}</td>
                <td>{activeJobBadge(j)}</td>
                <td>{activeJobProgress(j)}</td>
                <td>{j.findings_count ?? <span className="subtle">—</span>}</td>
                <td className="subtle">{fmtDate(j.started_at || j.created_at)}</td>
                <td>
                  <div className="row" style={{
                    justifyContent: "flex-end",
                    gap: "6px"
                  }}>
                    <button className="btn secondary sm" onClick={() => nav(j.run_type === "sast" ? `#/sast-runs/${j.run_id}/progress` : j.run_type === "api" ? `#/api-runs/${j.run_id}/status` : `#/runs/${j.run_id}`)}>Open</button>
                    <button className="btn danger sm" onClick={() => stopJob(j)} disabled={isStopping}>{isStopping ? "Stopping…" : "Stop"}</button>
                  </div>
                </td>
              </tr>;
            })}
            </tbody>
          </table>
        </div>}
    </div>
  </>;
}
