import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { apiTranscriptText } from "../../lib/utilities";
import { OWASP_WEB_LABELS } from "./_constants";
import {
  SCOPE_IN_COLOR, SCOPE_OUT_COLOR, USER_ALL_COLOR, USER_ANONYMOUS_COLOR,
  USER_MULTIPLE_COLOR, USER_PALETTE
} from "./_helpers";
import { useSelectedSitemapPage } from "./useSelectedSitemapPage";
import { useSitemapGraph } from "./useSitemapGraph";
import { WebRunSitemapTab } from "./WebRunSitemapTab";

/** The interactive sitemap canvas and its selected-page inspector. */
export function WebRunSitemapGraph({
  runId, run, graph, active, graphView, onGraphChange, onStart,
  onStartThinkingScan, hasCheckpoint, onResumeThinkingScan, checkpointStatus, onError
}) {
  const { selectedNode, setSelectedNode, pageDetail, pageViews } = useSelectedSitemapPage(runId);
  const [cascade, setCascade] = useState(false);
  const [scopeBusy, setScopeBusy] = useState(false);
  const [testStateBusy, setTestStateBusy] = useState(false);
  const [testStateMessage, setTestStateMessage] = useState("");
  const [scannerSessions, setScannerSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState("");
  useEffect(() => {
    let cancelled = false;
    api.getScannerSessions(runId, true).then(result => {
      if (!cancelled) setScannerSessions(result?.sessions || result?.items || []);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [runId]);
  const { svgRef } = useSitemapGraph({
    graph,
    activeTab: active ? "sitemap" : "hidden",
    graphView,
    credentials: run?.credentials,
    currentUrl: run?.current_url,
    onSelectNode: setSelectedNode
  });

  const refreshGraph = async () => onGraphChange(await api.getGraph(runId));
  const toggleScope = async () => {
    if (!selectedNode || scopeBusy) return;
    setScopeBusy(true);
    try {
      await api.setPageScope(runId, selectedNode.id, {
        in_scope: selectedNode.in_scope === false,
        cascade
      });
      const nextGraph = await api.getGraph(runId);
      onGraphChange(nextGraph);
      setSelectedNode(nextGraph.nodes.find(node => node.id === selectedNode.id) || null);
    } catch (error) {
      onError(error.message);
    } finally {
      setScopeBusy(false);
    }
  };
  const deleteNode = async () => {
    if (!selectedNode || scopeBusy) return;
    setScopeBusy(true);
    try {
      await api.deletePage(runId, selectedNode.id, cascade);
      await refreshGraph();
      setSelectedNode(null);
    } catch (error) {
      onError(error.message);
    } finally {
      setScopeBusy(false);
    }
  };
  const testState = async () => {
    if (!selectedNode || !pageDetail || testStateBusy) return;
    setTestStateBusy(true);
    setTestStateMessage("");
    try {
      const result = await api.testPageState(runId, selectedNode.id, selectedSession ? { use_session: selectedSession } : {});
      setTestStateMessage(result.status === "queued" ? "Queued for the current Test Lead." : "Focused scan started.");
    } catch (error) {
      onError(error.message);
    } finally {
      setTestStateBusy(false);
    }
  };

  return <div className="graph-layout" style={{ display: active ? "flex" : "none" }}>
    <div className="graph-canvas-wrap">
      {graph && graph.nodes.length === 0 && <div className="graph-empty">
        <WebRunSitemapTab activeTab="sitemap" run={run} onStart={onStart} onStartThinkingScan={onStartThinkingScan} hasCheckpoint={hasCheckpoint} onResumeThinkingScan={onResumeThinkingScan} checkpointStatus={checkpointStatus} />
      </div>}
      <svg ref={svgRef} className="graph-svg" width="100%" height="100%" style={{ pointerEvents: !graph || graph.nodes.length === 0 ? "none" : "all" }} />
      {graph && graph.nodes.length > 0 && <div className="graph-legend">
        {graphView === "user" && run?.credentials?.length > 1 ? <>
          {(run.credentials || []).map((credential, index) => <div key={credential.id} className="legend-item"><span className="legend-dot" style={{ background: USER_PALETTE[index % USER_PALETTE.length] }} />{credential.label || credential.username}</div>)}
          <div className="legend-item"><span className="legend-dot" style={{ background: USER_ANONYMOUS_COLOR }} />Unauthenticated</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: USER_MULTIPLE_COLOR }} />Multiple users</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: USER_ALL_COLOR }} />All users</div>
        </> : <>
          <div className="legend-item"><span className="legend-dot" style={{ background: SCOPE_IN_COLOR }} />In Scope</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: SCOPE_OUT_COLOR }} />Out of Scope</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: "var(--bg)", border: "2px solid #fbbf24" }} />Failed</div>
        </>}
        <div className="legend-item">
          <span className="pulse-legend-dot" style={{ border: "2px solid #f59e0b", background: "transparent" }} />
          Pending LLM Analysis
        </div>
      </div>}
    </div>
    {selectedNode && <SitemapPageInspector
      node={selectedNode} detail={pageDetail} views={pageViews} cascade={cascade} scopeBusy={scopeBusy}
      testStateBusy={testStateBusy} testStateMessage={testStateMessage}
      scannerSessions={scannerSessions} selectedSession={selectedSession} onSessionChange={setSelectedSession}
      onCascade={setCascade} onClose={() => setSelectedNode(null)} onToggleScope={toggleScope} onDelete={deleteNode} onTestState={testState}
    />}
  </div>;
}

function SitemapPageInspector({ node, detail, views, cascade, scopeBusy, testStateBusy, testStateMessage, scannerSessions, selectedSession, onSessionChange, onCascade, onClose, onToggleScope, onDelete, onTestState }) {
  const isFailed = node.status === "failed" || detail?.status === "failed";
  const errorMessage = detail?.error_message || node.error_message;

  return <div className="graph-panel">
    <div className="graph-panel-header"><div className="graph-panel-url">{node.state_label ? `${node.url} · ${node.state_label}` : node.url}</div><button className="btn ghost sm" onClick={onClose}>✕</button></div>
    {detail ? <div className="graph-panel-body">
      {detail.title && <div className="graph-panel-title">{detail.title}</div>}
      {isFailed && <div className="sitemap-failed-banner" style={{ background: "rgba(245, 158, 11, 0.12)", border: "1px solid #f59e0b", color: "#f59e0b", padding: "8px 12px", borderRadius: 6, marginBottom: 12, fontSize: 12, display: "flex", flexDirection: "column", gap: 4 }}>
        <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
          <span>⚠️ Page Load Failed</span>
        </div>
        {errorMessage && <div style={{ color: "var(--text-2, #d1d5db)", fontFamily: "monospace", fontSize: 11, wordBreak: "break-word" }}>{errorMessage}</div>}
      </div>}
      <div className="graph-panel-section-label">Scope</div>
      <div className="scope-row">
        <span className={'scope-badge ' + (node.in_scope === false ? 'out' : 'in')}>{node.in_scope === false ? 'Out of Scope' : 'In Scope'}</span>
        {isFailed && <span className="cat-badge cat-no" style={{ fontSize: 11 }}>Failed</span>}
        <button className="btn sm" onClick={onToggleScope} disabled={scopeBusy}>{scopeBusy ? '…' : node.in_scope === false ? 'Mark in scope' : 'Mark out of scope'}</button>
        <button className="btn danger-outline sm" onClick={onDelete} disabled={scopeBusy} title="Delete this node (and children if checkbox is ticked)">🗑</button>
      </div>
      <label className="scope-cascade-label"><input type="checkbox" checked={cascade} onChange={event => onCascade(event.target.checked)} />Also apply to all children</label>
      {detail.browser_replay && <div className="spa-state-action"><div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 6 }}><label className="subtle">Session</label><select value={selectedSession} onChange={event => onSessionChange(event.target.value)}><option value="">Discovering session</option>{scannerSessions.map(session => <option key={session.id || session.label} value={session.label}>{session.label}{session.username ? ` · ${session.username}` : ''}</option>)}</select></div><button className="btn sm" onClick={onTestState} disabled={testStateBusy}>{testStateBusy ? '…' : 'Test this state'}</button>{testStateMessage && <span className="subtle">{testStateMessage}</span>}</div>}
      <PageCategories detail={detail} />
      {views.length > 0 ? <PageViews views={views} detail={detail} /> : <PageContext detail={detail} />}
      {views.length > 0 && <PageStateEvidence detail={detail} />}
    </div> : <div className="subtle" style={{ padding: 12 }}>Loading…</div>}
  </div>;
}

function PageCategories({ detail }) {
  const categories = [["req_auth", "Auth Required"], ["takes_input", "Takes Input"], ["has_object_ref", "Object Reference"], ["has_business_logic", "Business Logic"]];
  return <>
    <div className="graph-panel-section-label" style={{ marginTop: 14 }}>Page Categories</div>
    <div className="page-cats">{categories.map(([key, label]) => {
      const value = detail[key];
      return <div key={key} className="cat-row"><span className="cat-label">{label}</span><span className={'cat-badge ' + (value === true ? 'cat-yes' : value === false ? 'cat-no' : 'cat-unknown')}>{value === true ? 'Yes' : value === false ? 'No' : '?'}</span></div>;
    })}</div>
    {detail.owasp_applicable && Object.keys(detail.owasp_applicable).length > 0 && <>
      <div className="graph-panel-section-label" style={{ marginTop: 14 }}>OWASP Top 10:2025</div>
      <div className="page-cats">{Object.entries(detail.owasp_applicable).map(([category, applicable]) => <div key={category} className="cat-row"><span className="cat-label" style={{ fontSize: 11 }}>{category} {OWASP_WEB_LABELS[category] || ''}</span><span className={'cat-badge ' + (applicable ? 'cat-yes' : 'cat-no')}>{applicable ? 'Yes' : 'No'}</span></div>)}</div>
    </>}
  </>;
}

function PageViews({ views, detail }) {
  return <><div className="graph-panel-section-label" style={{ marginTop: 14 }}>Views by User</div>{views.map(view => {
    const transcript = apiTranscriptText(view.page_text || detail.page_text);
    return <div key={view.id} className="credential-view-card"><div className="credential-view-label">{view.username || 'Anonymous'}</div>{view.screenshot_b64 && <img src={'data:image/png;base64,' + view.screenshot_b64} className="credential-view-screenshot" alt={'screenshot (' + view.username + ')'} />}{!view.screenshot_b64 && transcript && <><div className="api-transcript-label">API Request / Response</div><pre className="api-transcript">{transcript}</pre></>}<div className="credential-view-context">{view.llm_context || 'No context.'}</div></div>;
  })}</>;
}

function PageContext({ detail }) {
  const transcript = apiTranscriptText(detail.page_text);
  return <><div className="graph-panel-section-label" style={{ marginTop: 14 }}>LLM Context</div><div className="graph-panel-context">{detail.llm_context || 'No context available.'}</div>{detail.screenshot_b64 && <><div className="graph-panel-section-label" style={{ marginTop: 12 }}>Screenshot</div><img src={'data:image/png;base64,' + detail.screenshot_b64} style={{ width: '100%', borderRadius: 6, border: '1px solid var(--border)' }} alt="screenshot" /></>}{!detail.screenshot_b64 && transcript && <><div className="graph-panel-section-label" style={{ marginTop: 12 }}>API Request / Response</div><pre className="api-transcript">{transcript}</pre></>}{<PageStateEvidence detail={detail} />}</>;
}

function PageStateEvidence({ detail }) {
  return <>{detail.browser_replay && <><div className="graph-panel-section-label" style={{ marginTop: 14 }}>Replay</div><div className="graph-panel-context">{detail.state_kind === 'interactive' ? 'Interactive browser state' : 'URL with replay fallback'} · {detail.browser_replay.steps.length} deterministic steps</div></>}{detail.traffic?.length > 0 && <><div className="graph-panel-section-label" style={{ marginTop: 14 }}>Captured traffic</div><div className="graph-panel-context">{detail.traffic.slice(0, 8).map(item => <div key={item.id}>{item.method} {item.url} → {item.status ?? 'failed'}</div>)}</div></>}{detail.object_references?.length > 0 && <><div className="graph-panel-section-label" style={{ marginTop: 14 }}>Object references</div><div className="graph-panel-context">{detail.object_references.slice(0, 8).map(item => <div key={item.id}>{item.key}: {item.value}</div>)}</div></>}</>;
}
