import { useState } from "react";
import { api } from "../../lib/api";
import { apiTranscriptText } from "../../lib/utilities";
import { OWASP_WEB_LABELS } from "./_constants";
import { SCOPE_IN_COLOR, SCOPE_OUT_COLOR, USER_BOTH_COLOR, USER_PALETTE } from "./_helpers";
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

  return <div className="graph-layout" style={{ display: active ? "flex" : "none" }}>
    <div className="graph-canvas-wrap">
      {graph && graph.nodes.length === 0 && <div className="graph-empty">
        <WebRunSitemapTab activeTab="sitemap" run={run} onStart={onStart} onStartThinkingScan={onStartThinkingScan} hasCheckpoint={hasCheckpoint} onResumeThinkingScan={onResumeThinkingScan} checkpointStatus={checkpointStatus} />
      </div>}
      <svg ref={svgRef} className="graph-svg" width="100%" height="100%" style={{ pointerEvents: !graph || graph.nodes.length === 0 ? "none" : "all" }} />
      {graph && graph.nodes.length > 0 && <div className="graph-legend">
        {graphView === "user" && run?.credentials?.length > 1 ? <>
          {(run.credentials || []).map((credential, index) => <div key={credential.id} className="legend-item"><span className="legend-dot" style={{ background: USER_PALETTE[index % USER_PALETTE.length] }} />{credential.label || credential.username}</div>)}
          <div className="legend-item"><span className="legend-dot" style={{ background: USER_BOTH_COLOR }} />All users</div>
        </> : <>
          <div className="legend-item"><span className="legend-dot" style={{ background: SCOPE_IN_COLOR }} />In Scope</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: SCOPE_OUT_COLOR }} />Out of Scope</div>
          <div className="legend-item"><span className="legend-dot" style={{ background: "var(--bg)", border: "2px solid #fbbf24" }} />Failed</div>
        </>}
      </div>}
    </div>
    {selectedNode && <SitemapPageInspector
      node={selectedNode} detail={pageDetail} views={pageViews} cascade={cascade} scopeBusy={scopeBusy}
      onCascade={setCascade} onClose={() => setSelectedNode(null)} onToggleScope={toggleScope} onDelete={deleteNode}
    />}
  </div>;
}

function SitemapPageInspector({ node, detail, views, cascade, scopeBusy, onCascade, onClose, onToggleScope, onDelete }) {
  return <div className="graph-panel">
    <div className="graph-panel-header"><div className="graph-panel-url">{node.url}</div><button className="btn ghost sm" onClick={onClose}>✕</button></div>
    {detail ? <div className="graph-panel-body">
      {detail.title && <div className="graph-panel-title">{detail.title}</div>}
      <div className="graph-panel-section-label">Scope</div>
      <div className="scope-row">
        <span className={'scope-badge ' + (node.in_scope === false ? 'out' : 'in')}>{node.in_scope === false ? 'Out of Scope' : 'In Scope'}</span>
        <button className="btn sm" onClick={onToggleScope} disabled={scopeBusy}>{scopeBusy ? '…' : node.in_scope === false ? 'Mark in scope' : 'Mark out of scope'}</button>
        <button className="btn danger-outline sm" onClick={onDelete} disabled={scopeBusy} title="Delete this node (and children if checkbox is ticked)">🗑</button>
      </div>
      <label className="scope-cascade-label"><input type="checkbox" checked={cascade} onChange={event => onCascade(event.target.checked)} />Also apply to all children</label>
      <PageCategories detail={detail} />
      {views.length > 0 ? <PageViews views={views} detail={detail} /> : <PageContext detail={detail} />}
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
  return <><div className="graph-panel-section-label" style={{ marginTop: 14 }}>LLM Context</div><div className="graph-panel-context">{detail.llm_context || 'No context available.'}</div>{detail.screenshot_b64 && <><div className="graph-panel-section-label" style={{ marginTop: 12 }}>Screenshot</div><img src={'data:image/png;base64,' + detail.screenshot_b64} style={{ width: '100%', borderRadius: 6, border: '1px solid var(--border)' }} alt="screenshot" /></>}{!detail.screenshot_b64 && transcript && <><div className="graph-panel-section-label" style={{ marginTop: 12 }}>API Request / Response</div><pre className="api-transcript">{transcript}</pre></>}</>;
}
