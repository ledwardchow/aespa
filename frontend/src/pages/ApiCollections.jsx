import { useState, useEffect, useRef, useCallback, useContext } from "react";
import { api, formatError } from "../lib/api";
import { nav } from "../lib/router";
import { aliceSessionSubscribe, _aliceFlushRecovery } from "../lib/aliceSession";
import { IconApis, IconPlus, IconPlay, IconShield, IconChevronRight, IconMessageSquare, IconBrain } from "../components/Icons";

import { LeadsPanel } from "./ApiCollections/LeadsPanel";
import { ApiRunLeadsTab } from "./ApiCollections/ApiRunLeadsTab";
import { ApiRunSessionsTab } from "./ApiCollections/ApiRunSessionsTab";
import { ApiRunFindingsTab } from "./ApiCollections/ApiRunFindingsTab";
import { ApiRunEndpointsTab } from "./ApiCollections/ApiRunEndpointsTab";
import { ApiRunWorkProgramTab } from "./ApiCollections/ApiRunWorkProgramTab";
import { ApiRunTrafficTab } from "./ApiCollections/ApiRunTrafficTab";
import { _buildAgentsFromLog } from "./ApiCollections/_buildAgentsFromLog";
import { ApiRunStatusTab } from "./ApiCollections/ApiRunStatusTab";
import { ApiRunLogTab } from "./ApiCollections/ApiRunLogTab";
import { ApiRunAgentsTab } from "./ApiCollections/ApiRunAgentsTab";
// ── API collections ───────────────────────────────────────────────────────────

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
    <div className="topbar">
      <div className="topbar-title">APIs</div>
      <div className="topbar-actions">
        <input ref={importRef} type="file" accept=".json" style={{
          display: "none"
        }} onChange={onImportFile} />
        <button className="btn secondary" onClick={() => importRef.current.click()} disabled={importing}>{importing ? "Importing…" : "Import API"}</button>
        <button className="btn" onClick={() => nav("#/apis/new")}><IconPlus /> New API collection</button>
      </div>
    </div>
    <div className="content scroll-content">
      {error && <div className="alert error" style={{
        marginBottom: 16
      }}>{error}</div>}
      {collections === null && <div className="subtle">Loading…</div>}
      {collections !== null && collections.length === 0 && <div className="empty-state">
          <div className="empty-icon">⬡</div>
          <div className="empty-msg">No API collections yet</div>
          <div className="empty-sub">Create a collection, upload API docs, and run structured API security tests.</div>
          <button className="btn" onClick={() => nav("#/apis/new")}><IconPlus /> New API collection</button>
        </div>}
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
export function ApiCollectionForm({
  collectionId
}) {
  const isEdit = typeof collectionId === "number";
  const [form, setForm] = useState({
    name: "",
    base_url: "",
    description: ""
  });
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  useEffect(() => {
    if (!isEdit) return;
    (async () => {
      try {
        const d = await api.getApiCollection(collectionId);
        setForm({
          name: d.name,
          base_url: d.base_url,
          description: d.description || ""
        });
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [isEdit, collectionId]);
  const upd = p => setForm(f => ({
    ...f,
    ...p
  }));
  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    const payload = {
      name: form.name.trim(),
      base_url: form.base_url.trim(),
      description: form.description.trim() || null
    };
    try {
      if (isEdit) {
        await api.updateApiCollection(collectionId, payload);
        nav(`#/apis/${collectionId}`);
      } else {
        const c = await api.createApiCollection(payload);
        nav(`#/apis/${c.id}`);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const bc = isEdit ? <><a href={`#/apis/${collectionId}`} style={{
      color: "var(--muted)",
      fontWeight: 400
    }}>{form.name || "API collection"}</a><span className="breadcrumb-sep"> / </span>Edit</> : <><a href="#/apis" style={{
      color: "var(--muted)",
      fontWeight: 400
    }}>APIs</a><span className="breadcrumb-sep"> / </span>New API collection</>;
  return <>
    <div className="topbar"><div className="topbar-title">{bc}</div></div>
    <div className="content scroll-content">
      {loading && <div className="subtle">Loading…</div>}
      {!loading && <form className="card" onSubmit={onSubmit}>
          {error && <div className="alert error">{error}</div>}
          <div className="form-section-title">API collection</div>
          <div className="field"><label>Name</label>
            <input type="text" required value={form.name} placeholder="e.g. Payments API" onChange={e => upd({
            name: e.target.value
          })} /></div>
          <div className="field"><label>Base URL</label>
            <input type="url" required value={form.base_url} placeholder="https://api.example.com" onChange={e => upd({
            base_url: e.target.value
          })} /></div>
          <div className="field"><label>Description (optional)</label>
            <textarea value={form.description} placeholder="What these APIs do, scope, contacts…" onChange={e => upd({
            description: e.target.value
          })} /></div>
          <div className="divider" />
          <div className="row spread">
            <button type="button" className="btn ghost" onClick={() => isEdit ? nav(`#/apis/${collectionId}`) : nav("#/apis")}>Cancel</button>
            <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : isEdit ? "Save changes" : "Create collection"}</button>
          </div>
        </form>}
    </div></>;
}
export function ApiCollectionDetail({
  collectionId
}) {
  const [collection, setCollection] = useState(null);
  const [endpoints, setEndpoints] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [apiRuns, setApiRuns] = useState(null);
  const [credentials, setCredentials] = useState(null);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [assessing, setAssessing] = useState(false);
  const [purging, setPurging] = useState(false);
  const load = useCallback(async () => {
    try {
      const [c, eps, rd, runs, creds] = await Promise.all([api.getApiCollection(collectionId), api.listApiEndpoints(collectionId), api.getApiReadiness(collectionId), api.listApiRuns(collectionId), api.listApiCredentials(collectionId)]);
      setCollection(c);
      setEndpoints(eps);
      setReadiness(rd && rd.status !== "not_assessed" ? rd : null);
      setApiRuns(runs);
      setCredentials(creds);
    } catch (e) {
      setError(e.message);
    }
  }, [collectionId]);
  useEffect(() => {
    load();
  }, [load]);
  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  };
  const onAssessReadiness = async () => {
    setAssessing(true);
    setError(null);
    try {
      const rd = await api.runApiReadiness(collectionId);
      setReadiness(rd);
      // Reload endpoints so prereq columns update
      const eps = await api.listApiEndpoints(collectionId);
      setEndpoints(eps);
    } catch (e) {
      setError(e.message);
    } finally {
      setAssessing(false);
    }
  };
  const onPurgeData = async () => {
    if (!confirm("Delete ALL endpoints and credentials for this collection?\n\n" + "Documents are kept \u2014 you can re-parse them afterwards.\n\n" + "Use this to clear duplicates from uploading the same file multiple times.")) return;
    setPurging(true);
    setError(null);
    try {
      const result = await api.purgeCollectionData(collectionId);
      setEndpoints([]);
      setReadiness(null);
      setCredentials([]);
      alert(`Purged: ${result.endpoints_deleted} endpoints and ${result.credentials_deleted} credentials removed.`);
    } catch (e) {
      setError(e.message);
    } finally {
      setPurging(false);
    }
  };
  const onDelete = async () => {
    if (!collection) return;
    if (!confirm(`Delete "${collection.name}"? This also removes all uploaded docs, endpoints and test runs.`)) return;
    try {
      await api.deleteApiCollection(collectionId);
      nav("#/apis");
    } catch (e) {
      setError(e.message);
    }
  };
  const toggleScope = async ep => {
    try {
      const updated = await api.patchEndpointScope(collectionId, ep.id, {
        in_scope: !ep.in_scope
      });
      setEndpoints(eps => eps.map(e => e.id === ep.id ? updated : e));
    } catch (e) {
      setError(e.message);
    }
  };
  const methodBadge = m => {
    const cls = {
      GET: "badge method-get",
      POST: "badge method-post",
      PUT: "badge method-put",
      PATCH: "badge method-patch",
      DELETE: "badge method-delete"
    };
    return <span className={cls[m] || "badge neutral"}>{m}</span>;
  };

  // Readiness helpers
  const scoreColor = score => score >= 75 ? "var(--success,#22c55e)" : score >= 40 ? "var(--warning-text,#d97706)" : "var(--danger,#ef4444)";
  const readinessLabel = score => score >= 75 ? "Ready" : score >= 40 ? "Partial" : "Not Ready";
  const prereqIcon = ep => {
    if (!ep.prereq_can_test) return <span title="Cannot test — insufficient info" style={{
      color: "var(--danger,#ef4444)",
      fontSize: 14
    }}>✗</span>;
    if (!ep.prereq_can_test_auth) return <span title="Auth credentials missing" style={{
      color: "var(--warning-text,#d97706)",
      fontSize: 14
    }}>⚠</span>;
    return <span title="Ready to test" style={{
      color: "var(--success,#22c55e)",
      fontSize: 14
    }}>✓</span>;
  };
  return <>
    <div className="topbar">
      <div className="topbar-title">
        <a href="#/apis" style={{
          color: "var(--muted)",
          fontWeight: 400
        }}>APIs</a>
        <span className="breadcrumb-sep"> / </span>
        {collection ? collection.name : "…"}
      </div>
      <div className="topbar-actions">
        {collection && <button className="btn secondary" onClick={() => nav(`#/apis/${collectionId}/files`)}>Manage files</button>}
        {collection && <button className="btn danger-outline" onClick={onPurgeData} disabled={purging}>{purging ? "Purging…" : "Purge data"}</button>}
        {collection && <button className="btn secondary" onClick={() => nav(`#/apis/${collectionId}/edit`)}>Edit collection</button>}
        {collection && <button className="btn danger-outline" onClick={onDelete}>Delete</button>}
      </div>
    </div>
    <div className="content scroll-content stack">
      {error && <div className="alert error">{error}</div>}
      {collection && <>
        <div className="card">
          <div className="form-section-title">Overview</div>
          <div className="field" style={{
            margin: 0
          }}><label>Base URL</label><div className="url">{collection.base_url}</div></div>
          {collection.description && <div className="field" style={{
            marginTop: 12,
            marginBottom: 0
          }}><label>Description</label><div>{collection.description}</div></div>}
        </div>

        <div className="card">
          <div className="form-section-title" style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}>
            <span>Readiness</span>
            <button className="btn secondary sm" onClick={onAssessReadiness} disabled={assessing}>
              {assessing ? "Assessing…" : readiness ? "Re-assess" : "Assess Readiness"}
            </button>
          </div>
          {assessing && <div className="subtle" style={{
            padding: "12px 0"
          }}>Running LLM readiness assessment…</div>}
          {!assessing && !readiness && <div className="subtle" style={{
            padding: "8px 0"
          }}>
              Click <strong>Assess Readiness</strong> to run an LLM-driven gap analysis — checks whether you have the
              right credentials and enough spec detail to test each endpoint.
            </div>}
          {!assessing && readiness && <div>
              <div style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 10
            }}>
                <span style={{
                fontSize: 22,
                fontWeight: 700,
                color: scoreColor(readiness.overall.score)
              }}>{readiness.overall.score}/100</span>
                <span className="badge" style={{
                background: scoreColor(readiness.overall.score),
                color: "#fff",
                padding: "2px 10px"
              }}>{readinessLabel(readiness.overall.score)}</span>
                <span style={{
                fontSize: 13,
                color: "var(--fg)"
              }}>{readiness.overall.summary}</span>
              </div>
              {readiness.overall.blocking_gaps?.length > 0 && <div style={{
              marginBottom: 8
            }}>
                  <strong style={{
                fontSize: 12,
                color: "var(--danger,#ef4444)"
              }}>Blocking gaps</strong>
                  <ul style={{
                margin: "4px 0 0 18px",
                padding: 0,
                fontSize: 12,
                color: "var(--fg)"
              }}>
                    {readiness.overall.blocking_gaps.map((g, i) => <li key={i}>{g}</li>)}
                  </ul>
                </div>}
              {readiness.overall.recommendations?.length > 0 && <div>
                  <strong style={{
                fontSize: 12,
                color: "var(--muted)"
              }}>Recommendations</strong>
                  <ul style={{
                margin: "4px 0 0 18px",
                padding: 0,
                fontSize: 12,
                color: "var(--muted)"
              }}>
                    {readiness.overall.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>}
              <div style={{
              marginTop: 8,
              fontSize: 11,
              color: "var(--muted)"
            }}>
                Assessed {new Date(readiness.assessed_at).toLocaleString()}
                ·
                Auth understood: {readiness.overall.auth_method_understood ? "✓" : "✗"}
                · Credentials: {readiness.overall.has_credentials ? "✓" : "✗"}
                · Test data: {readiness.overall.has_sufficient_test_data ? "✓" : "✗"}
              </div>
            </div>}
        </div>

        <div className="card">
          <div className="form-section-title">
            <span>Credentials {credentials !== null ? <span className="badge neutral" style={{
                marginLeft: 6
              }}>{credentials.length}</span> : ""}</span>
          </div>
          {credentials === null && <div className="subtle">Loading…</div>}
          {credentials !== null && credentials.length === 0 && <div className="subtle" style={{
            padding: "8px 0"
          }}>
              No credentials. They are parsed from uploaded auth/credentials files, or discovered automatically during a scan.
              Secret values are never displayed.
            </div>}
          {credentials !== null && credentials.length > 0 && <>
            <div className="table-wrap" style={{
              overflowX: "auto"
            }}>
              <table style={{
                width: "100%"
              }}>
                <thead><tr>
                  {["Scheme", "Name", "Label", "Scope", "Auth endpoint", "Added"].map(h => <th key={h}>{h}</th>)}
                </tr></thead>
                <tbody>{credentials.map(c => <tr key={c.id}>
                    <td><span className={`badge ${c.scheme === "login" ? "warning" : "neutral"}`}>{c.scheme}</span></td>
                    <td style={{
                      fontFamily: "var(--mono,monospace)",
                      fontSize: 12
                    }}>{c.name || "—"}</td>
                    <td>{c.label || <span className="subtle">—</span>}</td>
                    <td style={{
                      fontSize: 12
                    }}>{c.scope}</td>
                    <td style={{
                      fontFamily: "var(--mono,monospace)",
                      fontSize: 12,
                      overflowWrap: "break-word",
                      wordBreak: "break-all"
                    }}>{c.auth_endpoint || <span className="subtle">—</span>}</td>
                    <td style={{
                      fontSize: 12,
                      color: "var(--muted)"
                    }}>{new Date(c.created_at).toLocaleString()}</td>
                  </tr>)}
                </tbody>
              </table>
            </div>
            <div className="subtle" style={{
              marginTop: 8,
              fontSize: 11
            }}>
              Secret values are stored but never shown. <strong>login</strong>-scheme entries are username/password test accounts used to obtain tokens during a scan.
            </div></>}
        </div>

        <div className="card">
          <div className="form-section-title" style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}>
            <span>Endpoints {endpoints !== null ? <span className="badge neutral" style={{
                marginLeft: 6
              }}>{endpoints.length}</span> : ""}</span>
            <div className="row" style={{
              gap: 8
            }}>
              <button className="btn secondary sm" onClick={onRefresh} disabled={refreshing}>{refreshing ? "…" : "Refresh"}</button>
              <button className="btn secondary sm" onClick={() => nav(`#/apis/${collectionId}/files`)}>Manage files</button>
            </div>
          </div>
          {endpoints === null && <div className="subtle">Loading…</div>}
          {endpoints !== null && endpoints.length === 0 && <div className="empty-state" style={{
            padding: "32px 16px"
          }}>
              <div className="empty-icon">⬡</div>
              <div className="empty-msg">No endpoints yet</div>
              <div className="empty-sub">
                Upload an <strong>OpenAPI/Swagger</strong> or <strong>Postman</strong> file via <strong>Manage files</strong> — it parses automatically.<br />
                <span style={{
                color: "var(--muted)",
                fontSize: 11
              }}>Markdown/text files use LLM extraction and require an active LLM profile in Settings.</span>
              </div>
            </div>}
          {endpoints !== null && endpoints.length > 0 && <div className="table-wrap" style={{
            overflowX: "auto"
          }}>
              <table style={{
              tableLayout: "fixed",
              width: "100%",
              minWidth: 760
            }}>
                <colgroup>
                  <col style={{
                  width: "8%"
                }} /><col style={{
                  width: "24%"
                }} /><col style={{
                  width: "28%"
                }} /><col style={{
                  width: "8%"
                }} /><col style={{
                  width: "16%"
                }} /><col style={{
                  width: "8%"
                }} /><col style={{
                  width: "8%"
                }} />
                </colgroup>
                <thead><tr>
                  {["Method", "Path", "Summary", "Auth", "Tags", "Ready", "In scope"].map(h => <th key={h} style={{
                    overflow: "hidden",
                    whiteSpace: "nowrap",
                    resize: "horizontal",
                    position: "relative"
                  }}>{h}</th>)}
                </tr></thead>
                <tbody>{endpoints.map(ep => <tr key={ep.id} style={{
                  opacity: ep.in_scope ? 1 : 0.5
                }}>
                    <td>{methodBadge(ep.method)}</td>
                    <td style={{
                    fontFamily: "var(--mono,monospace)",
                    fontSize: 12,
                    overflowWrap: "break-word",
                    wordBreak: "break-all"
                  }}>{ep.path}</td>
                    <td style={{
                    fontSize: 12,
                    overflowWrap: "break-word"
                  }}>{ep.summary || "—"}</td>
                    <td>{ep.auth_required ? <span className="badge warning">yes</span> : <span className="badge neutral">no</span>}</td>
                    <td style={{
                    fontSize: 11,
                    overflowWrap: "break-word"
                  }}>{JSON.parse(ep.tags_json || "[]").join(", ") || "—"}</td>
                    <td style={{
                    textAlign: "center"
                  }} title={JSON.parse(ep.prereq_notes || "[]").join("; ") || undefined}>
                      {prereqIcon(ep)}
                    </td>
                    <td style={{
                    textAlign: "center"
                  }}>
                      <input type="checkbox" checked={ep.in_scope} onChange={() => toggleScope(ep)} style={{
                      cursor: "pointer"
                    }} />
                    </td>
                  </tr>)}
                </tbody>
              </table>
            </div>}
        </div>

        <div className="card">
          <div className="form-section-title" style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}>
            <span>Test Runs</span>
            <button className="btn sm" onClick={() => nav(`#/apis/${collectionId}/runs/new`)}>+ New test run</button>
          </div>
          {apiRuns === null && <div className="subtle">Loading…</div>}
          {apiRuns !== null && apiRuns.length === 0 && <div className="subtle" style={{
            padding: "12px 0"
          }}>
              No test runs yet. Click <strong>+ New test run</strong> to start one.
            </div>}
          {apiRuns !== null && apiRuns.length > 0 && <table style={{
            width: "100%"
          }}>
              <thead><tr>
                <th>Name</th><th>Status</th><th>Coverage</th><th>Created</th><th></th>
              </tr></thead>
              <tbody>{apiRuns.map(r => <tr key={r.id}>
                  <td><a href={`#/api-runs/${r.id}/status`} style={{
                    fontWeight: 600
                  }}>{r.name}</a></td>
                  <td><span className={`badge ${r.status === "completed" ? "success" : r.status === "running" ? "warning" : r.status === "failed" ? "danger" : "neutral"}`}>{r.status}</span></td>
                  <td>{r.coverage_mode}</td>
                  <td style={{
                  fontSize: 12,
                  color: "var(--muted)"
                }}>{new Date(r.created_at).toLocaleString()}</td>
                  <td><a href={`#/api-runs/${r.id}/status`} className="btn secondary sm">Open</a></td>
                </tr>)}
              </tbody>
            </table>}
        </div></>}
    </div>
  </>;
}
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

// ── API test run form ─────────────────────────────────────────────────────────

export function ApiTestRunForm({
  collectionId
}) {
  const [form, setForm] = useState({
    name: "",
    llm_profile_id: "",
    coverage_mode: "track"
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const upd = p => setForm(f => ({
    ...f,
    ...p
  }));
  useEffect(() => {
    api.listLLMProfiles().then(p => setProfiles(p || [])).catch(e => setError(e.message));
  }, []);
  const onSubmit = async e => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        name: form.name.trim() || null,
        llm_profile_id: form.llm_profile_id ? +form.llm_profile_id : null,
        coverage_mode: form.coverage_mode
      };
      const run = await api.createApiRun(collectionId, payload);
      nav(`#/api-runs/${run.id}/status`);
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  };
  return <>
    <div className="topbar">
      <div className="topbar-title">
        <a href={`#/apis/${collectionId}`} style={{
          color: "var(--muted)",
          fontWeight: 400
        }}>API collection</a>
        <span className="breadcrumb-sep"> / </span>New test run
      </div>
    </div>
    <div className="content scroll-content">
      {error && <div className="alert error">{error}</div>}
      <form className="card" style={{
        maxWidth: 560
      }} onSubmit={onSubmit}>
        <div className="form-section-title">New API test run</div>
        <div className="field">
          <label>Name <span className="subtle">(optional — auto-generated if blank)</span></label>
          <input type="text" value={form.name} onInput={e => upd({
            name: e.target.value
          })} placeholder="e.g. Sprint 12 auth test" />
        </div>
        <div className="field">
          <label>LLM profile</label>
          <select value={form.llm_profile_id} onChange={e => upd({
            llm_profile_id: e.target.value
          })}>
            <option value="">— Use global active profile —</option>
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Coverage mode</label>
          <select value={form.coverage_mode} onChange={e => upd({
            coverage_mode: e.target.value
          })}>
            <option value="track">Track — record coverage but don't enforce it</option>
            <option value="enforce">Enforce — block completion until all endpoints covered</option>
          </select>
        </div>
        <div className="row spread" style={{
          marginTop: 16
        }}>
          <button type="button" className="btn ghost" onClick={() => nav(`#/apis/${collectionId}`)}>Cancel</button>
          <button type="submit" className="btn" disabled={saving}>{saving ? "Creating…" : "Create run"}</button>
        </div>
      </form>
    </div></>;
}

// ── API test run detail ────────────────────────────────────────────────────────

const API_RUN_TABS = [{
  key: "status",
  label: "Status"
}, {
  key: "findings",
  label: "Findings"
}, {
  key: "leads",
  label: "Scan Leads"
}, {
  key: "sessions",
  label: "Sessions"
}, {
  key: "traffic",
  label: "Traffic Log"
}, {
  key: "endpoints",
  label: "Endpoints"
}, {
  key: "workprogram",
  label: "OWASP Coverage"
}];

// Reuse the same alice session management infrastructure as TestRunDetail but
// bound to the /api/api-test-runs/{id}/* alias routes.
export function useApiAliceSession(runId) {
  const [aliceSessions, setAliceSessions] = useState(null);
  const [aliceLoaded, setAliceLoaded] = useState(false);
  const [activeTabId, setActiveTabId] = useState("tab-default");
  const [aliceStatus, setAliceStatus] = useState(null);
  const streamRef = useRef(null);
  const cursorRef = useRef(0);
  const loadSessions = useCallback(async () => {
    try {
      const data = await api.getApiAliceSessions(runId);
      setAliceSessions(data.chats || []);
      setActiveTabId(data.active_tab_id || "tab-default");
      setAliceLoaded(true);
    } catch (e) {
      console.error("alice sessions load error", e);
      setAliceLoaded(true);
    }
  }, [runId]);
  const saveSessions = useCallback(async (chats, activeId) => {
    try {
      await api.saveApiAliceSessions(runId, {
        chats,
        active_tab_id: activeId
      });
    } catch (e) {
      console.error("alice sessions save error", e);
    }
  }, [runId]);
  const pollStatus = useCallback(async () => {
    try {
      const st = await api.getApiAliceStatus(runId);
      setAliceStatus(st);
    } catch {}
  }, [runId]);
  return {
    aliceSessions,
    setAliceSessions,
    aliceLoaded,
    activeTabId,
    setActiveTabId,
    aliceStatus,
    setAliceStatus,
    loadSessions,
    saveSessions,
    pollStatus,
    streamRef,
    cursorRef
  };
}
export function ApiTestRunDetail({
  runId,
  initialTab
}) {
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);
  const [scanStatus, setScanStatus] = useState(null);
  const [scanBusy, setScanBusy] = useState(false);
  const [coverageMode, setCoverageMode] = useState("track");
  const tab = initialTab || "status";
  useEffect(() => {
    api.getApiRun(runId).then(r => {
      setRun(r);
      setCoverageMode(r.coverage_mode || "track");
    }).catch(e => setError(e.message));
    api.getApiScanStatus(runId).then(setScanStatus).catch(() => {});
  }, [runId]);

  // Poll scan status while scanning.
  useEffect(() => {
    if (!scanStatus?.running) return;
    const t = setInterval(() => {
      api.getApiScanStatus(runId).then(st => {
        setScanStatus(st);
        if (!st.running) api.getApiRun(runId).then(setRun).catch(() => {});
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(t);
  }, [scanStatus?.running, runId]);
  const onStartScan = async () => {
    setScanBusy(true);
    try {
      await api.startApiScan(runId, coverageMode);
      const st = await api.getApiScanStatus(runId);
      setScanStatus(st);
      api.getApiRun(runId).then(r => {
        setRun(r);
        setCoverageMode(r.coverage_mode || "track");
      }).catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setScanBusy(false);
    }
  };
  const onStopScan = async () => {
    setScanBusy(true);
    try {
      await api.stopApiScan(runId);
      const st = await api.getApiScanStatus(runId);
      setScanStatus(st);
      api.getApiRun(runId).then(setRun).catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setScanBusy(false);
    }
  };
  const onDelete = async () => {
    if (!run) return;
    if (!confirm(`Delete test run "${run.name}"?`)) return;
    try {
      await api.deleteApiRun(runId);
      nav(`#/apis/${run.collection_id}`);
    } catch (e) {
      setError(e.message);
    }
  };
  const statusBadge = s => {
    const cls = s === "completed" ? "success" : s === "running" || s === "scanning" ? "warning" : s === "failed" || s === "cancelled" ? "danger" : "neutral";
    return <span className={"badge " + cls}>{s}</span>;
  };
  const scanRunning = scanStatus?.running === true;
  return <>
    <div className="topbar">
      <div className="topbar-title">
        <a href={run ? `#/apis/${run.collection_id}` : "#/apis"} style={{
          color: "var(--muted)",
          fontWeight: 400
        }}>API collection</a>
        <span className="breadcrumb-sep"> / </span>
        {run ? run.name : "…"}
        {run && <> {statusBadge(run.status)}</>}
      </div>
      <div className="topbar-actions">
        {scanRunning ? <button className="btn danger-outline" disabled={scanBusy} onClick={onStopScan}>
                   {scanBusy ? "Stopping…" : "Stop Scan"}
                 </button> : <>
            <label className="subtle" style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 12
          }} title="Track: observe coverage as the scan runs. Enforce: drive every applicable endpoint × category to covered or skipped-with-reason.">
              Coverage:
              <select value={coverageMode} disabled={scanBusy} onChange={e => setCoverageMode(e.target.value)}>
                <option value="track">Track</option>
                <option value="enforce">Enforce</option>
              </select>
            </label>
            <button className="btn" disabled={scanBusy} onClick={onStartScan}>
              {scanBusy ? "Starting…" : "Start Scan"}
            </button></>}
        {run && <button className="btn danger-outline" onClick={onDelete}>Delete</button>}
      </div>
    </div>
    <div className="tab-bar">
      {API_RUN_TABS.map(t => <button key={t.key} className={"tab-btn" + (tab === t.key ? " active" : "")} onClick={() => nav(`#/api-runs/${runId}/${t.key}`)}>{t.label}</button>)}
    </div>
    <div className={"content no-padding" + (tab === "status" ? " flex-fill-noscroll" : " scroll-content")}>
      {error && <div className="alert error">{error}</div>}
      {tab === "status" && <ApiRunStatusTab runId={runId} scanRunning={scanRunning} />}
      {tab === "findings" && <ApiRunFindingsTab runId={runId} scanRunning={scanRunning} run={run} />}
      {tab === "leads" && <ApiRunLeadsTab runId={runId} scanRunning={scanRunning} />}
      {tab === "sessions" && <ApiRunSessionsTab runId={runId} scanRunning={scanRunning} />}
      {tab === "traffic" && <ApiRunTrafficTab runId={runId} scanRunning={scanRunning} />}
      {tab === "endpoints" && <ApiRunEndpointsTab runId={runId} run={run} />}
      {tab === "workprogram" && <ApiRunWorkProgramTab runId={runId} scanRunning={scanRunning} run={run} />}
    </div>
  </>;
}

// ── ApiRunLeadsTab ─────────────────────────────────────────────────────────────


export function TestRunForm({
  siteId
}) {
  const [form, setForm] = useState({
    name: "",
    max_depth: 3,
    max_pages: 50,
    llm_profile_id: null
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const upd = p => setForm(f => ({
    ...f,
    ...p
  }));
  useEffect(() => {
    (async () => {
      try {
        const profs = await api.listLLMProfiles();
        setProfiles(profs || []);
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);
  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const run = await api.createRun(siteId, {
        name: form.name.trim() || null,
        max_depth: Number(form.max_depth),
        max_pages: Number(form.max_pages),
        llm_profile_id: form.llm_profile_id || null
      });
      nav(`#/runs/${run.id}`);
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  };
  return <>
    <div className="topbar">
      <div className="topbar-title">
        <a href={`#/sites/${siteId}`} style={{
          color: "var(--muted)",
          fontWeight: 400
        }}>Site</a>
        <span className="breadcrumb-sep"> / </span>New test run
      </div>
    </div>
    <div className="content scroll-content">
      <form className="card" onSubmit={onSubmit}>
        {error && <div className="alert error">{error}</div>}
        <div className="form-section-title">Run Configuration</div>
        <div className="field">
          <label>Name <span className="field-optional">(optional — auto-generated if blank)</span></label>
          <input type="text" value={form.name} placeholder="e.g. Initial crawl" onChange={e => upd({
            name: e.target.value
          })} />
        </div>
        <div className="two-col">
          <div className="field">
            <label>Max depth <span className="field-hint-inline">(1–10)</span></label>
            <input type="number" required min="1" max="10" value={form.max_depth} onChange={e => upd({
              max_depth: e.target.value
            })} />
          </div>
          <div className="field">
            <label>Max pages <span className="field-hint-inline">(5–500)</span></label>
            <input type="number" required min="5" max="500" value={form.max_pages} onChange={e => upd({
              max_pages: e.target.value
            })} />
          </div>
        </div>
        <div className="alert" style={{
          marginTop: 12
        }}>
          This run will use the global scan policy from Settings.
        </div>
        <div className="divider" />
        <div className="form-section-title">LLM Profile</div>
        <div className="field">
          <label>LLM profile <span className="field-optional">(optional — uses the globally active profile if not set)</span></label>
          <select className="select" value={form.llm_profile_id || ""} onChange={e => upd({
            llm_profile_id: e.target.value ? Number(e.target.value) : null
          })}>
            <option value="">— Use global active profile —</option>
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div className="row spread">
          <button type="button" className="btn ghost" onClick={() => nav(`#/sites/${siteId}`)}>Cancel</button>
          <button type="submit" className="btn" disabled={saving}>{saving ? "Creating…" : "Create run"}</button>
        </div>
      </form>
    </div></>;
}
export { LeadsPanel };
export { ApiRunLeadsTab };
export { ApiRunFindingsTab };
export { ApiRunEndpointsTab };
export { ApiRunWorkProgramTab };
export { ApiRunTrafficTab };
export { _buildAgentsFromLog };
export { ApiRunStatusTab };
export { ApiRunLogTab };
export { ApiRunAgentsTab };