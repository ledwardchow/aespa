import { renderMarkdown } from "../../lib/aliceSession";
import { ALICE_DEDUP_DIRECTIVE } from "../SastRuns";
import { useState, useEffect, useRef, useMemo, useReducer } from "react";
import { api, formatError } from "../../lib/api";
import { SCAN_MODE_OPTIONS, SCAN_MODE_DEFINITIONS, ScanModeDefinitions, scanModeLabel, csv, defaultPolicyForm, policyToForm, policyPayload } from "../../lib/policy";
import { aliceSessionSubscribe, _aliceFlushRecovery } from "../../lib/aliceSession";
import { fmtDate, sourceLabel, markdownText, markdownCodeBlock, leadImportPayload, leadsToMarkdown, markdownExportFilename, downloadTextFile, findingsToMarkdown, workProgramToMarkdown, parseFindingsMarkdown, markdownBullet, stripMarkdownFence } from "../../lib/utilities";


export function ApiRunFindingsTab({
  runId,
  scanRunning,
  run
}) {
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(new Set());
  const [clearBusy, setClearBusy] = useState(false);
  const [dedupeBusy, setDedupeBusy] = useState(false);
  const [editingFinding, setEditingFinding] = useState(null); // finding id being edited
  const [editDraft, setEditDraft] = useState(null); // working copy
  const [editBusy, setEditBusy] = useState(false);
  const issueImportInputRef = useRef(null);
  const load = async () => {
    try {
      const data = await api.getApiFindings(runId);
      setFindings(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, [runId, load]);

  // Poll while scan is running.
  useEffect(() => {
    if (!scanRunning) return;
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, [
	scanRunning,
	runId,
	load
]);
  const toggle = id => {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };
  const onExportFindingsMarkdown = () => {
    try {
      const md = findingsToMarkdown(findings, {
        runName: run?.name,
        generatedAt: new Date()
      });
      downloadTextFile(markdownExportFilename(run, null), md, "text/markdown;charset=utf-8");
    } catch (e) {
      setError(e.message);
    }
  };
  const onImportFindingsClick = () => {
    issueImportInputRef.current?.click();
  };
  const onImportFindingsFile = async e => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const imported = parseFindingsMarkdown(await file.text());
      if (!imported.length) throw new Error("No issues found in the selected file.");
      const result = await api.importApiFindings(runId, imported);
      setFindings(await api.getApiFindings(runId));
      alert(`Imported ${result.imported} issue${result.imported === 1 ? "" : "s"}.`);
    } catch (e) {
      setError(e.message);
    }
  };

  // Seed the dedup directive into ALICE and run it — the API analogue of the web
  // scan's "AI Review Issues" button. Because the ALICE chat lives in a separate
  // tab here, we persist the prompt into the active session (so it shows up when
  // the user opens the Agents tab), start the run, poll to completion, then reload.
  const onDeduplicateFindings = async () => {
    if (dedupeBusy) return;
    try {
      const st = await api.getApiAliceStatus(runId);
      if (st?.running) {
        setError("A.L.I.C.E. is already running — wait for it to finish.");
        return;
      }
    } catch {}
    setDedupeBusy(true);
    setError(null);
    try {
      const data = await api.getApiAliceSessions(runId);
      const chats = data.chats && data.chats.length ? data.chats : [{
        id: "tab-default",
        title: "Session 1",
        messages: []
      }];
      const tabId = data.active_tab_id || chats[0].id;
      const target = chats.find(c => c.id === tabId) || chats[0];
      const history = target.messages.map(m => ({
        sender: m.sender,
        text: m.text
      }));
      const now = Date.now();
      const thinkId = `think-${now}`,
        replyId = `reply-${now + 1}`;
      const ts = new Date().toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit"
      });
      target.messages.push({
        id: `u-${now}`,
        sender: "user",
        type: "message",
        text: ALICE_DEDUP_DIRECTIVE,
        ts
      }, {
        id: thinkId,
        sender: "alice",
        type: "thinking",
        text: "",
        ts
      }, {
        id: replyId,
        sender: "alice",
        type: "message",
        text: "",
        ts
      });
      await api.saveApiAliceSessions(runId, {
        chats,
        active_tab_id: tabId
      });
      await api.startApiAliceRun(runId, {
        message: ALICE_DEDUP_DIRECTIVE,
        history,
        tab_id: tabId,
        think_msg_id: thinkId,
        reply_msg_id: replyId
      });
      await new Promise(resolve => {
        const t = setInterval(async () => {
          try {
            const s = await api.getApiAliceStatus(runId);
            if (!s?.running) {
              clearInterval(t);
              resolve();
            }
          } catch {
            clearInterval(t);
            resolve();
          }
        }, 3000);
      });
      await load();
      setExpanded(new Set());
    } catch (e) {
      setError(e.message);
    } finally {
      setDedupeBusy(false);
    }
  };
  const onClearFindings = async () => {
    if (!confirm("Clear all findings for this API test run?")) return;
    setClearBusy(true);
    setError(null);
    try {
      await api.clearApiFindings(runId);
      setFindings([]);
    } catch (e) {
      setError(e.message);
    } finally {
      setClearBusy(false);
    }
  };
  const onDeleteApiFinding = async (e, findingId) => {
    e.stopPropagation();
    try {
      await api.deleteApiFinding(runId, findingId);
      setFindings(prev => prev.filter(f => f.id !== findingId));
      setExpanded(prev => {
        const next = new Set(prev);
        next.delete(findingId);
        return next;
      });
    } catch (err) {
      setError(err.message);
    }
  };
  const onEditApiFinding = (e, f) => {
    e.stopPropagation();
    setExpanded(prev => new Set(prev).add(f.id));
    setEditingFinding(f.id);
    setEditDraft({
      severity: f.severity,
      validation_status: f.validation_status,
      title: f.title || "",
      affected_url: f.affected_url || "",
      owasp_api_category: f.owasp_api_category || "",
      description: f.description || "",
      impact: f.impact || "",
      recommendation: f.recommendation || "",
      evidence: f.evidence || ""
    });
  };
  const onCancelEditApiFinding = e => {
    e?.stopPropagation?.();
    setEditingFinding(null);
    setEditDraft(null);
  };
  const onSaveEditApiFinding = async (e, findingId) => {
    e?.stopPropagation?.();
    if (!editDraft || editBusy) return;
    setEditBusy(true);
    try {
      const updated = await api.updateApiFinding(runId, findingId, editDraft);
      setFindings(prev => prev.map(f => f.id === findingId ? {
        ...f,
        ...updated
      } : f));
      setEditingFinding(null);
      setEditDraft(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setEditBusy(false);
    }
  };
  const sevCls = s => ({
    critical: "sev-critical",
    high: "sev-high",
    medium: "sev-medium",
    low: "sev-low",
    info: "sev-info"
  })[s] || "sev-info";
  if (loading) return <div className="subtle" style={{
    padding: 32
  }}>Loading findings…</div>;
  return <div style={{
    padding: "16px 24px"
  }}>
      {error && <div className="alert error" style={{
      marginBottom: 12
    }}>{error}</div>}
      <div style={{
      display: "flex",
      alignItems: "center",
      gap: 8,
      marginBottom: 16,
      flexWrap: "wrap"
    }}>
        <h3 style={{
        margin: 0,
        marginRight: 4
      }}>Security Findings</h3>
        {scanRunning && <span className="badge warning" style={{
        fontSize: 12
      }}>Scan running…</span>}
        <span className="badge neutral" style={{
        fontSize: 12
      }}>{findings.length} finding{findings.length !== 1 ? "s" : ""}</span>
        <div style={{
        flex: 1
      }}></div>
        <button className="btn sm" onClick={load}>Refresh</button>
        {findings.length > 0 && <button className="btn sm" onClick={onExportFindingsMarkdown}>Export Issues</button>}
        <button className="btn sm" onClick={onImportFindingsClick}>Import Issues</button>
        <input ref={issueImportInputRef} type="file" accept=".md,text/markdown,text/plain" style={{
        display: "none"
      }} onChange={onImportFindingsFile} />
        {findings.length > 0 && <button className="btn sm" disabled={dedupeBusy || scanRunning} onClick={onDeduplicateFindings}>
            {dedupeBusy && <span className="inline-spinner"></span>}
            {dedupeBusy ? "Reviewing…" : "AI Review Issues"}
          </button>}
        {findings.length > 0 && <button className="btn danger-outline sm" disabled={clearBusy} onClick={onClearFindings}>{clearBusy ? "Clearing…" : "Clear all"}</button>}
      </div>
      {findings.length === 0 ? <div className="subtle" style={{
      padding: 24,
      textAlign: "center"
    }}>
                 {scanRunning ? "Scan in progress — findings will appear here as they are discovered." : "No findings yet. Start a scan to test this API collection."}
               </div> : findings.map(f => <div key={f.id} className="finding-card" style={{
      marginBottom: 8,
      border: "1px solid var(--border)",
      borderRadius: 8,
      overflow: "hidden"
    }}>
            <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "10px 14px",
        cursor: "pointer",
        background: "var(--surface)"
      }} onClick={() => {
        if (editingFinding === f.id) return;
        toggle(f.id);
      }}>
              <span className={"sev-badge " + sevCls(f.severity)}>{f.severity}</span>
              <span style={{
          fontWeight: 600,
          flex: 1
        }}>{f.title}</span>
              {f.validation_status === "confirmed" && <span className="val-badge val-confirmed">confirmed</span>}
              {f.validation_status === "unconfirmed" && <span className="val-badge val-unconfirmed">unconfirmed</span>}
              {(f.validation_status === "false_positive" || f.validation_status === "low_confidence") && <span className="val-badge val-fp">low conf</span>}
              {f.owasp_api_category && <span className="badge neutral" style={{
          fontSize: 11
        }}>{f.owasp_api_category}</span>}
              {!f.owasp_api_category && f.owasp_category && <span className="badge neutral" style={{
          fontSize: 11
        }}>{f.owasp_category}</span>}
              <span style={{
          color: "var(--muted)",
          fontSize: 12
        }}>{expanded.has(f.id) ? "▲" : "▼"}</span>
              <button className="btn ghost sm finding-del-btn" title="Edit finding" onClick={e => onEditApiFinding(e, f)}>✎</button>
              <button className="btn ghost sm finding-del-btn" title="Delete finding" onClick={e => onDeleteApiFinding(e, f.id)}>🗑</button>
            </div>
            {expanded.has(f.id) && editingFinding === f.id && editDraft && <div className="finding-edit-form" style={{
        borderTop: "1px solid var(--border)",
        background: "var(--bg)"
      }} onClick={e => e.stopPropagation()}>
                <div className="finding-edit-row">
                  <label className="finding-edit-field">
                    <span>Severity</span>
                    <select value={editDraft.severity} onChange={e => setEditDraft(d => ({
              ...d,
              severity: e.target.value
            }))}>
                      {["critical", "high", "medium", "low", "info"].map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </label>
                  <label className="finding-edit-field">
                    <span>Status</span>
                    <select value={editDraft.validation_status} onChange={e => setEditDraft(d => ({
              ...d,
              validation_status: e.target.value
            }))}>
                      {[["unvalidated", "unvalidated"], ["confirmed", "confirmed"], ["unconfirmed", "unconfirmed"], ["false_positive", "low confidence"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select>
                  </label>
                  <label className="finding-edit-field" style={{
            maxWidth: 120
          }}>
                    <span>OWASP API</span>
                    <input type="text" value={editDraft.owasp_api_category} onChange={e => setEditDraft(d => ({
              ...d,
              owasp_api_category: e.target.value
            }))} />
                  </label>
                </div>
                <label className="finding-edit-field">
                  <span>Title</span>
                  <input type="text" value={editDraft.title} onChange={e => setEditDraft(d => ({
            ...d,
            title: e.target.value
          }))} />
                </label>
                <label className="finding-edit-field">
                  <span>Affected URL</span>
                  <input type="text" value={editDraft.affected_url} onChange={e => setEditDraft(d => ({
            ...d,
            affected_url: e.target.value
          }))} />
                </label>
                {[["description", "Description"], ["impact", "Impact"], ["recommendation", "Recommendation"], ["evidence", "Evidence"]].map(([k, label]) => <label key={k} className="finding-edit-field">
                    <span>{label}</span>
                    <textarea rows="3" value={editDraft[k]} onChange={e => setEditDraft(d => ({
            ...d,
            [k]: e.target.value
          }))}></textarea>
                  </label>)}
                <div className="row" style={{
          gap: 8,
          marginTop: 4,
          justifyContent: "flex-end"
        }}>
                  <button className="btn ghost sm" disabled={editBusy} onClick={onCancelEditApiFinding}>Cancel</button>
                  <button className="btn sm" disabled={editBusy} onClick={e => onSaveEditApiFinding(e, f.id)}>{editBusy ? "Saving…" : "Save"}</button>
                </div>
              </div>}
            {expanded.has(f.id) && editingFinding !== f.id && <div style={{
        padding: "12px 14px",
        borderTop: "1px solid var(--border)",
        background: "var(--bg)"
      }}>
                {f.affected_url && <div style={{
          marginBottom: 8
        }}><b>URL:</b> <code style={{
            fontSize: 12
          }}>{f.affected_url}</code></div>}
                {f.description && <div style={{
          marginBottom: 8
        }}><b>Description:</b>
                  <div style={{
            marginTop: 4
          }}>{renderMarkdown(f.description)}</div></div>}
                {f.impact && <div style={{
          marginBottom: 8
        }}><b>Impact:</b> {f.impact}</div>}
                {f.recommendation && <div style={{
          marginBottom: 8
        }}><b>Recommendation:</b> {f.recommendation}</div>}
                {f.evidence && <div style={{
          marginBottom: 8
        }}><b>Evidence:</b>
                  <pre style={{
            fontSize: 11,
            background: "var(--code-bg,#1e1e2e)",
            color: "var(--code-fg,#cdd6f4)",
            padding: 8,
            borderRadius: 4,
            overflow: "auto",
            maxHeight: 200,
            whiteSpace: "pre-wrap"
          }}>{f.evidence}</pre></div>}
                <div style={{
          fontSize: 11,
          color: "var(--muted)"
        }}>{f.validation_status} · {f.finding_source}</div>
              </div>}
          </div>)}
    </div>;
}

// ── ApiRunEndpointsTab — per-endpoint prerequisites display ───────────────────

