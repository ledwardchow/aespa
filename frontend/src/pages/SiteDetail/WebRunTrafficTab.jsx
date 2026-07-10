import React, { useState, useRef } from "react";
import { parseDate } from "../../lib/utilities";

export function WebRunTrafficTab({ runId, traffic, setTraffic, api, lastTrafficIdRef, trafficColW, startTrafficResize, run, isDynamicScanActive, thinkingStatus, trafficTotal, selectedTraffic, setSelectedTraffic }) {
    const [trafficFilter, setTrafficFilter] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
    const [trafficSort, setTrafficSort] = useState({
    field: "_seq",
    dir: "asc"
  });

    const trafficTableRef = useRef(null);

    // ── Traffic helpers ────────────────────────────────────────────────────────
  const fmtRequest = e => {
    if (!e) return "";
    const u = new URL(e.url);
    const path = u.pathname + u.search;
    const hdrs = Object.entries(e.request_headers || {}).map(([k, v]) => `${k}: ${v}`).join("\n");
    return `${e.method} ${path} HTTP/1.1\nHost: ${u.host}\n${hdrs}${e.request_body ? "\n\n" + e.request_body : ""}`;
  };
  const fmtResponse = e => {
    if (!e) return "";
    const hdrs = Object.entries(e.response_headers || {}).map(([k, v]) => `${k}: ${v}`).join("\n");
    return `HTTP/1.1 ${e.status ?? ""}\n${hdrs}${e.response_body ? "\n\n" + e.response_body : ""}`;
  };
  const statusClass = s => !s ? "" : s < 300 ? "tr-2xx" : s < 400 ? "tr-3xx" : s < 500 ? "tr-4xx" : "tr-5xx";
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
  const sortArrow = field => trafficSort.field === field ? <span className="sort-arrow">{trafficSort.dir === "asc" ? "▲" : "▼"}</span> : "";
  const fmtTs = iso => {
    try {
      const d = parseDate(iso);
      return d.toTimeString().slice(0, 8) + "." + String(d.getMilliseconds()).padStart(3, "0");
    } catch {
      return iso || "";
    }
  };

  


  

  return (
    <div className="traffic-panel">
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
          }}>Clear</button>
          </div>

          <div className="traffic-table-wrap" ref={trafficTableRef}>
            <table className="traffic-table">
              <colgroup>{trafficColW.map((w, i) => <col key={i} style={{
                width: w != null ? w + "px" : undefined
              }} />)}</colgroup>
              <thead>
                <tr>
                  <th className="sortable tr-num" onClick={() => onTrafficSort("_seq")}>#{sortArrow("_seq")}<div className="col-rh" onMouseDown={e => startTrafficResize(0, e)} onClick={e => e.stopPropagation()} /></th>
                  <th className="sortable tr-ts" onClick={() => onTrafficSort("created_at")}>Time{sortArrow("created_at")}<div className="col-rh" onMouseDown={e => startTrafficResize(1, e)} onClick={e => e.stopPropagation()} /></th>
                  <th className="sortable" onClick={() => onTrafficSort("source")}>Source{sortArrow("source")}<div className="col-rh" onMouseDown={e => startTrafficResize(2, e)} onClick={e => e.stopPropagation()} /></th>
                  <th className="sortable" onClick={() => onTrafficSort("username")}>User{sortArrow("username")}<div className="col-rh" onMouseDown={e => startTrafficResize(3, e)} onClick={e => e.stopPropagation()} /></th>
                  <th className="sortable" onClick={() => onTrafficSort("method")}>Method{sortArrow("method")}<div className="col-rh" onMouseDown={e => startTrafficResize(4, e)} onClick={e => e.stopPropagation()} /></th>
                  <th className="sortable" onClick={() => onTrafficSort("status")}>Status{sortArrow("status")}<div className="col-rh" onMouseDown={e => startTrafficResize(5, e)} onClick={e => e.stopPropagation()} /></th>
                  <th className="sortable" onClick={() => onTrafficSort("url")}>URL{sortArrow("url")}<div className="col-rh" onMouseDown={e => startTrafficResize(6, e)} onClick={e => e.stopPropagation()} /></th>
                  <th className="sortable tr-dur" onClick={() => onTrafficSort("duration_ms")}>Duration{sortArrow("duration_ms")}<div className="col-rh" onMouseDown={e => startTrafficResize(7, e)} onClick={e => e.stopPropagation()} /></th>
                </tr>
              </thead>
              <tbody>
                {filteredTraffic.map((e, i) => <tr key={e.id} className={"traffic-row" + (selectedTraffic?.id === e.id ? " selected" : "")} onClick={() => setSelectedTraffic(selectedTraffic?.id === e.id ? null : e)}>
                    <td className="tr-num">{e._seq ?? i + 1}</td>
                    <td className="tr-ts">{fmtTs(e.created_at)}</td>
                    <td><span className={"src-badge src-" + e.source}>{e.source}</span></td>
                    <td className="tr-user">{e.username || "-"}</td>
                    <td className="tr-method">{e.method}</td>
                    <td><span className={"status-pill " + statusClass(e.status)}>{e.status ?? "-"}</span></td>
                    <td className="tr-url" title={e.url}>{e.url}</td>
                    <td className="tr-dur">{e.duration_ms != null ? e.duration_ms + "ms" : "-"}</td>
                  </tr>)}
              </tbody>
            </table>
            {filteredTraffic.length === 0 && <div className="subtle" style={{
            padding: "24px",
            textAlign: "center"
          }}>
                {run?.status === "running" || isDynamicScanActive(thinkingStatus?.status) ? "Capturing traffic…" : "No traffic recorded yet. Start a crawl or scan."}
              </div>}
          </div>

          {selectedTraffic && <div className="traffic-detail">
              <div className="traffic-pane">
                <div className="traffic-pane-label">REQUEST — {selectedTraffic.method} {selectedTraffic.url}</div>
                <pre className="traffic-raw">{fmtRequest(selectedTraffic)}</pre>
              </div>
              <div className="traffic-pane">
                <div className="traffic-pane-label">RESPONSE — {selectedTraffic.status ?? "-"} {selectedTraffic.duration_ms != null ? "(" + selectedTraffic.duration_ms + "ms)" : ""}</div>
                <pre className="traffic-raw">{fmtResponse(selectedTraffic)}</pre>
              </div>
            </div>}
        </div>
  );
}
