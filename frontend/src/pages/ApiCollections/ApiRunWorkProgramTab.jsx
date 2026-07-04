import { useState, useEffect, useRef, useMemo, useReducer } from "react";
import { OWASP_LABELS, COVERAGE_CATEGORIES } from "./ApiRunEndpointsTab";
import { api, formatError } from "../../lib/api";
import { SCAN_MODE_OPTIONS, SCAN_MODE_DEFINITIONS, ScanModeDefinitions, scanModeLabel, csv, defaultPolicyForm, policyToForm, policyPayload } from "../../lib/policy";
import { aliceSessionSubscribe, _aliceFlushRecovery } from "../../lib/aliceSession";
import { fmtDate, sourceLabel, markdownText, markdownCodeBlock, slugForFilename, leadsExportFilename, markdownExportFilename, downloadTextFile, WP_STATUS_MARK, workProgramToMarkdown, parseFindingsMarkdown, markdownBullet, stripMarkdownFence } from "../../lib/utilities";


export function ApiRunWorkProgramTab({
  runId,
  scanRunning,
  run
}) {
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedCell, setSelectedCell] = useState(null);
  const [enforce, setEnforce] = useState(null); // latest enforce_progress event
  const esRef = useRef(null);
  const loadMatrix = () => api.getApiCoverageMatrix(runId).then(m => {
    setMatrix(m);
    setLoading(false);
  }).catch(() => setLoading(false));
  useEffect(() => {
    loadMatrix();
  }, [runId, loadMatrix]);

  // Poll during scan.
  useEffect(() => {
    if (!scanRunning) return;
    const t = setInterval(loadMatrix, 5000);
    return () => clearInterval(t);
  }, [
	scanRunning,
	runId,
	loadMatrix
]);

  // SSE live updates.
  useEffect(() => {
    if (!scanRunning) return;
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    const es = new EventSource(`/api/api-test-runs/${runId}/events`);
    esRef.current = es;
    es.onmessage = ev => {
      try {
        const d = JSON.parse(ev.data);
        if (d.type === "coverage_update") {
          setMatrix(prev => {
            if (!prev) return prev;
            return {
              ...prev,
              endpoints: prev.endpoints.map(ep => {
                if (ep.endpoint_id !== d.endpoint_id) return ep;
                const cells = {
                  ...ep.cells
                };
                const existing = cells[d.owasp_api_category] || {
                  status: "not_started",
                  finding_ids: []
                };
                const fids = [...existing.finding_ids];
                if (d.finding_id && !fids.includes(d.finding_id)) fids.push(d.finding_id);
                cells[d.owasp_api_category] = {
                  status: d.status,
                  finding_ids: fids
                };
                return {
                  ...ep,
                  cells
                };
              })
            };
          });
        } else if (d.type === "enforce_progress") {
          setEnforce(d);
          if (d.phase === "complete") loadMatrix();
        }
      } catch {}
    };
    return () => {
      es.close();
      esRef.current = null;
    };
  }, [
	scanRunning,
	runId,
	loadMatrix
]);
  if (loading) return <div className="subtle" style={{
    padding: 24
  }}>Loading coverage matrix…</div>;
  if (!matrix || !matrix.endpoints?.length) return <div className="subtle" style={{
    padding: 24,
    textAlign: "center"
  }}>
      No coverage data yet.{" "}
      {run?.status === "pending" ? "Start a scan to populate the OWASP Coverage matrix." : "The matrix will appear once a scan has started."}
    </div>;
  const cats = matrix.categories || COVERAGE_CATEGORIES;
  const totals = matrix.totals || {};
  const totalCells = Object.values(totals).reduce((a, b) => a + b, 0);
  const coveredCount = (totals.covered || 0) + (totals.finding || 0) + (totals.skipped || 0);
  const pct = totalCells > 0 ? Math.round(coveredCount / totalCells * 100) : 0;
  const onExportMarkdown = () => {
    const md = workProgramToMarkdown(matrix, {
      cats,
      labels: OWASP_LABELS,
      kind: "api",
      runName: run?.name,
      generatedAt: new Date()
    });
    downloadTextFile(`${slugForFilename(run?.name || `api-run-${runId}`)}-owasp-coverage-${new Date().toISOString().slice(0, 10)}.md`, md, "text/markdown;charset=utf-8");
  };
  return <div style={{
    padding: 16
  }}>
      <div style={{
      display: "flex",
      alignItems: "center",
      gap: 16,
      marginBottom: 12,
      flexWrap: "wrap"
    }}>
        <h3 style={{
        margin: 0
      }}>OWASP Coverage Matrix</h3>
        <span className={"badge " + (run?.coverage_mode === "enforce" ? "warning" : "neutral")}>
          {run?.coverage_mode || "track"} mode
        </span>
        <span className="badge neutral">{pct}% coverage ({coveredCount}/{totalCells} cells)</span>
        {scanRunning && <span className="badge warning">● Live</span>}
        {enforce && enforce.phase !== "complete" && <span className="badge warning" title="Enforce mode is resolving remaining coverage cells">
            Enforcing… {enforce.resolved != null ? `${enforce.resolved}/${enforce.total}` : `${enforce.remaining} left`}
          </span>}
        {enforce && enforce.phase === "complete" && <span className="badge success" title={enforce.message || ""}>
            Enforce done · {enforce.covered || 0} covered, {enforce.skipped || 0} skipped{enforce.budget_exhausted ? " (budget hit)" : ""}
          </span>}
        <div style={{
        flex: 1
      }}></div>
        <button className="btn sm" onClick={onExportMarkdown}>Export Markdown</button>
      </div>

      <div style={{
      display: "flex",
      gap: 8,
      marginBottom: 10,
      flexWrap: "wrap",
      fontSize: 11
    }}>
        {[["not_started", "cov-not-started", "Not started"], ["in_progress", "cov-in-progress", "In progress"], ["covered", "cov-covered", "Covered"], ["finding", "cov-finding", "Finding"], ["skipped", "cov-skipped", "Skipped"]].map(([s, cls, label]) => <span key={s} style={{
        display: "flex",
        alignItems: "center",
        gap: 4
      }}>
            <span className={"cov-cell " + cls} style={{
          display: "inline-block",
          width: 14,
          height: 14,
          borderRadius: 3
        }}></span>
            {label} ({totals[s] || 0})
          </span>)}
      </div>

      <div style={{
      overflowX: "auto"
    }}>
        <table className="coverage-matrix" style={{
        borderCollapse: "collapse",
        fontSize: 11,
        minWidth: 600
      }}>
          <thead>
            <tr>
              <th style={{
              textAlign: "left",
              padding: "4px 8px",
              minWidth: 280,
              width: "30%"
            }}>Endpoint</th>
              <th style={{
              padding: "4px 6px",
              textAlign: "center",
              minWidth: 50
            }}>Ready</th>
              {cats.map(cat => <th key={cat} style={{
              padding: "4px 4px",
              textAlign: "center",
              minWidth: 60
            }} title={cat + ": " + (OWASP_LABELS[cat] || cat)}>
                  <div style={{
                fontWeight: 600
              }}>{cat}</div>
                  <div style={{
                color: "var(--muted)",
                fontWeight: 400,
                fontSize: 10
              }}>{OWASP_LABELS[cat] || ""}</div>
                </th>)}
            </tr>
          </thead>
          <tbody>
            {matrix.endpoints.map(ep => {
            const readyOk = ep.prereq_can_test && ep.prereq_can_test_auth;
            return <tr key={ep.endpoint_id} style={{
              borderBottom: "1px solid var(--border)"
            }}>
                  <td style={{
                padding: "4px 8px"
              }}>
                    <span className={"method-badge method-" + ep.method.toLowerCase()} style={{
                  marginRight: 4
                }}>{ep.method}</span>
                    <span className="mono" style={{
                  fontSize: 11
                }}>{ep.path}</span>
                  </td>
                  <td style={{
                textAlign: "center",
                padding: "4px 6px"
              }}>
                    {ep.auth_required ? <span title="Auth required" style={{
                  color: readyOk ? "var(--success,#4caf50)" : "var(--danger,#f44336)"
                }}>{readyOk ? "✔" : "✘"}</span> : <span title="No auth" style={{
                  color: "var(--success,#4caf50)"
                }}>✔</span>}
                  </td>
                  {cats.map(cat => {
                const cell = ep.cells?.[cat];
                if (!cell) return <td key={cat} style={{
                  textAlign: "center",
                  padding: "2px 4px"
                }}><span className="cov-cell cov-na" title="N/A">—</span></td>;
                const fids = cell.finding_ids || [];
                const findings = cell.findings || [];
                const isSelected = selectedCell?.endpoint_id === ep.endpoint_id && selectedCell?.cat === cat;
                return <td key={cat} style={{
                  textAlign: "center",
                  padding: "2px 4px"
                }}>
                        <span className={"cov-cell cov-" + cell.status.replace("_", "-") + (isSelected ? " selected" : "") + (fids.length ? " has-findings" : "")} title={cat + ": " + cell.status + (fids.length ? " (" + fids.length + " finding" + (fids.length > 1 ? "s" : "") + "" : "")} style={{
                    cursor: fids.length ? "pointer" : "default"
                  }} onClick={() => fids.length && setSelectedCell(isSelected ? null : {
                    endpoint_id: ep.endpoint_id,
                    cat,
                    path: ep.path,
                    method: ep.method,
                    fids,
                    findings
                  })}>{fids.length > 0 ? fids.length : ""}</span>
                      </td>;
              })}
                </tr>;
          })}
          </tbody>
        </table>
      </div>

      {selectedCell && <div style={{
      marginTop: 12,
      padding: 12,
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: 6
    }}>
          <div style={{
        display: "flex",
        justifyContent: "space-between",
        marginBottom: 8
      }}>
            <b style={{
          fontSize: 13
        }}>{selectedCell.method} {selectedCell.path} — {selectedCell.cat} {OWASP_LABELS[selectedCell.cat] || ""}</b>
            <button className="btn ghost sm" onClick={() => setSelectedCell(null)}>✕</button>
          </div>
          {selectedCell.findings && selectedCell.findings.length ? selectedCell.findings.map(f => <div key={f.id} style={{
        padding: "6px 0",
        borderTop: "1px solid var(--border)"
      }}>
                  <div style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          marginBottom: 2
        }}>
                    <span className={"sev-badge sev-" + (f.severity || "info")}>{f.severity || "info"}</span>
                    <b style={{
            fontSize: 12
          }}>{f.title}</b>
                    {f.validation_status && f.validation_status !== "unvalidated" ? <span style={{
            fontSize: 11,
            color: "var(--muted)"
          }}>({f.validation_status})</span> : ""}
                  </div>
                  {f.description ? <div style={{
          fontSize: 12,
          color: "var(--muted)",
          whiteSpace: "pre-wrap"
        }}>{f.description}</div> : ""}
                  <div style={{
          fontSize: 11,
          color: "var(--muted)",
          marginTop: 2
        }}>Finding #{f.id} — view in the Findings tab.</div>
                </div>) : <div style={{
        fontSize: 12
      }}>Finding IDs: {selectedCell.fids.join(", ")} — view in the Findings tab.</div>}
        </div>}
    </div>;
}

// ── ApiRunTrafficTab ───────────────────────────────────────────────────────────

