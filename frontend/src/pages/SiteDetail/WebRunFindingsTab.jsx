import React from "react";
export function WebRunFindingsTab(props) {
  const { thinkingStatus, thinkingStopRequested, validateStatus, onStopValidation, dedupeBusy, findings, onExportFindingsMarkdown, onImportFindingsClick, issueImportInputRef, onImportFindingsFile, validateBusy, onValidateAll, aliceIsThinking, onDeduplicateFindings, clearBusy, confirm, setClearBusy, setClearError, api, runId, setFindings, isDynamicScanActive, editingFinding, setExpandedFinding, expandedFinding, onValidateFinding, onEditFinding, onDeleteFinding, editDraft, setEditDraft, editBusy, onCancelEditFinding, onSaveEditFinding, renderMarkdown, navigator, toggleGroup, sourceLabel, expandedGroups, findColW, startFindResize, onDeleteFindingGroup } = props;
  return (
    <>
      <div className="findings-panel">
          <div className="findings-status-bar">
            {thinkingStatus && thinkingStatus.status && thinkingStatus.status !== "idle" && <span className={"scan-status-badge scan-status-" + (thinkingStopRequested ? "stopping" : thinkingStatus.status)}>
                {thinkingStopRequested ? "Stopping Dynamic Scan…" : thinkingStatus.status === "running" ? "Dynamic Scan running…" : thinkingStatus.status === "analysing" ? "Dynamic Scan analysing…" : thinkingStatus.status === "stopping" ? "Dynamic Scan stopping…" : thinkingStatus.status === "complete" ? "Dynamic Scan complete" : thinkingStatus.status === "stopped" ? "Dynamic Scan stopped" : thinkingStatus.status === "failed" ? "Dynamic Scan failed" : "Dynamic Scan"}
              </span>}
            <div style={{
            flex: 1
          }}></div>
            {validateStatus?.status === "running" ? <span className="val-status-badge val-running">Validating… {validateStatus.confirmed + validateStatus.false_positives + (validateStatus.unconfirmed || 0)}/{validateStatus.total}</span> : validateStatus?.status === "stopped" ? <span className="val-status-badge val-fp">Validation stopped</span> : validateStatus?.status === "complete" ? <span className="val-status-badge val-complete">{validateStatus.confirmed} confirmed · {validateStatus.unconfirmed || 0} unconfirmed · {validateStatus.false_positives} low confidence</span> : null}
            {validateStatus?.status === "running" && <button className="btn danger-outline sm" style={{
            marginLeft: 8
          }} onClick={onStopValidation}>Stop validation</button>}
            {dedupeBusy && <span className="val-status-badge val-running dedupe-status">
                <span className="inline-spinner"></span>
                A.L.I.C.E. is reviewing issues…
              </span>}
            <div className="row" style={{
            gap: 8,
            marginLeft: 8
          }}>
              {findings.length > 0 && <button className="btn sm" onClick={onExportFindingsMarkdown}>
                  Export Issues
                </button>}
              <button className="btn sm" onClick={onImportFindingsClick}>
                Import Issues
              </button>
              <input ref={issueImportInputRef} type="file" accept=".md,text/markdown,text/plain" style={{
              display: "none"
            }} onChange={onImportFindingsFile} />
              {findings.length > 0 && <button className="btn sm" disabled={validateBusy || validateStatus?.status === "running"} onClick={onValidateAll}>✓ Validate Issues</button>}
              {findings.length > 0 && <button className="btn sm" disabled={dedupeBusy || validateBusy || aliceIsThinking || validateStatus?.status === "running"} onClick={onDeduplicateFindings}>
                  {dedupeBusy && <span className="inline-spinner"></span>}
                  {dedupeBusy ? "Reviewing…" : "AI Review Issues"}
                </button>}
              {findings.length > 0 && <button className="btn danger-outline sm" disabled={clearBusy === "findings"} onClick={async () => {
              if (!confirm("Clear all findings and reset page scan status?\nThis lets you re-run the scanner on the same crawl.")) return;
              setClearBusy("findings");
              setClearError(null);
              try {
                await api.clearFindings(runId);
                setFindings([]);
              } catch (e) {
                setClearError(e.message);
              } finally {
                setClearBusy("");
              }
            }}>{clearBusy === "findings" ? "Clearing…" : "Clear all"}</button>}
            </div>
          </div>
          {findings.length === 0 ? <div className="subtle" style={{
          padding: 24,
          textAlign: "center"
        }}>
                {isDynamicScanActive(thinkingStatus?.status) ? "Scan running… findings will appear here." : "No findings yet. Start a Dynamic Scan to begin."}
              </div> : <div className="findings-table-wrap">{(() => {
            const SEV_ORDER = {
              critical: 0,
              high: 1,
              medium: 2,
              low: 3,
              info: 4
            };
            const VAL_ORDER = {
              confirmed: 0,
              validating: 1,
              unvalidated: 2,
              unconfirmed: 3,
              false_positive: 4,
              low_confidence: 4
            };
            const DETERMINISTIC_GROUP_KEY = "__deterministic__";
            const UNCONFIRMED_GROUP_KEY = "__unconfirmed__";
            const FP_GROUP_KEY = "__low_confidence__";
            const activeMap = {};
            const unconfirmedMap = {};
            const fpMap = {};
            const deterministicMap = {};
            // The TLS/SSL posture finding is a deterministic_probe by origin, but it
            // is a first-class A02 finding and belongs in the normal findings list —
            // not the low-signal Deterministic Findings bucket (per-page probe echoes).
            const isDeterministicBucket = f => f.finding_source === "deterministic_probe" && f.title !== "TLS/SSL configuration weaknesses";
            for (const f of findings) {
              const target = isDeterministicBucket(f) ? deterministicMap : f.validation_status === "false_positive" || f.validation_status === "low_confidence" ? fpMap : f.validation_status === "unconfirmed" ? unconfirmedMap : activeMap;
              (target[f.title] = target[f.title] || []).push(f);
            }
            const makeGroups = map => Object.entries(map).map(([title, items]) => {
              const sortedItems = [...items].sort((a, b) => {
                const va = VAL_ORDER[a.validation_status] ?? 2;
                const vb = VAL_ORDER[b.validation_status] ?? 2;
                if (va !== vb) return va - vb;
                return (SEV_ORDER[a.severity] ?? 99) - (SEV_ORDER[b.severity] ?? 99);
              });
              const topSev = items.reduce((b, f) => (SEV_ORDER[f.severity] ?? 99) < (SEV_ORDER[b] ?? 99) ? f.severity : b, items[0].severity);
              return {
                title,
                items: sortedItems,
                topSev,
                count: items.length,
                source: items[0].finding_source || "unknown"
              };
            }).sort((a, b) => {
              return (SEV_ORDER[a.topSev] ?? 99) - (SEV_ORDER[b.topSev] ?? 99);
            });
            const groups = makeGroups(activeMap);
            const unconfirmedGroups = makeGroups(unconfirmedMap);
            const fpGroups = makeGroups(fpMap);
            const deterministicGroups = makeGroups(deterministicMap);
            const unconfirmedCount = unconfirmedGroups.reduce((total, g) => total + g.count, 0);
            const fpCount = fpGroups.reduce((total, g) => total + g.count, 0);
            const deterministicCount = deterministicGroups.reduce((total, g) => total + g.count, 0);
            const evidenceItemsFor = f => {
              let items = [];
              if (Array.isArray(f.evidence_items)) {
                items = f.evidence_items;
              } else {
                try {
                  const parsed = JSON.parse(f.evidence_json || "[]");
                  items = Array.isArray(parsed) ? parsed : [];
                } catch  {
                  items = [];
                }
              }
              // The verdict and reasoning are already shown in the finding-level
              // "Validation (…)" note, so drop the duplicate evidence items here.
              return items.filter(it => it && it.type !== "validation_verdict" && it.type !== "validation_reasoning");
            };
            const renderFinding = (f, keyPrefix = "") => <React.Fragment key={keyPrefix + f.id}>
                  <tr key={keyPrefix + f.id} className="finding-instance-row" onClick={() => {
                if (editingFinding === f.id) return;
                setExpandedFinding(expandedFinding === f.id ? null : f.id);
              }}>
                    <td>
                      {f.validation_status === "confirmed" && <span className="val-badge val-confirmed">confirmed</span>}
                      {f.validation_status === "unconfirmed" && <span className="val-badge val-unconfirmed">unconfirmed</span>}
                      {f.validation_status === "false_positive" && <span className="val-badge val-fp">low conf</span>}
                      {f.validation_status === "low_confidence" && <span className="val-badge val-fp">low conf</span>}
                      {f.validation_status === "validating" && <span className="val-badge val-validating">…</span>}
                    </td>
                    <td></td>
                    <td colSpan="2">
                      <span className="instance-chevron">{expandedFinding === f.id ? "▾" : "▸"}</span>
                      <span className="finding-affected-label" style={{
                    marginRight: 6
                  }}>Affected URL</span>
                      <span className="mono" style={{
                    fontSize: 11,
                    wordBreak: "break-all"
                  }}>{f.affected_url || "—"}</span>
                    </td>
                    <td>
                      <div className="row" style={{
                    gap: 4,
                    justifyContent: "flex-end"
                  }}>
                        {(f.validation_status === "unvalidated" || f.validation_status === "unconfirmed" || f.validation_status === "false_positive" || f.validation_status === "low_confidence") && <button className="btn ghost sm finding-del-btn" title="Validate" onClick={e => onValidateFinding(e, f.id)}>✓</button>}
                        <button className="btn ghost sm finding-del-btn" title="Edit" onClick={e => onEditFinding(e, f)}>✎</button>
                        <button className="btn ghost sm finding-del-btn" title="Delete" onClick={e => onDeleteFinding(e, f.id)}>🗑</button>
                      </div>
                    </td>
                  </tr>
                  {expandedFinding === f.id && editingFinding === f.id && editDraft && <tr key={"edit-" + keyPrefix + f.id} className="finding-evidence-row">
                      <td colSpan="5">
                        <div className="finding-edit-form" onClick={e => e.stopPropagation()}>
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
                        maxWidth: 90
                      }}>
                              <span>CVSS</span>
                              <input type="number" min="0" max="10" step="0.1" value={editDraft.cvss_score} onChange={e => setEditDraft(d => ({
                          ...d,
                          cvss_score: e.target.value
                        }))} />
                            </label>
                            <label className="finding-edit-field" style={{
                        flex: 2
                      }}>
                              <span>CVSS Vector</span>
                              <input type="text" value={editDraft.cvss_vector} onChange={e => setEditDraft(d => ({
                          ...d,
                          cvss_vector: e.target.value
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
                          {[["description", "Description"], ["impact", "Impact"], ["likelihood", "Likelihood"], ["recommendation", "Recommendation"]].map(([k, label]) => <label key={k} className="finding-edit-field">
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
                            <button className="btn ghost sm" disabled={editBusy} onClick={onCancelEditFinding}>Cancel</button>
                            <button className="btn sm" disabled={editBusy} onClick={e => onSaveEditFinding(e, f.id)}>{editBusy ? "Saving…" : "Save"}</button>
                          </div>
                        </div>
                      </td>
                    </tr>}
                  {expandedFinding === f.id && editingFinding !== f.id && <tr key={"ev-" + keyPrefix + f.id} className="finding-evidence-row">
                      <td colSpan="5">
                        <div className="finding-description">
                          <div><strong>Description</strong></div>
                          <div>{renderMarkdown(f.description) || "—"}</div>
                          <div style={{
                      marginTop: 8
                    }}><strong>Impact</strong></div>
                          <div>{renderMarkdown(f.impact) || "—"}</div>
                          <div style={{
                      marginTop: 8
                    }}><strong>Likelihood</strong></div>
                          <div>{renderMarkdown(f.likelihood) || "—"}</div>
                          <div style={{
                      marginTop: 8
                    }}><strong>Recommendation</strong></div>
                          <div>{renderMarkdown(f.recommendation) || "—"}</div>
                          <div style={{
                      marginTop: 8
                    }}><strong>CVSS 3.1</strong></div>
                          <div>
                            {f.cvss_score !== undefined && f.cvss_score !== null ? `${Number(f.cvss_score).toFixed(1)} (${f.severity})` : "—"}
                            {f.cvss_vector ? <span className="mono" style={{
                        marginLeft: 8,
                        fontSize: 11
                      }}>{f.cvss_vector}</span> : ""}
                          </div>
                        </div>
                        {f.validation_note && <div className={"finding-validation-note val-note-" + f.validation_status}>
                            <strong>Validation ({f.validation_status}):</strong> {f.validation_note}
                          </div>}
                        {f.poc_command && <div className="finding-poc" style={{
                    marginTop: 12
                  }}>
                            <div className="row" style={{
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}>
                              <strong>Validation Command (verified)</strong>
                              <button className="btn ghost sm" title="Copy command" onClick={e => {
                        e.stopPropagation();
                        navigator.clipboard?.writeText(f.poc_command);
                      }}>Copy</button>
                            </div>
                            <pre className="finding-evidence">{f.poc_command}</pre>
                            {f.poc_setup && <details style={{
                      marginTop: 4
                    }}>
                                <summary className="finding-affected-label" style={{
                        cursor: "pointer"
                      }}>Setup (capture an authenticated session)</summary>
                                <pre className="finding-evidence" style={{
                        whiteSpace: "pre-wrap"
                      }}>{f.poc_setup}</pre>
                              </details>}
                          </div>}
                        {evidenceItemsFor(f).length > 0 && <div className="structured-evidence">
                            {evidenceItemsFor(f).map((item, idx) => <div key={idx} className={"structured-evidence-item evidence-type-" + (item.type || "note")}>
                                <div className="structured-evidence-label">
                                  <span>{item.label || item.type || "Evidence"}</span>
                                </div>
                                <pre className="structured-evidence-value">{item.value}</pre>
                              </div>)}
                          </div>}
                        {(() => {
                    // Skip the raw request/response dump when the structured
                    // evidence above already renders them — otherwise the same
                    // HTTP exchange shows up twice in the write-up.
                    const hasStructuredHttp = evidenceItemsFor(f).some(it => it.type === "http_request" || it.type === "http_response");
                    if (hasStructuredHttp) return null;
                    return <>
                            {f.request_evidence && <pre className="finding-evidence">REQUEST:\n{f.request_evidence}</pre>}
                            {f.response_evidence && <pre className="finding-evidence">RESPONSE:\n{f.response_evidence}</pre>}
                            {!f.request_evidence && !f.response_evidence && f.evidence && <pre className="finding-evidence">{f.evidence}</pre>}</>;
                  })()}
                        {f.screenshot_b64 && <div className="finding-screenshot-wrap">
                            <div className="finding-affected-label">Screenshot</div>
                            <img src={"data:image/png;base64," + f.screenshot_b64} className="finding-screenshot" alt="proof screenshot" />
                          </div>}
                        {(() => {
                    const instances = (() => {
                      try {
                        return JSON.parse(f.merged_instances || "[]");
                      } catch  {
                        return [];
                      }
                    })();
                    if (!instances.length) return null;
                    return <div style={{
                      marginTop: 12
                    }}>
                              <strong>Additional Affected Instances ({instances.length})</strong>
                              {instances.map((inst, idx) => <div key={idx} style={{
                        marginTop: 8,
                        paddingLeft: 12,
                        borderLeft: "2px solid var(--border,#ccc)"
                      }}>
                                  <div className="finding-affected-label">Instance {idx + 2}</div>
                                  <span className="mono" style={{
                          fontSize: 11,
                          wordBreak: "break-all"
                        }}>{inst.url || "\u2014"}</span>
                                  {inst.request_evidence && <pre className="finding-evidence" style={{
                          marginTop: 4
                        }}>REQUEST:\n{inst.request_evidence}</pre>}
                                  {inst.response_evidence && <pre className="finding-evidence">RESPONSE:\n{inst.response_evidence}</pre>}
                                  {!inst.request_evidence && !inst.response_evidence && inst.evidence && <pre className="finding-evidence">{inst.evidence}</pre>}
                                </div>)}
                            </div>;
                  })()}
                      </td>
                    </tr>}
                </React.Fragment>;
            const renderStatusRows = (statusGroups, keyPrefix) => statusGroups.map(g => {
              const groupKey = keyPrefix + ":" + g.title;
              return <React.Fragment key={groupKey}>
                    <tr key={groupKey} className="finding-group-row" onClick={() => toggleGroup(groupKey)}>
                      <td><span className={"sev-badge sev-" + g.topSev}>{g.topSev}</span></td>
                      <td><span className="source-badge">{sourceLabel(g.source)}</span></td>
                      <td className="finding-title">
                        <span className="group-chevron">{expandedGroups.has(groupKey) ? "▾" : "▸"}</span>
                        {g.title}
                      </td>
                      <td><span className="finding-count-badge">{g.count}</span></td>
                      <td></td>
                    </tr>
                    {expandedGroups.has(groupKey) && g.items.map(f => renderFinding(f, keyPrefix + "-"))}
                  </React.Fragment>;
            });
            const unconfirmedRows = renderStatusRows(unconfirmedGroups, "unconfirmed");
            const fpRows = renderStatusRows(fpGroups, "fp");
            const deterministicRows = renderStatusRows(deterministicGroups, "deterministic");
            return <table className="findings-table">
                  <colgroup>{findColW.map((w, i) => <col key={i} style={{
                  width: w != null ? w + "px" : undefined
                }} />)}</colgroup>
                  <thead>
                    <tr>
                      <th>Severity <div className="col-rh" onMouseDown={e => startFindResize(0, e)} onClick={e => e.stopPropagation()} /></th>
                      <th>Source <div className="col-rh" onMouseDown={e => startFindResize(1, e)} onClick={e => e.stopPropagation()} /></th>
                      <th>Title <div className="col-rh" onMouseDown={e => startFindResize(2, e)} onClick={e => e.stopPropagation()} /></th>
                      <th># <div className="col-rh" onMouseDown={e => startFindResize(3, e)} onClick={e => e.stopPropagation()} /></th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {groups.map(g => <React.Fragment key={g.title}>
                      <tr className="finding-group-row" onClick={() => toggleGroup(g.title)}>
                        <td><span className={"sev-badge sev-" + g.topSev}>{g.topSev}</span></td>
                        <td><span className="source-badge">{sourceLabel(g.source)}</span></td>
                        <td className="finding-title">
                          <span className="group-chevron">{expandedGroups.has(g.title) ? "▾" : "▸"}</span>
                          {g.title}
                        </td>
                        <td><span className="finding-count-badge">{g.count}</span></td>
                        <td>
                          <button className="btn ghost sm finding-del-btn" title="Delete group" onClick={e => onDeleteFindingGroup(e, g.title)}>🗑</button>
                        </td>
                      </tr>
                      {expandedGroups.has(g.title) && g.items.map(f => renderFinding(f))}
                    </React.Fragment>)}
                    {unconfirmedCount > 0 && <>
                      <tr key={UNCONFIRMED_GROUP_KEY} className="finding-group-row" onClick={() => toggleGroup(UNCONFIRMED_GROUP_KEY)}>
                        <td><span className="val-badge val-unconfirmed">unconfirmed</span></td>
                        <td></td>
                        <td className="finding-title">
                          <span className="group-chevron">{expandedGroups.has(UNCONFIRMED_GROUP_KEY) ? "▾" : "▸"}</span>
                          Unconfirmed Findings
                        </td>
                        <td><span className="finding-count-badge">{unconfirmedCount}</span></td>
                        <td></td>
                      </tr>
                      {expandedGroups.has(UNCONFIRMED_GROUP_KEY) && unconfirmedRows}
                    </>}
                    {fpCount > 0 && <>
                      <tr key={FP_GROUP_KEY} className="finding-group-row" onClick={() => toggleGroup(FP_GROUP_KEY)}>
                        <td><span className="val-badge val-fp">low conf</span></td>
                        <td></td>
                        <td className="finding-title">
                          <span className="group-chevron">{expandedGroups.has(FP_GROUP_KEY) ? "▾" : "▸"}</span>
                          Low Confidence
                        </td>
                        <td><span className="finding-count-badge">{fpCount}</span></td>
                        <td></td>
                      </tr>
                      {expandedGroups.has(FP_GROUP_KEY) && fpRows}
                    </>}
                    {deterministicCount > 0 && <>
                      <tr key={DETERMINISTIC_GROUP_KEY} className="finding-group-row" onClick={() => toggleGroup(DETERMINISTIC_GROUP_KEY)}>
                        <td><span className="val-badge val-fp">deterministic</span></td>
                        <td></td>
                        <td className="finding-title">
                          <span className="group-chevron">{expandedGroups.has(DETERMINISTIC_GROUP_KEY) ? "▾" : "▸"}</span>
                          Deterministic Findings
                        </td>
                        <td><span className="finding-count-badge">{deterministicCount}</span></td>
                        <td></td>
                      </tr>
                      {expandedGroups.has(DETERMINISTIC_GROUP_KEY) && deterministicRows}
                    </>}
                  </tbody>
                </table>;
          })()}
              </div>}
        </div>
    </>
  );
}
