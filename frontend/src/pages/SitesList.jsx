import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { nav } from "../lib/router";
import { api } from "../lib/api";
import { IconPlus } from "../components/Icons";
import { EmptyState } from "../components/EmptyState";

// ── Sites list ────────────────────────────────────────────────────────────────

export function SitesList() {
  const [sites, setSites] = useState(null);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
  const [sortField, setSortField] = useState("name");
  const [sortDir, setSortDir] = useState("asc");
  const importRef = useRef(null);

  const load = useCallback(async () => {
    try {
      setSites(await api.listSites());
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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

  const sortedSites = useMemo(() => {
    if (!sites) return [];
    return [...sites].sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (sortField === "requires_auth") {
        valA = a.requires_auth ? 1 : 0;
        valB = b.requires_auth ? 1 : 0;
      } else if (sortField === "credential_count") {
        valA = a.credential_count || 0;
        valB = b.credential_count || 0;
      }

      if (valA == null) valA = "";
      if (valB == null) valB = "";

      let cmp = typeof valA === "number" && typeof valB === "number"
        ? valA - valB
        : String(valA).localeCompare(String(valB), undefined, { sensitivity: "base", numeric: true });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [sites, sortField, sortDir]);

  const onDelete = async s => {
    if (!confirm(`Delete "${s.name}"? This also removes all test runs and credentials.`)) return;
    try {
      await api.deleteSite(s.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const onExport = s => {
    window.location.href = `/api/sites/${s.id}/export`;
  };

  const onImportFile = async e => {
    const file = e.target.files[0];
    if (!file) return;
    e.target.value = "";
    setImporting(true);
    setError(null);
    try {
      const text = await file.text();
      await api.importSite(text);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  return <>
    <div className="topbar">
      <div className="topbar-title">Sites</div>
      <div className="topbar-actions">
        <input ref={importRef} type="file" accept=".json" style={{
          display: "none"
        }} onChange={onImportFile} />
        <button className="btn secondary" onClick={() => importRef.current.click()} disabled={importing}>{importing ? "Importing…" : "Import site"}</button>
        <button className="btn" onClick={() => nav("#/sites/new")}><IconPlus /> New site</button>
      </div>
    </div>
    <div className="content scroll-content">
      {error && <div className="alert error" style={{
        marginBottom: 16
      }}>{error}</div>}
      {sites === null && <div className="subtle">Loading…</div>}
      {sites !== null && sites.length === 0 && <EmptyState
        title="No sites configured"
        sub="Add a target site to begin setting up your pentest scope."
        action={<button className="btn" onClick={() => nav("#/sites/new")}><IconPlus /> New site</button>} />}
      {sites && sites.length > 0 && <div className="table-wrap">
          <table>
            <colgroup>
              <col style={{
              width: "18%"
            }} /><col style={{
              width: "42%"
            }} /><col style={{
              width: "10%"
            }} /><col style={{
              width: "10%"
            }} /><col style={{
              width: "20%"
            }} />
            </colgroup>
            <thead>
              <tr>
                <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => toggleSort("name")}>Name {sortArrow("name")}</th>
                <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => toggleSort("base_url")}>Base URL {sortArrow("base_url")}</th>
                <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => toggleSort("requires_auth")}>Auth {sortArrow("requires_auth")}</th>
                <th style={{ cursor: "pointer", userSelect: "none" }} onClick={() => toggleSort("credential_count")}>Credentials {sortArrow("credential_count")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>{sortedSites.map(s => <tr key={s.id}>
                <td><a href={`#/sites/${s.id}`} style={{
                  fontWeight: 600
                }}>{s.name}</a></td>
                <td className="url">{s.base_url}</td>
                <td>{s.requires_auth ? <span className="badge ok">required</span> : <span className="badge neutral">none</span>}</td>
                <td>{s.credential_count > 0 ? s.credential_count : <span className="subtle">—</span>}</td>
                <td>
                  <div className="row" style={{
                  justifyContent: "flex-end"
                }}>
                    <button className="btn secondary sm" onClick={() => nav(`#/sites/${s.id}`)}>Open</button>
                    <button className="btn secondary sm" onClick={() => onExport(s)}>Export</button>
                    <button className="btn danger-outline sm" onClick={() => onDelete(s)}>Delete</button>
                  </div>
                </td>
              </tr>)}
            </tbody>
          </table>
        </div>}
    </div>
  </>;
}