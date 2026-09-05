import * as sastRunsApi from "../../shared/api/sastRuns.js";
import * as settingsApi from "../../shared/api/settings.js";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";

import { nav } from "../../shared/navigation/router.js";
import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";
import { EmptyState } from "../../shared/ui/EmptyState.jsx";
import { PageHeader } from "../../shared/ui/PageHeader.jsx";
import { usePolling } from "../../shared/hooks/usePolling.js";

export function SastRunsListPage() {
  const [runs, setRuns] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
  const importInputRef = useRef(null);
  const [sortField, setSortField] = useState("started_at");
  const [sortDir, setSortDir] = useState("desc");

  const loadRuns = useCallback(async () => {
    try {
      const r = await sastRunsApi.listAllSastRuns();
      setRuns(r);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }, []);

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
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
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

  const sortedRuns = useMemo(() => {
    if (!runs) return [];
    return [...runs].sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (sortField === "leads_count") {
        valA = a.leads_count || 0;
        valB = b.leads_count || 0;
      } else if (sortField === "linked_scan") {
        valA = a.triggered_by_run_id ? `API #${a.triggered_by_run_id}` : a.source_filename || "";
        valB = b.triggered_by_run_id ? `API #${b.triggered_by_run_id}` : b.source_filename || "";
      } else if (sortField === "started_at") {
        valA = a.started_at ? new Date(a.started_at).getTime() : 0;
        valB = b.started_at ? new Date(b.started_at).getTime() : 0;
      }

      if (valA == null) valA = "";
      if (valB == null) valB = "";

      let cmp =
        typeof valA === "number" && typeof valB === "number"
          ? valA - valB
          : String(valA).localeCompare(String(valB), undefined, {
              sensitivity: "base",
              numeric: true,
            });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [runs, sortField, sortDir]);

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
              className="btn ghost sm"
              disabled={importing}
              onClick={() => importInputRef.current?.click()}
            >
              {importing ? "Importing…" : "Import SAST Run"}
            </button>
            <button className="btn primary sm" onClick={() => nav("#/sast-runs/new")}>
              New SAST Scan
            </button>
          </>
        }
      />
      <div className="content scroll-content">
        {error && (
          <div
            className="alert error"
            style={{
              marginBottom: 16,
            }}
          >
            {error}
          </div>
        )}
        {runs === null && <div className="subtle">Loading…</div>}
        {runs !== null && runs.length === 0 && (
          <EmptyState
            icon="🔍"
            title="No SAST scans yet"
            sub={
              'Click "New SAST Scan" to upload a source ZIP and analyse it. Leads can then be imported into a web or API test run.'
            }
          />
        )}
        {runs && runs.length > 0 && (
          <div className="table-wrap sast-runs-list-table-wrap">
            <table>
              <colgroup>
                <col
                  style={{
                    width: "24%",
                  }}
                />
                <col
                  style={{
                    width: "12%",
                  }}
                />
                <col
                  style={{
                    width: "10%",
                  }}
                />
                <col
                  style={{
                    width: "18%",
                  }}
                />
                <col
                  style={{
                    width: "18%",
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
                    onClick={() => toggleSort("leads_count")}
                  >
                    Leads {sortArrow("leads_count")}
                  </th>
                  <th
                    style={{ cursor: "pointer", userSelect: "none" }}
                    onClick={() => toggleSort("linked_scan")}
                  >
                    Linked scan {sortArrow("linked_scan")}
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
                {sortedRuns.map((r) => (
                  <tr key={r.id}>
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
                    </td>
                    <td>
                      <StatusBadge status={r.status} />
                    </td>
                    <td>{r.leads_count}</td>
                    <td>
                      {r.triggered_by_run_id ? (
                        <a href={`#/api-runs/${r.triggered_by_run_id}/status`}>
                          API run #{r.triggered_by_run_id}
                        </a>
                      ) : (
                        <span className="subtle">{r.source_filename || "standalone"}</span>
                      )}
                    </td>
                    <td>
                      {r.started_at ? (
                        new Date(r.started_at).toLocaleString()
                      ) : (
                        <span className="subtle">—</span>
                      )}
                    </td>
                    <td>
                      <a className="btn ghost sm" href={`#/sast-runs/${r.id}/progress`}>
                        View →
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
