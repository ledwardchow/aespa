import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";

export function fmtBytes(n) {
  if (n === null || n === undefined) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}
export function ApiFilesManager({
  collectionId
}) {
  const [collection, setCollection] = useState(null);
  const [docs, setDocs] = useState(null);
  const [endpoints, setEndpoints] = useState([]);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [reparseState, setReparseState] = useState({}); // docId → "running"|"done"|"failed"
  const [sastRuns, setSastRuns] = useState([]);
  const [sastBusy, setSastBusy] = useState(false);
  const fileRef = useRef(null);
  const load = useCallback(async () => {
    try {
      const [c, d, eps, sr] = await Promise.all([api.getApiCollection(collectionId), api.listApiDocuments(collectionId), api.listApiEndpoints(collectionId), api.listSastRuns(collectionId).catch(() => [])]);
      setCollection(c);
      setDocs(d);
      setEndpoints(eps);
      setSastRuns(sr);
    } catch (e) {
      setError(e.message);
    }
  }, [collectionId]);
  useEffect(() => {
    load();
  }, [load]);

  // Endpoint count keyed by source_doc_id
  const epCountByDoc = endpoints.reduce((acc, ep) => {
    if (ep.source_doc_id != null) acc[ep.source_doc_id] = (acc[ep.source_doc_id] || 0) + 1;
    return acc;
  }, {});
  const doUpload = async fileList => {
    const files = Array.from(fileList || []);
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      await api.uploadApiDocuments(collectionId, files);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };
  const onPick = e => {
    doUpload(e.target.files);
    e.target.value = "";
  };
  const onDrop = e => {
    e.preventDefault();
    setDragOver(false);
    doUpload(e.dataTransfer.files);
  };
  const onDelete = async doc => {
    if (!confirm(`Delete "${doc.filename}"?`)) return;
    try {
      await api.deleteApiDocument(collectionId, doc.id);
      setDocs(ds => ds.filter(d => d.id !== doc.id));
    } catch (e) {
      setError(e.message);
    }
  };
  const onReparse = async doc => {
    setReparseState(s => ({
      ...s,
      [doc.id]: "running"
    }));
    try {
      const updated = await api.parseApiDocument(collectionId, doc.id);
      setDocs(ds => ds.map(d => d.id === doc.id ? updated : d));
      // Refresh endpoint counts too
      const eps = await api.listApiEndpoints(collectionId);
      setEndpoints(eps);
      setReparseState(s => ({
        ...s,
        [doc.id]: updated.status === "parsed" ? "done" : "failed"
      }));
    } catch (e) {
      setError(e.message);
      setReparseState(s => ({
        ...s,
        [doc.id]: "failed"
      }));
    }
  };
  const statusCell = d => {
    const count = epCountByDoc[d.id];
    if (d.status === "failed") {
      const tip = d.error_message || "";
      return <span className="badge danger" title={tip} style={{
        cursor: "help"
      }}>failed</span>;
    }
    if (d.status === "parsed") {
      if (count != null && count > 0) {
        return <span><span className="badge ok">parsed</span> <span style={{
            fontSize: 11,
            color: "var(--muted)",
            marginLeft: 4
          }}>{count} endpoint{count === 1 ? "" : "s"}</span></span>;
      }
      if (d.doc_type === "credentials") {
        return <span className="badge ok" title="Credentials parsed — no endpoints from this type">parsed</span>;
      }
      return <span className="badge ok">parsed</span>;
    }
    return <span className="badge neutral">uploaded</span>;
  };
  return <>
    <div className="topbar">
      <div className="topbar-title">
        <a href="#/apis" style={{
          color: "var(--muted)",
          fontWeight: 400
        }}>APIs</a>
        <span className="breadcrumb-sep"> / </span>
        <a href={`#/apis/${collectionId}`} style={{
          color: "var(--muted)",
          fontWeight: 400
        }}>{collection ? collection.name : "…"}</a>
        <span className="breadcrumb-sep"> / </span>
        Files
      </div>
      <div className="topbar-actions">
        <input ref={fileRef} type="file" multiple style={{
          display: "none"
        }} onChange={onPick} />
        <button className="btn" onClick={() => fileRef.current.click()} disabled={uploading}>{uploading ? "Uploading…" : "Upload files"}</button>
      </div>
    </div>
    <div className="content scroll-content stack">
      {error && <div className="alert error">{error}</div>}
      <div className={"upload-dropzone" + (dragOver ? " dragover" : "")} onDragOver={e => {
        e.preventDefault();
        setDragOver(true);
      }} onDragLeave={() => setDragOver(false)} onDrop={onDrop} onClick={() => fileRef.current.click()} style={{
        border: "2px dashed var(--border)",
        borderRadius: 8,
        padding: "28px 16px",
        textAlign: "center",
        cursor: "pointer",
        color: dragOver ? "var(--accent)" : "var(--muted)",
        background: dragOver ? "var(--surface-2,#222)" : "transparent"
      }}>
        <div style={{
          fontSize: 13
        }}>{uploading ? "Uploading…" : "Drag & drop files here, or click to choose"}</div>
        <div className="subtle" style={{
          marginTop: 6,
          fontSize: 11
        }}>OpenAPI / Swagger, Postman, free text, credentials, or a source zip (max 25 MB each)</div>
      </div>
      {endpoints.length > 0 && <div className="alert" style={{
        background: "var(--surface-2,#1a2a1a)",
        borderColor: "var(--ok,#4caf50)",
        color: "var(--ok,#4caf50)",
        padding: "10px 14px",
        borderRadius: 6,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
      }}>
          <span>{endpoints.length} endpoint{endpoints.length === 1 ? "" : "s"} extracted</span>
          <a href={`#/apis/${collectionId}`} style={{
          color: "var(--ok,#4caf50)",
          fontWeight: 600,
          textDecoration: "none"
        }}>View endpoints →</a>
        </div>}
      {docs === null && <div className="subtle">Loading…</div>}
      {docs !== null && docs.length === 0 && <div className="empty-state" style={{
        padding: "24px 16px"
      }}>
          <div className="empty-icon">📄</div>
          <div className="empty-msg">No files uploaded yet</div>
          <div className="empty-sub">Upload API documentation to attach it to this collection.</div>
        </div>}
      {docs && docs.length > 0 && <div className="table-wrap">
          <table>
            <colgroup>
              <col style={{
              width: "32%"
            }} /><col style={{
              width: "14%"
            }} /><col style={{
              width: "10%"
            }} /><col style={{
              width: "22%"
            }} /><col style={{
              width: "22%"
            }} />
            </colgroup>
            <thead><tr><th>Filename</th><th>Type</th><th>Size</th><th>Status</th><th></th></tr></thead>
            <tbody>{docs.map(d => <tr key={d.id}>
                <td style={{
                fontWeight: 600
              }}>{d.filename}</td>
                <td><span className="badge neutral">{d.doc_type}</span></td>
                <td>{fmtBytes(d.size_bytes)}</td>
                <td>{statusCell(d)}</td>
                <td>
                  <div className="row" style={{
                  justifyContent: "flex-end"
                }}>
                    <button className="btn secondary sm" onClick={() => onReparse(d)} disabled={reparseState[d.id] === "running"}>{reparseState[d.id] === "running" ? "Parsing…" : d.status === "uploaded" ? "Parse" : "Reparse"}</button>
                    <button className="btn secondary sm" onClick={() => api.downloadApiDocument(collectionId, d.id)}>Download</button>
                    <button className="btn danger-outline sm" onClick={() => onDelete(d)}>Delete</button>
                  </div>
                </td>
              </tr>)}
            </tbody>
          </table>
        </div>}

      {/* SAST runs section — only show when a source_zip is present */
      docs && docs.some(d => d.doc_type === "source_zip") && <div style={{
        marginTop: 24
      }}>
          <div style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 10
        }}>
            <h3 style={{
            margin: 0
          }}>SAST Scans</h3>
            <button className="btn sm" disabled={sastBusy} onClick={async () => {
            setSastBusy(true);
            setError(null);
            try {
              const sr = await api.createSastRun(collectionId);
              await api.startSastScan(sr.id);
              nav(`#/sast-runs/${sr.id}/progress`);
            } catch (e) {
              setError(e.message);
            } finally {
              setSastBusy(false);
            }
          }}>{sastBusy ? "Starting…" : "Run SAST Scan"}</button>
          </div>
          {sastRuns.length === 0 ? <div className="subtle">No SAST scans yet. Click "Run SAST Scan" to analyse the uploaded source code.</div> : <div className="table-wrap">
              <table>
                <colgroup><col style={{
                width: "30%"
              }} /><col style={{
                width: "12%"
              }} /><col style={{
                width: "8%"
              }} /><col style={{
                width: "18%"
              }} /><col style={{
                width: "16%"
              }} /><col /></colgroup>
                <thead><tr><th>Name</th><th>Status</th><th>Leads</th><th>Linked scan</th><th>Started</th><th></th></tr></thead>
                <tbody>{sastRuns.map(sr => <tr key={sr.id}>
                    <td>{sr.name}</td>
                    <td><span className={"badge " + (sr.status === "completed" ? "ok" : sr.status === "failed" ? "danger" : sr.status === "scanning" ? "running" : "neutral")}>{sr.status}</span></td>
                    <td>{sr.leads_count}</td>
                    <td>{sr.triggered_by_run_id ? <a href={`#/api-runs/${sr.triggered_by_run_id}/status`}>API run #{sr.triggered_by_run_id}</a> : <span className="subtle">—</span>}</td>
                    <td>{sr.started_at ? new Date(sr.started_at).toLocaleString() : "—"}</td>
                    <td><a className="btn ghost sm" href={`#/sast-runs/${sr.id}/progress`}>View →</a></td>
                  </tr>)}
                </tbody>
              </table>
            </div>}
        </div>}
    </div>
  </>;
}
