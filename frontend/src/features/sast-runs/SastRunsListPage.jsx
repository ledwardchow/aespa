import { fmtDate } from "../../shared/lib/dates.js";
import { IconPlus } from "../../shared/ui/Icons.jsx";
import { useBenchmarkLinks } from "../../shared/hooks/useBenchmarkLinks.js";
import { BenchmarkBadge } from "../../shared/ui/BenchmarkBadge.jsx";
import * as sastRunsApi from "../../shared/api/sastRuns.js";
import * as settingsApi from "../../shared/api/settings.js";
import * as sitesApi from "../../shared/api/sites.js";
import * as apiCollectionsApi from "../../shared/api/apiCollections.js";

import { useState, useEffect, useRef, useCallback } from "react";

import { nav } from "../../shared/navigation/router.js";
import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";
import { EmptyState } from "../../shared/ui/EmptyState.jsx";
import { NavigationRow } from "../../shared/ui/NavigationRow.jsx";
import { PageHeader } from "../../shared/ui/PageHeader.jsx";
import { usePolling } from "../../shared/hooks/usePolling.js";
import { PageError } from "../../shared/ui/Notice.jsx";
import { Tabs } from "../../shared/ui/Tabs.tsx";

const ASSOCIATION_TABS = [
  { key: "site", label: "Site" },
  { key: "api", label: "API" },
  { key: "unassociated", label: "Unassociated" },
];

export function SastRunsListPage({ initialTab = "unassociated" }) {
  const [runs, setRuns] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [association, setAssociation] = useState(initialTab);
  const [targetFilter, setTargetFilter] = useState("");
  const [profiles, setProfiles] = useState([]);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
  const importInputRef = useRef(null);
  const [sortField, setSortField] = useState("started_at");
  const [sortDir, setSortDir] = useState("desc");
  const benchmarkLinks = useBenchmarkLinks();
  const [deletingRunId, setDeletingRunId] = useState(null);
  const [editingRun, setEditingRun] = useState(null);
  const [editName, setEditName] = useState("");
  const [editGroup, setEditGroup] = useState("");
  const [editTarget, setEditTarget] = useState("");
  const [sites, setSites] = useState([]);
  const [apiCollections, setApiCollections] = useState([]);
  const [savingEdit, setSavingEdit] = useState(false);
  const editNameRef = useRef(null);

  const loadRuns = useCallback(
    async (signal) => {
      try {
        const result = await sastRunsApi.listSastRunsPage(
          {
            page,
            pageSize,
            sortField,
            sortDir,
            association,
            ...(targetFilter ? { targetId: Number(targetFilter) } : {}),
          },
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
    [page, pageSize, sortField, sortDir, association, targetFilter],
  );

  usePolling(loadRuns, { intervalMs: 3000 });

  useEffect(() => {
    setAssociation(initialTab);
    setTargetFilter("");
    setPage(1);
    setRuns(null);
  }, [initialTab]);

  useEffect(() => {
    if (association === "site") {
      sitesApi
        .listSites()
        .then(setSites)
        .catch((e) => setError(e.message));
    } else if (association === "api") {
      apiCollectionsApi
        .listApiCollections()
        .then(setApiCollections)
        .catch((e) => setError(e.message));
    }
  }, [association]);

  useEffect(() => {
    settingsApi
      .listLLMProfiles()
      .then((p) => setProfiles(p || []))
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (editingRun) editNameRef.current?.focus();
  }, [editingRun]);

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

  const onEdit = async (run) => {
    setEditingRun(run);
    setEditName(run.name);
    setEditGroup(
      run.site_id
        ? "site"
        : run.associated_collection_id || (run.collection_id && !run.group_override)
          ? "api"
          : "",
    );
    setEditTarget(
      String(
        run.site_id ||
          run.associated_collection_id ||
          (!run.group_override && run.collection_id) ||
          "",
      ),
    );
    setError(null);
    try {
      const [siteItems, apiItems] = await Promise.all([
        sitesApi.listSites(),
        apiCollectionsApi.listApiCollections(),
      ]);
      setSites(siteItems || []);
      setApiCollections(apiItems || []);
    } catch (e) {
      setError(e.message);
    }
  };

  const onSaveEdit = async (event) => {
    event.preventDefault();
    if (!editName.trim()) {
      setError("Enter a scan name");
      return;
    }
    if (editGroup && !editTarget) {
      setError(`Choose a ${editGroup === "site" ? "Site" : "API"}`);
      return;
    }
    setSavingEdit(true);
    setError(null);
    try {
      await sastRunsApi.updateSastRun(editingRun.id, {
        name: editName.trim(),
        site_id: editGroup === "site" ? Number(editTarget) : null,
        associated_collection_id: editGroup === "api" ? Number(editTarget) : null,
      });
      setEditingRun(null);
      await loadRuns();
    } catch (e) {
      setError(e.message);
    } finally {
      setSavingEdit(false);
    }
  };

  const sortableHeader = (label, field) => {
    const active = sortField === field;
    return (
      <th aria-sort={active ? (sortDir === "asc" ? "ascending" : "descending") : "none"}>
        <button
          className={`sast-sort-button${active ? " active" : ""}`}
          type="button"
          onClick={() => toggleSort(field)}
        >
          {label}
          <span className="sast-sort-indicator" aria-hidden="true">
            {active ? (sortDir === "asc" ? "▲" : "▼") : "↕"}
          </span>
        </button>
      </th>
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
      <Tabs
        label="SAST scan groups"
        tabs={ASSOCIATION_TABS}
        value={association}
        onChange={(key) => {
          setAssociation(key);
          setTargetFilter("");
          setPage(1);
          setRuns(null);
          nav(`#/sast-runs/${key}`);
        }}
      />
      <div className="content scroll-content">
        <PageError error={error} inline={!runs} onDismiss={() => setError(null)} />
        {association !== "unassociated" && (
          <div className="sast-runs-filter">
            <label htmlFor="sast-runs-target-filter">
              Filter by {association === "site" ? "Site" : "API"}
            </label>
            <select
              id="sast-runs-target-filter"
              className="select"
              value={targetFilter}
              onChange={(event) => {
                setTargetFilter(event.target.value);
                setPage(1);
                setRuns(null);
              }}
            >
              <option value="">All {association === "site" ? "Sites" : "APIs"}</option>
              {(association === "site" ? sites : apiCollections).map((target) => (
                <option key={target.id} value={target.id}>
                  {target.name}
                </option>
              ))}
            </select>
          </div>
        )}
        {editingRun && (
          <form
            className="card"
            style={{ maxWidth: 620, marginBottom: 16 }}
            onSubmit={onSaveEdit}
            aria-label="Edit SAST scan"
          >
            <div className="form-section-title">Edit SAST scan</div>
            <div className="field">
              <label htmlFor="sast-edit-name">Name</label>
              <input
                id="sast-edit-name"
                ref={editNameRef}
                value={editName}
                onChange={(event) => setEditName(event.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="sast-edit-group">Group</label>
              <select
                id="sast-edit-group"
                className="select"
                value={editGroup}
                onChange={(event) => {
                  setEditGroup(event.target.value);
                  setEditTarget("");
                }}
              >
                <option value="">Unassociated</option>
                <option value="site">Site</option>
                <option value="api">API</option>
              </select>
            </div>
            {editGroup && (
              <div className="field">
                <label htmlFor="sast-edit-target">{editGroup === "site" ? "Site" : "API"}</label>
                <select
                  id="sast-edit-target"
                  className="select"
                  value={editTarget}
                  onChange={(event) => setEditTarget(event.target.value)}
                  required
                >
                  <option value="">Choose {editGroup === "site" ? "Site" : "API"}</option>
                  {(editGroup === "site" ? sites : apiCollections).map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div className="row" style={{ gap: 8 }}>
              <button className="btn" type="submit" disabled={savingEdit}>
                {savingEdit ? "Saving…" : "Save changes"}
              </button>
              <button className="btn secondary" type="button" onClick={() => setEditingRun(null)}>
                Cancel
              </button>
            </div>
          </form>
        )}
        {runs === null && <div className="subtle">Loading…</div>}
        {runs !== null && total === 0 && (
          <EmptyState
            icon="🔍"
            title={
              targetFilter
                ? `No scans for this ${association === "site" ? "Site" : "API"}`
                : association === "unassociated"
                  ? "No unassociated SAST scans"
                  : `No ${association === "site" ? "Site" : "API"} SAST scans`
            }
            sub={
              targetFilter
                ? `Choose another ${association === "site" ? "Site" : "API"} or show all.`
                : association === "unassociated"
                  ? "Create a SAST scan without choosing a Site or API to list it here."
                  : `Create a SAST scan and choose a ${association === "site" ? "Site" : "API"} to list it here.`
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
                      width: association === "unassociated" ? "30%" : "24%",
                    }}
                  />
                  {association !== "unassociated" && <col style={{ width: "16%" }} />}
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
                    {sortableHeader("Name", "name")}
                    {association !== "unassociated" &&
                      sortableHeader(association === "site" ? "Site" : "API", "target")}
                    {sortableHeader("Status", "status")}
                    {sortableHeader("Analysis", "analysis_mode")}
                    {sortableHeader("Leads", "leads_count")}
                    {sortableHeader("Started", "started_at")}
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
                      {association !== "unassociated" && (
                        <td>
                          <a
                            href={
                              r.site_id
                                ? `#/sites/${r.site_id}`
                                : `#/apis/${r.associated_collection_id || r.collection_id}`
                            }
                          >
                            {r.associated_name ||
                              (r.site_id
                                ? `Site #${r.site_id}`
                                : `API #${r.associated_collection_id || r.collection_id}`)}
                          </a>
                        </td>
                      )}
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
                            className="btn secondary sm"
                            onClick={() => onEdit(r)}
                          >
                            Edit
                          </button>
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
