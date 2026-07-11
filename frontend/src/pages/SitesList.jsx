import { useState, useEffect, useRef, useCallback } from "react";
import { nav } from "../lib/router";
import { api } from "../lib/api";
import { IconPlus } from "../components/Icons";
import { EmptyState } from "../components/EmptyState";

// ── Sites list ────────────────────────────────────────────────────────────────

export function SitesList() {
  const [sites, setSites] = useState(null);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
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
            <thead><tr><th>Name</th><th>Base URL</th><th>Auth</th><th>Credentials</th><th></th></tr></thead>
            <tbody>{sites.map(s => <tr key={s.id}>
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