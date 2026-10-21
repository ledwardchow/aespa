import { fmtDate } from "../../shared/lib/dates.js";
import { IconPlus } from "../../shared/ui/Icons.jsx";
import { useBenchmarkLinks } from "../../shared/hooks/useBenchmarkLinks.js";
import { BenchmarkBadge } from "../../shared/ui/BenchmarkBadge.jsx";
import * as sastRunsApi from "../../shared/api/sastRuns.js";
import * as settingsApi from "../../shared/api/settings.js";

import { useState, useEffect, useRef, useCallback } from "react";

import { nav } from "../../shared/navigation/router.js";
import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";
import { EmptyState } from "../../shared/ui/EmptyState.jsx";
import { NavigationRow } from "../../shared/ui/NavigationRow.jsx";
import { PageHeader } from "../../shared/ui/PageHeader.jsx";
import { usePolling } from "../../shared/hooks/usePolling.js";
import { PageError } from "../../shared/ui/Notice.jsx";

export function SastRunsListPage() {
  const [runs, setRuns] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [profiles, setProfiles] = useState([]);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
  const importInputRef = useRef(null);
  const [sortField, setSortField] = useState("started_at");
  const [sortDir, setSortDir] = useState("desc");
  const benchmarkLinks = useBenchmarkLinks();
  const [deletingRunId, setDeletingRunId] = useState(null);

  const loadRuns = useCallback(
    async (signal) => {
      try {
        const result = await sastRunsApi.listSastRunsPage(
          { page, pageSize, sortField, sortDir },
          signal,
        );
        if (signal?.aborted) return;
        setRuns(result.items);
        setTotal(result.total);
        if (result.total && page > Math.ceil(result.total / pageSize)) {
          setPage(Math.ceil(result.total / pageSize));
        }
        setError(null);
      } catch (e) {
        if (!signal?.aborted) setError(e.message);
      }
    },
    [page, pageSize, sortField, sortDir],
  );

  usePolling(loadRuns, { intervalMs: 3000 });

  useEffect(() => {
    settingsApi
      .listLLMProfiles()
      .then((p) => setProfiles(p || []))
      .catch((e) => setError(e.message));
  }, []);

  const onImport = async (event) => {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    if (!file) return;
    setImporting(true);
    setError(null);
    try {
      const restored = await sastRunsApi.importSastRun(await file.text());
      await loadRuns();
      nav(`#/sast-runs/${restored.id}/coverage`);
    } catch (e) {
      setError(e.message);
    } finally {
      setImporting(false);
    }
  };

  const toggleSort = (field) => {
    setPage(1);
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const onDelete = async (run) => {
    if (!confirm(`Delete "${run.name}" and all its leads?`)) return;
    setDeletingRunId(run.id);
    setError(null);
    try {
      await sastRunsApi.deleteSastRun(run.id);
      await loadRuns();
    } catch (e) {
      setError(e.message);
    } finally {
      setDeletingRunId(null);
    }
  };

  const sortArrow = (field) => {
    if (sortField !== field) return null;
    return (
      <span style={{ marginLeft: "4px", fontSize: "10px", opacity: 0.85 }}>
        {sortDir === "asc" ? "▲" : "▼"}
      </span>
    );
  };

  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  return (
    <>
      <PageHeader
        title="SAST Scans"
        actions={
          <>
            <input
              ref={importInputRef}
              type="file"
              accept=".json,.aespa-sast.json"
              style={{ display: "none" }}
              onChange={onImport}
            />
            <button
              className="btn secondary"
              disabled={importing}
              onClick={() => importInputRef.current?.click()}
            >
              {importing ? "Importing…" : "Import SAST scan"}
            </button>
            <button className="btn" onClick={() => nav("#/sast-runs/new")}>
              <IconPlus /> New SAST scan
            </button>
          </>
        }
      />
      <div className="content scroll-content">
        <PageError error={error} inline={!runs} onDismiss={() => setError(null)} />
        {runs === null && <div className="subtle">Loading…</div>}
        {runs !== null && total === 0 && (
          <EmptyState
            icon="🔍"
            title="No SAST scans yet"
            sub={
              'Click "New SAST Scan" to upload a source ZIP and analyse it. Leads can then be imported into a web or API test run.'
            }
          />
        )}
        {runs && total > 0 && (
          <>
            <div className="table-wrap sast-runs-list-table-wrap">
              <table>
                <colgroup>
                  <col
                    style={{
                      width: "30%",
                    }}
                  />
                  <col
                    style={{
                      width: "13%",
                    }}
                  />
                  <col
                    style={{
                      width: "9%",
                    }}
                  />
                  <col style={{ width: "8%" }} />
                  <col
                    style={{
                      width: "22%",
                    }}
                  />
                  <col />
                </colgroup>
                <thead>
                  <tr>
                    <th
                      style={{ cursor: "pointer", userSelect: "none" }}
                      onClick={() => toggleSort("name")}
                    >
                      Name {sortArrow("name")}
                    </th>
                    <th
                      style={{ cursor: "pointer", userSelect: "none" }}
                      onClick={() => toggleSort("status")}
                    >
                      Status {sortArrow("status")}
                    </th>
                    <th
                      style={{ cursor: "pointer", userSelect: "none" }}
                      onClick={() => toggleSort("analysis_mode")}
                    >
                      Analysis {sortArrow("analysis_mode")}
                    </th>
                    <th
                      style={{ cursor: "pointer", userSelect: "none" }}
                      onClick={() => toggleSort("leads_count")}
                    >
                      Leads {sortArrow("leads_count")}
                    </th>
                    <th
                      style={{ cursor: "pointer", userSelect: "none" }}
                      onClick={() => toggleSort("started_at")}
                    >
                      Started {sortArrow("started_at")}
                    </th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <NavigationRow
                      key={r.id}
                      href={`#/sast-runs/${r.id}/progress`}
                      label={`Open ${r.name}`}
                    >
                      <td>
                        <a
                          href={`#/sast-runs/${r.id}/progress`}
                          style={{
                            fontWeight: 600,
                          }}
                        >
                          {r.name}
                        </a>
                        {r.llm_profile_id && (
                          <div
                            style={{
                              fontSize: 11,
                              color: "var(--muted)",
                              marginTop: 2,
                            }}
                          >
                            {
                              (
                                profiles.find((p) => p.id === r.llm_profile_id) || {
                                  name: "Profile #" + r.llm_profile_id,
                                }
                              ).name
                            }
                          </div>
                        )}
                        <BenchmarkBadge href={benchmarkLinks[`sast:${r.id}`]} />
                      </td>
                      <td>
                        <StatusBadge status={r.status} />
                      </td>
                      <td>{r.analysis_mode === "light" ? "Light" : "Deep"}</td>
                      <td>{r.leads_count}</td>
                      <td>
                        {r.started_at ? fmtDate(r.started_at) : <span className="subtle">—</span>}
                      </td>
                      <td>
                        <div className="row" style={{ justifyContent: "flex-end" }}>
                          <a className="btn secondary sm" href={`#/sast-runs/${r.id}/progress`}>
                            Open
                          </a>
                          <button
                            type="button"
                            className="btn danger-outline sm"
                            disabled={deletingRunId === r.id}
                            onClick={() => onDelete(r)}
                          >
                            {deletingRunId === r.id ? "Deleting…" : "Delete"}
                          </button>
                        </div>
                      </td>
                    </NavigationRow>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="sast-runs-pager">
              <span aria-live="polite">
                {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
              </span>
              <label>
                Scans per page
                <select
                  value={pageSize}
                  onChange={(event) => {
                    setPageSize(Number(event.target.value));
                    setPage(1);
                  }}
                >
                  {[10, 25, 50, 100].map((size) => (
                    <option key={size} value={size}>
                      {size}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="btn secondary sm"
                type="button"
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </button>
              <span>
                Page {page} of {pageCount}
              </span>
              <button
                className="btn secondary sm"
                type="button"
                disabled={page >= pageCount}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
