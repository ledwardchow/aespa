import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../../lib/api";
import { usePolling } from "../../hooks/usePolling";


export function ApiRunTrafficTab({
  runId,
  scanRunning
}) {
  const [traffic, setTraffic] = useState([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const lastIdRef = useRef(0);
  const tableRef = useRef(null);
  const loadMore = useCallback(async () => {
    try {
      const items = await api.getApiTraffic(runId, lastIdRef.current);
      if (items.length) {
        setTraffic(prev => {
          const next = [...prev, ...items];
          lastIdRef.current = Math.max(...next.map(e => e.id));
          return next;
        });
      }
      const ct = await api.getApiTrafficCount(runId);
      setTotal(ct.count || 0);
    } catch {}
  }, [runId]);
  usePolling(loadMore, { enabled: scanRunning, intervalMs: 4000 });
  useEffect(() => {
    if (autoScroll && tableRef.current) {
      tableRef.current.scrollTop = tableRef.current.scrollHeight;
    }
  }, [traffic.length, autoScroll]);
  const fmtTs = ts => {
    if (!ts) return "-";
    try {
      return new Date(ts).toLocaleTimeString();
    } catch {
      return ts;
    }
  };
  const statusCls = s => !s ? "" : s < 300 ? "status-2xx" : s < 400 ? "status-3xx" : s < 500 ? "status-4xx" : "status-5xx";
  const filtered = filter ? traffic.filter(e => (e.url + e.method + (e.status ?? "") + e.source).toLowerCase().includes(filter.toLowerCase())) : traffic;
  return <div style={{
    display: "flex",
    flexDirection: "column",
    height: "calc(100vh - 130px)"
  }}>
      <div style={{
      display: "flex",
      alignItems: "center",
      gap: 8,
      padding: "8px 16px",
      borderBottom: "1px solid var(--border)",
      flexShrink: 0
    }}>
        <input className="traffic-filter" type="text" placeholder="Filter…" value={filter} onInput={e => setFilter(e.target.value)} style={{
        flex: 1
      }} />
        <span className="traffic-count-label">{filtered.length} shown{total > filtered.length ? ` of ${total}` : ""}</span>
        <label style={{
        fontSize: 12,
        display: "flex",
        alignItems: "center",
        gap: 4
      }}>
          <input type="checkbox" checked={autoScroll} onChange={e => setAutoScroll(e.target.checked)} />
          Auto-scroll
        </label>
        <button className="btn ghost sm" onClick={() => {
        setTraffic([]);
        lastIdRef.current = 0;
        setSelected(null);
      }}>Clear</button>
      </div>
      <div style={{
      flex: 1,
      overflow: "auto"
    }} ref={tableRef}>
        <table className="traffic-table" style={{
        width: "100%",
        tableLayout: "fixed"
      }}>
          <colgroup>
            <col style={{
            width: "32px"
          }} />
            <col style={{
            width: "82px"
          }} />
            <col style={{
            width: "68px"
          }} />
            <col style={{
            width: "90px"
          }} />
            <col style={{
            width: "68px"
          }} />
            <col style={{
            width: "56px"
          }} />
            <col />
            <col style={{
            width: "72px"
          }} />
          </colgroup>
          <thead>
            <tr>
              <th>#</th><th>Time</th><th>Source</th><th>User</th>
              <th>Method</th><th>Status</th><th>URL</th><th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((e, i) => <tr key={e.id} className={"traffic-row" + (selected?.id === e.id ? " selected" : "")} onClick={() => setSelected(selected?.id === e.id ? null : e)}>
                <td className="tr-num">{i + 1}</td>
                <td className="tr-ts">{fmtTs(e.created_at)}</td>
                <td><span className={"src-badge src-" + e.source}>{e.source}</span></td>
                <td className="tr-user">{e.username || "-"}</td>
                <td className="tr-method">{e.method}</td>
                <td><span className={"status-pill " + statusCls(e.status)}>{e.status ?? "-"}</span></td>
                <td className="tr-url" title={e.url}>{e.url}</td>
                <td className="tr-dur">{e.duration_ms != null ? e.duration_ms + "ms" : "-"}</td>
              </tr>)}
          </tbody>
        </table>
        {filtered.length === 0 && <div className="subtle" style={{
        padding: 24,
        textAlign: "center"
      }}>
            {scanRunning ? "Capturing traffic…" : "No traffic recorded yet. Start a scan to generate traffic."}
          </div>}
      </div>
      {selected && <div style={{
      flexShrink: 0,
      borderTop: "2px solid var(--accent)",
      padding: "10px 16px",
      maxHeight: 220,
      overflow: "auto",
      background: "var(--surface)"
    }}>
          <div style={{
        display: "flex",
        justifyContent: "space-between",
        marginBottom: 6
      }}>
            <b style={{
          fontSize: 13
        }}>{selected.method} {selected.url}</b>
            <button className="btn ghost sm" onClick={() => setSelected(null)}>✕</button>
          </div>
          {selected.request_body && <div style={{
        marginBottom: 6
      }}><b style={{
          fontSize: 11
        }}>Request Body:</b>
            <pre style={{
          fontSize: 10,
          background: "var(--code-bg,#1e1e2e)",
          color: "var(--code-fg,#cdd6f4)",
          padding: 6,
          borderRadius: 4,
          overflow: "auto",
          maxHeight: 80,
          margin: "2px 0",
          whiteSpace: "pre-wrap"
        }}>{selected.request_body}</pre></div>}
          {selected.response_body && <div><b style={{
          fontSize: 11
        }}>Response Body:</b>
            <pre style={{
          fontSize: 10,
          background: "var(--code-bg,#1e1e2e)",
          color: "var(--code-fg,#cdd6f4)",
          padding: 6,
          borderRadius: 4,
          overflow: "auto",
          maxHeight: 80,
          margin: "2px 0",
          whiteSpace: "pre-wrap"
        }}>{selected.response_body?.slice(0, 2000)}</pre></div>}
        </div>}
    </div>;
}

// Build the agent list from a raw agent-log API response, preserving task history.
