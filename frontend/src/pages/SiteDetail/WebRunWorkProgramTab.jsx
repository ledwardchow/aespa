import { useState, useEffect, useRef, useCallback } from "react";
import { OWASP_WEB_LABELS } from "./_constants";
import { OWASP_WEB_SHORT } from "../ApiCollections/ApiRunEndpointsTab";
import { OWASP_WEB_CATEGORIES } from "./WebRunSastLeadsTab";
import { api } from "../../lib/api";
import { slugForFilename, downloadTextFile, workProgramToMarkdown } from "../../lib/utilities";
import { usePolling } from "../../hooks/usePolling";

export function WebRunWorkProgramTab({
  runId,
  run,
  scanRunning,
  reloadKey = 0
}) {
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [selectedCell, setSelectedCell] = useState(null);
  const [seedMsg, setSeedMsg] = useState(null);
  const [enforce, setEnforce] = useState(null); // latest enforce_progress event
  const esRef = useRef(null);
  const loadMatrix = useCallback(() => api.getWebCoverageMatrix(runId).then(m => {
    setMatrix(m);
    setLoading(false);
  }).catch(() => setLoading(false)), [runId]);
  usePolling(loadMatrix, { enabled: scanRunning, intervalMs: 5000 });
  useEffect(() => {
    if (reloadKey > 0) loadMatrix();
  }, [reloadKey, loadMatrix]);

  // SSE live updates — mirrors ApiRunWorkProgramTab.
  useEffect(() => {
    if (!scanRunning) return;
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    const es = new EventSource(`/api/test-runs/${runId}/events`);
    esRef.current = es;
    es.onmessage = ev => {
      try {
        const d = JSON.parse(ev.data);
        if (d.type === "coverage_update") {
          setMatrix(prev => {
            if (!prev) return prev;
            return {
              ...prev,
              pages: prev.pages.map(pg => {
                if (!pg.page_ids.includes(d.page_id) && pg.page_id !== d.page_id) return pg;
                const cells = {
                  ...pg.cells
                };
                const existing = cells[d.owasp_category] || {
                  status: "not_started",
                  finding_ids: []
                };
                const fids = [...(existing.finding_ids || [])];
                if (d.finding_id && !fids.includes(d.finding_id)) fids.push(d.finding_id);
                cells[d.owasp_category] = {
                  ...existing,
                  status: d.status,
                  finding_ids: fids
                };
                return {
                  ...pg,
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
  }, [scanRunning, runId, loadMatrix]);
  const onSeed = async () => {
    setSeeding(true);
    setSeedMsg(null);
    try {
      const r = await api.seedWebWorkprogram(runId);
      setSeedMsg(r.created > 0 ? `Added ${r.created} new cell${r.created !== 1 ? "s" : ""}.` : "No new cells — OWASP Coverage is up to date.");
      await loadMatrix();
    } catch (e) {
      setSeedMsg("Error: " + e.message);
    } finally {
      setSeeding(false);
    }
  };
  const onExportMarkdown = () => {
    const md = workProgramToMarkdown(matrix, {
      cats: OWASP_WEB_CATEGORIES,
      labels: OWASP_WEB_LABELS,
      kind: "web",
      runName: run?.name,
      generatedAt: new Date()
    });
    downloadTextFile(`${slugForFilename(run?.name || `web-run-${runId}`)}-owasp-coverage-${new Date().toISOString().slice(0, 10)}.md`, md, "text/markdown;charset=utf-8");
  };
  if (loading) return <div className="subtle" style={{
    padding: 24
  }}>Loading OWASP Coverage…</div>;
  const cats = OWASP_WEB_CATEGORIES;
  const totals = matrix?.totals || {};
  const totalCells = Object.values(totals).reduce((a, b) => a + b, 0);
  const coveredCount = (totals.covered || 0) + (totals.finding || 0) + (totals.skipped || 0);
  const pct = totalCells > 0 ? Math.round(coveredCount / totalCells * 100) : 0;
  const effectiveCoverageMode = matrix?.coverage_mode || run?.coverage_mode || "track";
  return <div style={{
    padding: 16
  }}>
      <div style={{
      display: "flex",
      alignItems: "center",
      gap: 12,
      marginBottom: 12,
      flexWrap: "wrap"
    }}>
        <h3 style={{
        margin: 0
      }}>OWASP Coverage Matrix</h3>
        <span className={"badge " + (effectiveCoverageMode === "enforce" ? "warning" : "neutral")}>
          {effectiveCoverageMode} mode
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
        {matrix?.pages?.length > 0 && <button className="btn sm" onClick={onExportMarkdown}>Export Markdown</button>}
        <button className="btn sm" disabled={seeding} onClick={onSeed}>
          {seeding ? "Populating…" : "Populate from Site Map"}
        </button>
      </div>
      {seedMsg && <div className={"alert " + (seedMsg.startsWith("Error") ? "error" : "success")} style={{
      marginBottom: 10,
      padding: "6px 12px",
      fontSize: 12
    }}>{seedMsg}</div>}

      {!matrix?.seeded && <div className="subtle" style={{
      padding: 24,
      textAlign: "center"
    }}>
          No OWASP Coverage data yet. Click <b>Populate from Site Map</b> to seed the matrix from crawl data.
        </div>}

      {matrix?.seeded && !matrix?.pages?.length && <div className="subtle" style={{
      padding: 24,
      textAlign: "center"
    }}>
          No applicable pages found. Run a crawl first so OWASP categories can be classified.
        </div>}

      {matrix?.seeded && matrix?.pages?.length > 0 && <>
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
          minWidth: 700
        }}>
            <thead>
              <tr>
                <th style={{
                textAlign: "left",
                padding: "4px 8px",
                minWidth: 300,
                width: "35%"
              }}>Page</th>
                {cats.map(cat => <th key={cat} style={{
                padding: "4px 4px",
                textAlign: "center",
                minWidth: 70
              }} title={cat + ": " + (OWASP_WEB_LABELS[cat] || cat)}>
                    <div style={{
                  fontWeight: 600
                }}>{cat}</div>
                    <div style={{
                  color: "var(--muted)",
                  fontWeight: 400,
                  fontSize: 10,
                  lineHeight: 1.2,
                  whiteSpace: "pre-line"
                }}>{(OWASP_WEB_SHORT[cat] || OWASP_WEB_LABELS[cat] || "").replace(/ /g, "\n")}</div>
                  </th>)}
              </tr>
            </thead>
            <tbody>
              {matrix.pages.map(pg => <tr key={pg.page_id} style={{
              borderBottom: "1px solid var(--border)"
            }}>
                  <td style={{
                padding: "4px 8px"
              }}>
                    <div className="mono" style={{
                  fontSize: 11,
                  wordBreak: "break-all"
                }} title={pg.url}>{pg.url}</div>
                    {pg.title && <div style={{
                  fontSize: 10,
                  color: "var(--muted)"
                }}>{pg.title}</div>}
                  </td>
                  {cats.map(cat => {
                const cell = pg.cells?.[cat];
                if (!cell) return <td key={cat} style={{
                  textAlign: "center",
                  padding: "2px 4px"
                }}><span className="cov-cell cov-na" title="N/A">—</span></td>;
                const fids = cell.finding_ids || [];
                const isSelected = selectedCell?.page_id === pg.page_id && selectedCell?.cat === cat;
                return <td key={cat} style={{
                  textAlign: "center",
                  padding: "2px 4px"
                }}>
                        <span className={"cov-cell cov-" + cell.status.replace("_", "-") + (isSelected ? " selected" : "") + (fids.length ? " has-findings" : "")} title={cat + ": " + cell.status + (fids.length ? " (" + fids.length + " finding" + (fids.length > 1 ? "s" : "") + "" : "") + ")\n" + pg.url} style={{
                    cursor: fids.length ? "pointer" : "default"
                  }} onClick={() => fids.length && setSelectedCell(isSelected ? null : {
                    page_id: pg.page_id,
                    cat,
                    url: pg.url,
                    fids,
                    findings: cell.findings
                  })}>{fids.length > 0 ? fids.length : ""}</span>
                      </td>;
              })}
                </tr>)}
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
          }}>{selectedCell.cat} {OWASP_WEB_LABELS[selectedCell.cat] || ""} — {selectedCell.url}</b>
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
      </>}
    </div>;
}
