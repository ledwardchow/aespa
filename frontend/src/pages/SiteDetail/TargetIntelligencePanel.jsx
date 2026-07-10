import { useColResize } from "../SiteDetail";
import { truncUrl } from "../../lib/utilities";

export function TargetIntelligencePanel({
  data,
  selectedKind,
  onKind,
  refresh,
  onClear,
  clearing
}) {
  const [intelColW, startIntelResize] = useColResize("colw:intel", [116, 86, 120, null, 130, 82]);
  const counts = data?.counts || {};
  const items = data?.items || [];
  const kinds = ["", ...Object.keys(counts).sort()];
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const KIND_LABELS = {
    endpoint: "Endpoints",
    form: "Forms",
    input: "Inputs",
    script: "Scripts",
    storage_key: "Storage Keys",
    id: "IDs",
    response_field: "Response Fields"
  };
  const kindLabel = k => k ? KIND_LABELS[k] || k.replace(/_/g, " ") : "All";
  const compactMeta = meta => {
    if (!meta || Object.keys(meta).length === 0) return "";
    const shown = Object.entries(meta).filter(([k]) => !["fields"].includes(k)).slice(0, 5).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.length + " item(s)" : String(v).slice(0, 80)}`);
    return shown.join(" · ");
  };
  return <div className="intel-panel">
      <div className="intel-toolbar">
        <div className="intel-title">
          <span>Target Intelligence</span>
          <span className="subtle">{total} item{total === 1 ? "" : "s"} discovered during crawl</span>
        </div>
        <div className="intel-filter">
          <label>Kind</label>
          <select className="select" value={selectedKind} onChange={e => onKind(e.target.value)}>
            {kinds.map(k => <option key={k || "all"} value={k}>{kindLabel(k)}{k ? ` (${counts[k] || 0})` : ""}</option>)}
          </select>
          <button className="btn ghost sm" onClick={refresh}>Refresh</button>
          {total > 0 && <button className="btn danger-outline sm" disabled={clearing} onClick={onClear}>{clearing ? "Clearing…" : "Clear"}</button>}
        </div>
      </div>

      <div className="intel-counts">
        {Object.entries(counts).sort(([a], [b]) => a.localeCompare(b)).map(([kind, count]) => <button key={kind} className={"intel-count-card" + (selectedKind === kind ? " active" : "")} onClick={() => onKind(selectedKind === kind ? "" : kind)}>
            <span className="intel-count-value">{count}</span>
            <span className="intel-count-label">{kindLabel(kind)}</span>
          </button>)}
        {total === 0 && <div className="subtle">No target intelligence has been collected yet. Start or restart a crawl to populate the inventory.</div>}
      </div>

      <div className="intel-table-wrap">
        <table className="intel-table">
          <colgroup>{intelColW.map((w, i) => <col key={i} style={{
            width: w != null ? w + "px" : undefined
          }} />)}</colgroup>
          <thead>
            <tr>
              <th>Kind <div className="col-rh" onMouseDown={e => startIntelResize(0, e)} onClick={e => e.stopPropagation()} /></th>
              <th>Method <div className="col-rh" onMouseDown={e => startIntelResize(1, e)} onClick={e => e.stopPropagation()} /></th>
              <th>Key <div className="col-rh" onMouseDown={e => startIntelResize(2, e)} onClick={e => e.stopPropagation()} /></th>
              <th>Value <div className="col-rh" onMouseDown={e => startIntelResize(3, e)} onClick={e => e.stopPropagation()} /></th>
              <th>Source <div className="col-rh" onMouseDown={e => startIntelResize(4, e)} onClick={e => e.stopPropagation()} /></th>
              <th>Conf. <div className="col-rh" onMouseDown={e => startIntelResize(5, e)} onClick={e => e.stopPropagation()} /></th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => <tr key={item.id}>
                <td><span className="intel-kind">{kindLabel(item.kind)}</span></td>
                <td><span className="mono">{item.method || "-"}</span></td>
                <td>
                  <div className="intel-primary" title={item.key}>{item.key || "—"}</div>
                  {item.url && <div className="intel-url mono" title={item.url}>{truncUrl(item.url, 72)}</div>}
                </td>
                <td>
                  <div className="intel-value" title={item.value}>{item.value || "—"}</div>
                  {item.evidence && <div className="intel-evidence">{item.evidence}</div>}
                  {compactMeta(item.item_metadata) && <div className="intel-meta">{compactMeta(item.item_metadata)}</div>}
                </td>
                <td>{item.source}</td>
                <td>{Math.round((item.confidence ?? 0) * 100)}%</td>
              </tr>)}
          </tbody>
        </table>
        {items.length === 0 && total > 0 && <div className="subtle" style={{
        padding: "24px",
        textAlign: "center"
      }}>No items match this filter.</div>}
      </div>
    </div>;
}
