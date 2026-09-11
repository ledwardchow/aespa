import * as settingsApi from "../../shared/api/settings.js";
import * as sitesApi from "../../shared/api/sites.js";
import * as webRunsApi from "../../shared/api/webRuns.js";

import { useState, useEffect, useCallback, useMemo } from "react";

import { nav } from "../../shared/navigation/router.js";

import { fmtDate } from "../../shared/lib/dates.js";
import { IconPlus } from "../../shared/ui/Icons.jsx";
import { EmptyState } from "../../shared/ui/EmptyState.jsx";
import { PageHeader, Crumb, Sep } from "../../shared/ui/PageHeader.jsx";

import { workflowBadge } from "../../shared/runs/presentation.jsx";

export function SiteDetail({ siteId }) {
  const [site, setSite] = useState(null);
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState(null);
  const [editingRun, setEditingRun] = useState(null); // run object being edited
  const [editForm, setEditForm] = useState({});
  const [editProfiles, setEditProfiles] = useState([]);
  const [editSaving, setEditSaving] = useState(false);
  const [sortField, setSortField] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc");

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

      if (sortField === "pages_discovered") {
        valA = a.pages_discovered || 0;
        valB = b.pages_discovered || 0;
      } else if (sortField === "created_at") {
        valA = a.created_at ? new Date(a.created_at).getTime() : 0;
        valB = b.created_at ? new Date(b.created_at).getTime() : 0;
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
  const load = useCallback(async () => {
    try {
      const [s, r, p] = await Promise.all([
        sitesApi.getSite(siteId),
        sitesApi.listRuns(siteId),
        settingsApi.listLLMProfiles(),
      ]);
      setSite(s);
      setRuns(r);
      setEditProfiles(p || []);
    } catch (e) {
      setError(e.message);
    }
  }, [siteId]);
  useEffect(() => {
    load();
  }, [load]);
  const openEdit = (run) => {
    setEditForm({
      max_depth: run.max_depth,
      max_pages: run.max_pages,
      crawler_mode: run.crawler_mode || "url",
      llm_profile_id: run.llm_profile_id || "",
    });
    setEditingRun(run);
  };
  const saveEdit = async () => {
    setEditSaving(true);
    try {
      const updated = await webRunsApi.updateRun(editingRun.id, {
        max_depth: Number(editForm.max_depth),
        max_pages: Number(editForm.max_pages),
        crawler_mode: editForm.crawler_mode,
        llm_profile_id: editForm.llm_profile_id ? Number(editForm.llm_profile_id) : null,
      });
      setRuns((rs) => rs.map((r) => (r.id === updated.id ? updated : r)));
      setEditingRun(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setEditSaving(false);
    }
  };
  const deleteRun = async (run) => {
    if (!confirm(`Delete run "${run.name}"?`)) return;
    try {
      await webRunsApi.deleteRun(run.id);
      setRuns((r) => r.filter((x) => x.id !== run.id));
    } catch (e) {
      setError(e.message);
    }
  };
  return (
    <>
      <PageHeader
        title={
          <>
            <Crumb href="#/">Sites</Crumb>
            <Sep />
            {site ? site.name : "…"}
          </>
        }
        actions={
          <>
            {site && (
              <button className="btn secondary" onClick={() => nav(`#/sites/${siteId}/edit`)}>
                Edit site
              </button>
            )}
            <button className="btn" onClick={() => nav(`#/sites/${siteId}/runs/new`)}>
              <IconPlus /> New run
            </button>
          </>
        }
      />
      <div className="content scroll-content stack">
        {error && <div className="alert error">{error}</div>}

        {editingRun && (
          <div
            className="card"
            style={{
              padding: "20px 24px",
              border: "1px solid var(--accent)",
              marginBottom: 8,
            }}
          >
            <div
              style={{
                fontWeight: 700,
                marginBottom: 14,
              }}
            >
              Edit run: {editingRun.name}
            </div>
            <div
              className="two-col"
              style={{
                gap: 12,
                marginBottom: 12,
              }}
            >
              <div
                className="field"
                style={{
                  margin: 0,
                }}
              >
                <label>Max depth</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={editForm.max_depth}
                  onInput={(e) =>
                    setEditForm((f) => ({
                      ...f,
                      max_depth: e.target.value,
                    }))
                  }
                  style={{
                    width: 80,
                  }}
                />
              </div>
              <div className="field" style={{ margin: 0 }}>
                <label>Crawler mode</label>
                <select
                  className="select"
                  value={editForm.crawler_mode}
                  onChange={(e) => setEditForm((f) => ({ ...f, crawler_mode: e.target.value }))}
                >
                  <option value="url">URL</option>
                  <option value="interactive">Interactive SPA</option>
                </select>
              </div>
              <div
                className="field"
                style={{
                  margin: 0,
                }}
              >
                <label>Max pages</label>
                <input
                  type="number"
                  min="5"
                  max="500"
                  value={editForm.max_pages}
                  onInput={(e) =>
                    setEditForm((f) => ({
                      ...f,
                      max_pages: e.target.value,
                    }))
                  }
                  style={{
                    width: 90,
                  }}
                />
              </div>
            </div>
            <div
              className="field"
              style={{
                marginBottom: 14,
              }}
            >
              <label>
                LLM profile{" "}
                <span className="field-optional">
                  (leave blank to use the globally active profile)
                </span>
              </label>
              <select
                className="select"
                value={editForm.llm_profile_id || ""}
                onChange={(e) =>
                  setEditForm((f) => ({
                    ...f,
                    llm_profile_id: e.target.value,
                  }))
                }
              >
                <option value="">— Use global active profile —</option>
                {editProfiles.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div
              className="row"
              style={{
                gap: 8,
              }}
            >
              <button className="btn sm" onClick={saveEdit} disabled={editSaving}>
                {editSaving ? "Saving…" : "Save"}
              </button>
              <button className="btn ghost sm" onClick={() => setEditingRun(null)}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {site && (
          <div
            className="card"
            style={{
              padding: "16px 20px",
            }}
          >
            <div className="row spread">
              <div
                className="stack"
                style={{
                  gap: 4,
                }}
              >
                <div
                  style={{
                    fontSize: 13,
                    color: "var(--muted)",
                  }}
                >
                  Base URL
                </div>
                <div
                  className="mono"
                  style={{
                    fontSize: 13,
                  }}
                >
                  {site.base_url}
                </div>
              </div>
              <div
                className="row"
                style={{
                  gap: 16,
                }}
              >
                {site.requires_auth ? (
                  <span className="badge ok">auth required</span>
                ) : (
                  <span className="badge neutral">no auth</span>
                )}
                <span className="subtle">
                  {site.credentials.length} credential{site.credentials.length !== 1 ? "s" : ""}
                </span>
              </div>
            </div>
            {site.notes && (
              <div
                style={{
                  marginTop: 10,
                  fontSize: 13,
                  color: "var(--muted)",
                }}
              >
                {site.notes}
              </div>
            )}
            {site.scan_guidance && (
              <div
                style={{
                  marginTop: 8,
                  fontSize: 13,
                  color: "var(--muted)",
                }}
              >
                <strong>Test Lead guidance:</strong> {site.scan_guidance}
              </div>
            )}
            {site.requires_auth && site.credentials.length > 0 && (
              <>
                <div className="site-credentials-list">
                  {site.credentials.map((c) => (
                    <div key={c.id} className="site-credential-row">
                      <div>
                        <div className="site-credential-name">
                          {c.label ||
                            (c.login_fields?.[0]?.key === "username" ? c.username : "Test account")}
                        </div>
                        <div className="site-credential-user">
                          {(c.login_fields || []).map((field) => field.label).join(" + ") ||
                            "Username + Password"}
                        </div>
                      </div>
                      <div className="site-credential-login mono">
                        {c.login_url || site.login_url || "No login URL"}
                      </div>
                    </div>
                  ))}
                </div>
                {site.credentials.some((c) => c.auth_mode === "guided") && (
                  <div
                    style={{
                      marginTop: 8,
                      padding: "8px 12px",
                      background: "var(--surface-2,#2a2a2a)",
                      border: "1px solid var(--warn,#f59e0b)",
                      borderRadius: 5,
                      fontSize: 12,
                      color: "var(--warn,#f59e0b)",
                    }}
                  >
                    ⚠️ This site is configured with interactive browser login credentials, which
                    only works if you're running this scanner on your local machine with a GUI. It
                    will not function if the scanner is installed on a headless host (i.e. server).
                  </div>
                )}
              </>
            )}
          </div>
        )}

        <div>
          <div
            className="row spread"
            style={{
              marginBottom: 12,
            }}
          >
            <div
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: "var(--muted)",
                textTransform: "uppercase",
                letterSpacing: "0.6px",
              }}
            >
              Test Runs
            </div>
          </div>
          {runs === null && <div className="subtle">Loading…</div>}
          {runs !== null && runs.length === 0 && (
            <EmptyState
              icon={null}
              style={{ padding: "32px" }}
              title="No test runs yet"
              sub="Create a new run to start crawling this site."
              action={
                <button className="btn" onClick={() => nav(`#/sites/${siteId}/runs/new`)}>
                  <IconPlus /> New run
                </button>
              }
            />
          )}
          {runs && runs.length > 0 && (
            <div className="table-wrap">
              <table>
                <colgroup>
                  <col
                    style={{
                      width: "35%",
                    }}
                  />
                  <col
                    style={{
                      width: "18%",
                    }}
                  />
                  <col
                    style={{
                      width: "10%",
                    }}
                  />
                  <col
                    style={{
                      width: "16%",
                    }}
                  />
                  <col
                    style={{
                      width: "21%",
                    }}
                  />
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
                      onClick={() => toggleSort("pages_discovered")}
                    >
                      Pages {sortArrow("pages_discovered")}
                    </th>
                    <th
                      style={{ cursor: "pointer", userSelect: "none" }}
                      onClick={() => toggleSort("created_at")}
                    >
                      Created {sortArrow("created_at")}
                    </th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRuns.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <strong>{r.name}</strong>
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
                                editProfiles.find((p) => p.id === r.llm_profile_id) || {
                                  name: "Profile #" + r.llm_profile_id,
                                }
                              ).name
                            }
                          </div>
                        )}
                      </td>
                      <td>{workflowBadge(r)}</td>
                      <td>{r.pages_discovered}</td>
                      <td className="subtle">{fmtDate(r.created_at)}</td>
                      <td>
                        <div
                          className="row"
                          style={{
                            justifyContent: "flex-end",
                          }}
                        >
                          <button
                            className="btn secondary sm"
                            onClick={() => nav(`#/runs/${r.id}`)}
                          >
                            Open
                          </button>
                          <button className="btn secondary sm" onClick={() => openEdit(r)}>
                            Edit
                          </button>
                          <button className="btn danger-outline sm" onClick={() => deleteRun(r)}>
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
