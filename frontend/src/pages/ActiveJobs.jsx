import { useState, useCallback, useMemo } from "react";
import { truncUrl, fmtDate } from "../lib/utilities";
import { api } from "../lib/api";
import { nav } from "../lib/router";
import { EmptyState } from "../components/EmptyState";
import { usePolling } from "../hooks/usePolling";

// ── Active jobs ───────────────────────────────────────────────────────────────

function activeJobBadge(job) {
  const status = job.status || "running";
  const key = status === "failed" ? "danger" : status === "stopping" ? "stopping" : status === "complete" ? "ok" : ["running", "analysing", "analyzing", "sast_running", "correlating", "dast_running"].includes(status) ? "running" : "neutral";
  const label = { sast_running: "source scan", correlating: "correlating", dast_running: "live testing" }[status] || status;
  return <span className={"badge " + key}>{label === "analyzing" ? "analysing" : label}</span>;
}
function activeJobProgress(job) {
  if (job.total_pages !== null && job.total_pages !== undefined) {
    return `${job.pages_done || 0} / ${job.total_pages}`;
  }
  if (job.pages_done !== null && job.pages_done !== undefined) return job.pages_done;
  return "—";
}
function activeJobScopeName(job) {
  if (job.run_type === "campaign") return job.application_name || `Application #${job.application_id}`;
  if (job.run_type === "api") return job.collection_name || `API #${job.collection_id}`;
  if (job.run_type === "sast") return job.collection_id ? (job.collection_name || `API #${job.collection_id}`) : job.run_name;
  return job.site_name || `Site #${job.site_id}`;
}
function activeJobScopeLink(job) {
  if (job.run_type === "campaign") return `#/applications/${job.application_id}/campaigns/${job.run_id}`;
  if (job.run_type === "api") return `#/apis/${job.collection_id}`;
  if (job.run_type === "sast") return job.collection_id ? `#/apis/${job.collection_id}` : `#/sast-runs/${job.run_id}/progress`;
  return `#/sites/${job.site_id}`;
}
export function ActiveJobsPage() {
  const [jobs, setJobs] = useState(null);
  const [error, setError] = useState(null);
  const [stopping, setStopping] = useState({}); // keyed by `${job_type}-${run_id}`
  const [sortField, setSortField] = useState("started_at");
  const [sortDir, setSortDir] = useState("desc");

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDir(d => d === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const sortArrow = (field) => {
    if (sortField !== field) return null;
    return <span style={{ marginLeft: "4px", fontSize: "10px", opacity: 0.85 }}>{sortDir === "asc" ? "▲" : "▼"}</span>;
  };

  const sortedJobs = useMemo(() => {
    if (!jobs) return [];
    return [...jobs].sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (sortField === "site_name") {
        valA = activeJobScopeName(a);
        valB = activeJobScopeName(b);
      } else if (sortField === "pages_done") {
        valA = a.pages_done || 0;
        valB = b.pages_done || 0;
      } else if (sortField === "findings_count") {
        valA = a.findings_count || 0;
        valB = b.findings_count || 0;
      } else if (sortField === "started_at") {
        valA = (a.started_at || a.created_at) ? new Date(a.started_at || a.created_at).getTime() : 0;
        valB = (b.started_at || b.created_at) ? new Date(b.started_at || b.created_at).getTime() : 0;
      }

      if (valA == null) valA = "";
      if (valB == null) valB = "";

      let cmp = typeof valA === "number" && typeof valB === "number"
        ? valA - valB
        : String(valA).localeCompare(String(valB), undefined, { sensitivity: "base", numeric: true });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [jobs, sortField, sortDir]);

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
      if (j.run_type === "campaign") {
        await api.stopCampaign(j.application_id, j.run_id);
      } else if (j.run_type === "sast") {
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
        } else if (j.job_type === "Validation") {
          await api.stopValidation(j.run_id);
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
            <thead>
              <tr>
                <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => toggleSort("run_name")}>Run {sortArrow("run_name")}</th>
                <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => toggleSort("site_name")}>App / API / SAST {sortArrow("site_name")}</th>
                <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => toggleSort("job_type")}>Job {sortArrow("job_type")}</th>
                <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => toggleSort("status")}>Status {sortArrow("status")}</th>
                <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => toggleSort("pages_done")}>Progress {sortArrow("pages_done")}</th>
                <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => toggleSort("findings_count")}>Findings {sortArrow("findings_count")}</th>
                <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => toggleSort("started_at")}>Started {sortArrow("started_at")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>{sortedJobs.map(j => {
              const key = `${j.job_type}-${j.run_id}`;
              const isStopping = !!stopping[key];
              const runLink = j.run_type === "campaign"
                ? `#/applications/${j.application_id}/campaigns/${j.run_id}`
                : j.run_type === "sast"
                  ? `#/sast-runs/${j.run_id}/progress`
                  : j.run_type === "api"
                    ? `#/api-runs/${j.run_id}/status`
                    : `#/runs/${j.run_id}`;
              return <tr key={key}>
                <td>
                  <a href={runLink} style={{
                    fontWeight: 600
                  }}>{j.run_name}</a>
                  {j.current_url && <div className="url" style={{
                    marginTop: 3
                  }}>{truncUrl(j.current_url, 54)}</div>}
                </td>
                <td><a href={activeJobScopeLink(j)}>{activeJobScopeName(j)}</a></td>
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
                    <button className="btn secondary sm" onClick={() => nav(runLink)}>Open</button>
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
