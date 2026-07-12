import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../../lib/api";
import { useIncrementalCollection } from "../../hooks/useIncrementalCollection";
import { TrafficDetail, TrafficTable } from "../../components/TrafficView";


export function ApiRunTrafficTab({
  runId,
  scanRunning
}) {
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const tableRef = useRef(null);
  const loadAfter = useCallback(cursor => api.getApiTraffic(runId, cursor), [runId]);
  const { items: traffic, reset } = useIncrementalCollection(loadAfter, { enabled: scanRunning, intervalMs: 4000 });
  const refreshTotal = useCallback(() => api.getApiTrafficCount(runId).then(result => setTotal(result.count || 0)).catch(() => {}), [runId]);
  useEffect(() => { refreshTotal(); }, [refreshTotal, traffic.length]);
  useEffect(() => {
    if (autoScroll && tableRef.current) {
      tableRef.current.scrollTop = tableRef.current.scrollHeight;
    }
  }, [traffic.length, autoScroll]);
  const filtered = filter ? traffic.filter(entry => (entry.url + entry.method + (entry.status ?? "") + entry.source).toLowerCase().includes(filter.toLowerCase())) : traffic;
  return <div className="traffic-panel" style={{ height: "calc(100vh - 130px)" }}>
    <div className="traffic-toolbar"><input className="traffic-filter" placeholder="Filter…" value={filter} onInput={event => setFilter(event.target.value)} /><span className="traffic-count-label">{filtered.length} shown{total > filtered.length ? ` of ${total}` : ""}</span><label className="traffic-autoscroll"><input type="checkbox" checked={autoScroll} onChange={event => setAutoScroll(event.target.checked)} />Auto-scroll</label><button className="btn ghost sm" onClick={() => { reset(); setSelected(null); }}>Clear</button></div>
    <div className="traffic-table-wrap" ref={tableRef}><TrafficTable entries={filtered} selected={selected} onSelect={setSelected} sequenceFor={(_, index) => index + 1} />{filtered.length === 0 && <div className="subtle" style={{ padding: 24, textAlign: "center" }}>{scanRunning ? "Capturing traffic…" : "No traffic recorded yet. Start a scan to generate traffic."}</div>}</div>
    <TrafficDetail entry={selected} onClose={() => setSelected(null)} />
  </div>;
}

// Build the agent list from a raw agent-log API response, preserving task history.
