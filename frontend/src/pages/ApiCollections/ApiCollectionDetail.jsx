import { useState, useEffect, useCallback } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";
import { StatusBadge } from "../../components/StatusBadge";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader, Crumb, Sep } from "../../components/PageHeader";

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
    if (!confirm("Delete ALL endpoints and credentials for this collection?\n\n" + "Documents are kept — you can re-parse them afterwards.\n\n" + "Use this to clear duplicates from uploading the same file multiple times.")) return;
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
    <PageHeader
      title={<><Crumb href="#/apis">APIs</Crumb><Sep />{collection ? collection.name : "…"}</>}
      actions={<>
        {collection && <button className="btn secondary" onClick={() => nav(`#/apis/${collectionId}/files`)}>Manage files</button>}
        {collection && <button className="btn danger-outline" onClick={onPurgeData} disabled={purging}>{purging ? "Purging…" : "Purge data"}</button>}
        {collection && <button className="btn secondary" onClick={() => nav(`#/apis/${collectionId}/edit`)}>Edit collection</button>}
        {collection && <button className="btn danger-outline" onClick={onDelete}>Delete</button>}
      </>} />
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
          {endpoints !== null && endpoints.length === 0 && <EmptyState style={{ padding: "32px 16px" }}
            title="No endpoints yet"
            sub={<>
                Upload an <strong>OpenAPI/Swagger</strong> or <strong>Postman</strong> file via <strong>Manage files</strong> — it parses automatically.<br />
                <span style={{
                color: "var(--muted)",
                fontSize: 11
              }}>Markdown/text files use LLM extraction and require an active LLM profile in Settings.</span>
              </>} />}
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
                  <td><StatusBadge status={r.status} /></td>
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
