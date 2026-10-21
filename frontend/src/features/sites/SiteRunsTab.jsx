import * as settingsApi from "../../shared/api/settings.js";
import * as sitesApi from "../../shared/api/sites.js";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { useCallback, useEffect, useState } from "react";
import { useBenchmarkLinks } from "../../shared/hooks/useBenchmarkLinks.js";
import { fmtDate } from "../../shared/lib/dates.js";
import { nav } from "../../shared/navigation/router.js";
import { workflowBadge } from "../../shared/runs/presentation.jsx";
import { BenchmarkBadge } from "../../shared/ui/BenchmarkBadge.jsx";
import { EmptyState } from "../../shared/ui/EmptyState.jsx";
import { IconPlus } from "../../shared/ui/Icons.jsx";
import { NavigationRow } from "../../shared/ui/NavigationRow.jsx";
import { PageError } from "../../shared/ui/Notice.jsx";
import { RunListPager } from "../../shared/ui/RunListPager.jsx";

export function SiteRunsTab({ siteId }) {
  const benchmarkLinks = useBenchmarkLinks();
  const [runs, setRuns] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [error, setError] = useState(null);
  const [editingRun, setEditingRun] = useState(null); // run object being edited
  const [editForm, setEditForm] = useState({});
  const [editProfiles, setEditProfiles] = useState([]);
  const [editSaving, setEditSaving] = useState(false);
  const [sortField, setSortField] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc");

  const toggleSort = (field) => {
    setPage(1);
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

  const profileName = (run) =>
    run.llm_profile_id
      ? editProfiles.find((p) => p.id === run.llm_profile_id)?.name ||
        `Profile #${run.llm_profile_id}`
      : "—";
  const loadRuns = useCallback(
    async (signal) => {
      try {
        const result = await sitesApi.listSiteRunsPage(
          siteId,
          { page, pageSize, sortField, sortDir },
          signal,
        );
        if (signal?.aborted) return;
        if (result.total && page > Math.ceil(result.total / pageSize)) {
          setPage(Math.ceil(result.total / pageSize));
          return;
        }
        setRuns(result.items);
        setTotal(result.total);
        setError(null);
      } catch (e) {
        if (!signal?.aborted) setError(e.message);
      }
    },
    [siteId, page, pageSize, sortField, sortDir],
  );
  useEffect(() => {
    const controller = new AbortController();
    void loadRuns(controller.signal);
    return () => controller.abort();
  }, [loadRuns]);
  useEffect(() => {
    settingsApi
      .listLLMProfiles()
      .then((profiles) => setEditProfiles(profiles || []))
      .catch((e) => setError(e.message));
  }, []);
  const openEdit = (run) => {
    setEditForm({
      max_depth: run.max_depth,
      max_pages: run.max_pages,
      crawler_mode: run.crawler_mode || "url",
      page_selection: run.page_selection || "each_url",
      llm_profile_id: run.llm_profile_id || "",
      llm_budget_usd: run.llm_budget_usd ?? "",
    });
    setEditingRun(run);
  };
  const saveEdit = async () => {
    setEditSaving(true);
    try {
      await webRunsApi.updateRun(editingRun.id, {
        max_depth: Number(editForm.max_depth),
        max_pages: Number(editForm.max_pages),
        crawler_mode: editForm.crawler_mode,
        page_selection: editForm.page_selection,
        llm_profile_id: editForm.llm_profile_id ? Number(editForm.llm_profile_id) : null,
        llm_budget_usd: editForm.llm_budget_usd === "" ? null : Number(editForm.llm_budget_usd),
      });
      await loadRuns();
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
      await loadRuns();
    } catch (e) {
      setError(e.message);
    }
  };
  return (
    <div className="content scroll-content stack site-detail-content">
      <PageError error={error} inline={runs === null} onDismiss={() => setError(null)} />
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
                disabled={editingRun.crawl_started_once}
                onChange={(e) =>
                  setEditForm((f) => ({
                    ...f,
                    crawler_mode: e.target.value,
                    page_selection: "each_url",
                  }))
                }
              >
                <option value="url">URL</option>
                <option value="interactive">Interactive SPA</option>
              </select>
            </div>
            <div className="field" style={{ margin: 0 }}>
              <label>Page selection</label>
              <select
                className="select"
                value={editForm.page_selection}
                disabled={editingRun.crawl_started_once || editForm.crawler_mode !== "url"}
                onChange={(e) => setEditForm((f) => ({ ...f, page_selection: e.target.value }))}
              >
                <option value="each_url">Visit each URL</option>
                <option value="group_similar">Group similar pages</option>
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
          <div className="field" style={{ marginBottom: 14 }}>
            <label>
              LLM budget{" "}
              <span className="field-optional">
                (leave blank for no limit; pauses all LLM work when estimated spend reaches it)
              </span>
            </label>
            <div className="row" style={{ gap: 8 }}>
              <span>$</span>
              <input
                type="number"
                min="0.01"
                step="0.01"
                placeholder="No limit"
                value={editForm.llm_budget_usd}
                onInput={(e) => setEditForm((f) => ({ ...f, llm_budget_usd: e.target.value }))}
                style={{ width: 120 }}
              />
            </div>
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
      <div className="site-runs-section">
        {runs === null && <div className="subtle">Loading…</div>}
        {runs !== null && total === 0 && (
          <EmptyState
            icon={null}
            style={{ padding: "32px" }}
            title="No test runs yet"
            sub="Create a new run to start crawling this site."
            action={
              <button className="btn" onClick={() => nav(`#/sites/${siteId}/runs/new`)}>
                <IconPlus /> New test run
              </button>
            }
          />
        )}
        {runs && total > 0 && (
          <>
            <div className="table-wrap site-runs-table">
              <table>
                <colgroup>
                  <col style={{ width: "28%" }} />
                  <col style={{ width: "13%" }} />
                  <col style={{ width: "19%" }} />
                  <col style={{ width: "7%" }} />
                  <col style={{ width: "14%" }} />
                  <col style={{ width: "19%" }} />
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
                    <th>Profile</th>
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
                  {runs.map((r) => (
                    <NavigationRow key={r.id} href={`#/runs/${r.id}`} label={`Open ${r.name}`}>
                      <td>
                        <span className="run-name">
                          <a href={`#/runs/${r.id}`} style={{ fontWeight: 600 }}>
                            {r.name}
                          </a>
                          {r.coverage_mode === "deep" && <span className="badge deep">Deep</span>}
                          {r.coverage_mode === "team" && <span className="badge">Team</span>}
                          <BenchmarkBadge inline href={benchmarkLinks[`site:${r.id}`]} />
                        </span>
                      </td>
                      <td>{workflowBadge(r)}</td>
                      <td className="subtle site-run-profile" title={profileName(r)}>
                        {profileName(r)}
                      </td>
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
                    </NavigationRow>
                  ))}
                </tbody>
              </table>
            </div>
            <RunListPager
              page={page}
              pageSize={pageSize}
              total={total}
              onPageChange={setPage}
              onPageSizeChange={(size) => {
                setPageSize(size);
                setPage(1);
              }}
            />
          </>
        )}
      </div>
    </div>
  );
}
