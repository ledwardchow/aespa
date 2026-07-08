import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";
import { IconPlus } from "../../components/Icons";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";

export function ApiCollectionsList() {
  const [collections, setCollections] = useState(null);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
  const importRef = useRef(null);
  const load = useCallback(async () => {
    try {
      setCollections(await api.listApiCollections());
    } catch (e) {
      setError(e.message);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  const onDelete = async c => {
    if (!confirm(`Delete "${c.name}"? This also removes all uploaded docs, endpoints and test runs.`)) return;
    try {
      await api.deleteApiCollection(c.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };
  const onExport = c => {
    window.location.href = `/api/api-collections/${c.id}/export`;
  };
  const onImportFile = async e => {
    const file = e.target.files[0];
    if (!file) return;
    e.target.value = "";
    setImporting(true);
    setError(null);
    try {
      await api.importApiCollection(await file.text());
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };
  return <>
    <PageHeader title="APIs" actions={<>
        <input ref={importRef} type="file" accept=".json" style={{
          display: "none"
        }} onChange={onImportFile} />
        <button className="btn secondary" onClick={() => importRef.current.click()} disabled={importing}>{importing ? "Importing…" : "Import API"}</button>
        <button className="btn" onClick={() => nav("#/apis/new")}><IconPlus /> New API collection</button>
      </>} />
    <div className="content scroll-content">
      {error && <div className="alert error" style={{
        marginBottom: 16
      }}>{error}</div>}
      {collections === null && <div className="subtle">Loading…</div>}
      {collections !== null && collections.length === 0 && <EmptyState
        title="No API collections yet"
        sub="Create a collection, upload API docs, and run structured API security tests."
        action={<button className="btn" onClick={() => nav("#/apis/new")}><IconPlus /> New API collection</button>} />}
      {collections && collections.length > 0 && <div className="table-wrap">
          <table>
            <colgroup>
              <col style={{
              width: "20%"
            }} /><col style={{
              width: "38%"
            }} /><col style={{
              width: "10%"
            }} /><col style={{
              width: "10%"
            }} /><col style={{
              width: "22%"
            }} />
            </colgroup>
            <thead><tr><th>Name</th><th>Base URL</th><th>Endpoints</th><th>Files</th><th></th></tr></thead>
            <tbody>{collections.map(c => <tr key={c.id}>
                <td><a href={`#/apis/${c.id}`} style={{
                  fontWeight: 600
                }}>{c.name}</a></td>
                <td className="url">{c.base_url}</td>
                <td>{c.endpoint_count > 0 ? c.endpoint_count : <span className="subtle">—</span>}</td>
                <td>{c.document_count > 0 ? c.document_count : <span className="subtle">—</span>}</td>
                <td>
                  <div className="row" style={{
                  justifyContent: "flex-end"
                }}>
                    <button className="btn secondary sm" onClick={() => nav(`#/apis/${c.id}`)}>Open</button>
                    <button className="btn secondary sm" onClick={() => onExport(c)}>Export</button>
                    <button className="btn danger-outline sm" onClick={() => onDelete(c)}>Delete</button>
                  </div>
                </td>
              </tr>)}
            </tbody>
          </table>
        </div>}
    </div>
  </>;
}
