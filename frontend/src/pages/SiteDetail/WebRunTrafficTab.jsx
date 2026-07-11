import React, { useCallback, useEffect, useState, useRef } from "react";
import { api } from "../../lib/api";
import { usePolling } from "../../hooks/usePolling";
import { useColResize } from "./_helpers";
import { TrafficDetail, TrafficTable } from "../../components/TrafficView";

export function WebRunTrafficTab({ runId, active, captureActive, runStatus, onTotalChange }) {
  const [traffic, setTraffic] = useState([]);
  const [trafficTotal, setTrafficTotal] = useState(0);
  const [selectedTraffic, setSelectedTraffic] = useState(null);
  const [trafficFilter, setTrafficFilter] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const [trafficSort, setTrafficSort] = useState({
    field: "_seq",
    dir: "asc"
  });
  const trafficTableRef = useRef(null);
  const lastTrafficIdRef = useRef(0);
  const [trafficColW, startTrafficResize] = useColResize("colw:traffic:v2", [30, 88, 68, 70, 62, 52, null, 66]);

  const updateTotal = useCallback(total => {
    setTrafficTotal(total);
    onTotalChange(total);
  }, [onTotalChange]);

  useEffect(() => {
    setTraffic([]);
    lastTrafficIdRef.current = 0;
    setSelectedTraffic(null);
    api.getTrafficCount(runId).then(result => updateTotal(result.count || 0)).catch(() => {});
  }, [runId, updateTotal]);

  const pollTraffic = useCallback(async () => {
    try {
      const entries = await api.getTraffic(runId, lastTrafficIdRef.current);
      if (entries.length > 0) {
        lastTrafficIdRef.current = entries[entries.length - 1].id;
        setTraffic(previous => {
          const stamped = entries.map((entry, index) => ({
            ...entry,
            _seq: previous.length + index + 1
          }));
          const next = [...previous, ...stamped];
          return next.length > 2000 ? next.slice(-2000) : next;
        });
      }
      if (active || entries.length > 0) {
        const result = await api.getTrafficCount(runId);
        updateTotal(result.count || 0);
      }
    } catch {}
  }, [active, runId, updateTotal]);
  const pollingActive = active || captureActive;
  usePolling(pollTraffic, {
    enabled: pollingActive,
    immediate: pollingActive,
    intervalMs: 2000
  });

    // ── Traffic helpers ────────────────────────────────────────────────────────
  const filteredTraffic = (() => {
    let list = trafficFilter ? traffic.filter(e => e.url.toLowerCase().includes(trafficFilter.toLowerCase()) || (e.method || "").toLowerCase().includes(trafficFilter.toLowerCase()) || String(e.status || "").includes(trafficFilter) || (e.source || "").toLowerCase().includes(trafficFilter.toLowerCase())) : traffic;
    const {
      field,
      dir
    } = trafficSort;
    const mul = dir === "asc" ? 1 : -1;
    const numeric = new Set(["_seq", "status", "duration_ms", "id"]);
    list = [...list].sort((a, b) => {
      let av = a[field],
        bv = b[field];
      if (numeric.has(field)) {
        av = av ?? -1;
        bv = bv ?? -1;
        return (av - bv) * mul;
      }
      return String(av ?? "").localeCompare(String(bv ?? "")) * mul;
    });
    return list;
  })();
  const onTrafficSort = field => setTrafficSort(prev => prev.field === field ? {
    field,
    dir: prev.dir === "asc" ? "desc" : "asc"
  } : {
    field,
    dir: "asc"
  });
  return (
    <div className="traffic-panel" style={{ display: active ? undefined : "none" }}>
      <div className="traffic-toolbar">
            <input className="traffic-filter" type="text" placeholder="Filter by URL, method or status…" value={trafficFilter} onInput={e => setTrafficFilter(e.target.value)} />
            <span className="traffic-count-label">{filteredTraffic.length} shown{trafficTotal > filteredTraffic.length ? ` of ${trafficTotal}` : ""}</span>
            <label className="traffic-autoscroll">
              <input type="checkbox" checked={autoScroll} onChange={e => setAutoScroll(e.target.checked)} />
              Auto-scroll
            </label>
            <button className="btn ghost sm" onClick={async () => {
            try {
              await api.clearTraffic(runId);
            } catch  {}
            setTraffic([]);
            lastTrafficIdRef.current = 0;
            setSelectedTraffic(null);
            updateTotal(0);
          }}>Clear</button>
          </div>

          <div className="traffic-table-wrap" ref={trafficTableRef}>
            <TrafficTable entries={filteredTraffic} selected={selectedTraffic} onSelect={setSelectedTraffic} sequenceFor={(entry, index) => entry._seq ?? index + 1} sortable sort={trafficSort} onSort={onTrafficSort} widths={trafficColW} onResizeStart={startTrafficResize} />
            {filteredTraffic.length === 0 && <div className="subtle" style={{
            padding: "24px",
            textAlign: "center"
          }}>
                {runStatus === "running" || captureActive ? "Capturing traffic…" : "No traffic recorded yet. Start a crawl or scan."}
              </div>}
          </div>
          <TrafficDetail entry={selectedTraffic} onClose={() => setSelectedTraffic(null)} />
        </div>
  );
}
