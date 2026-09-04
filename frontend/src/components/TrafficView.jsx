import { useRef, useState } from "react";
import { parseDate } from "../lib/utilities";

const statusClass = status => !status ? "" : status < 300 ? "tr-2xx" : status < 400 ? "tr-3xx" : status < 500 ? "tr-4xx" : "tr-5xx";
const TRAFFIC_LAYOUT_KEY = "traffic-layout:v1";
const MIN_DETAIL_HEIGHT = 20;
const MAX_DETAIL_HEIGHT = 80;
const MIN_PANE_WIDTH = 20;
const MAX_PANE_WIDTH = 80;
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const defaultTrafficLayout = { detailHeight: null, requestWidth: 50 };

function readTrafficLayout() {
  try {
    const saved = JSON.parse(localStorage.getItem(TRAFFIC_LAYOUT_KEY) || "null");
    return {
      detailHeight: Number.isFinite(saved?.detailHeight) ? clamp(saved.detailHeight, MIN_DETAIL_HEIGHT, MAX_DETAIL_HEIGHT) : null,
      requestWidth: Number.isFinite(saved?.requestWidth) ? clamp(saved.requestWidth, MIN_PANE_WIDTH, MAX_PANE_WIDTH) : defaultTrafficLayout.requestWidth
    };
  } catch {
    return defaultTrafficLayout;
  }
}

const formatTime = value => {
  try {
    const date = parseDate(value);
    return date.toTimeString().slice(0, 8) + "." + String(date.getMilliseconds()).padStart(3, "0");
  } catch { return value || ""; }
};
const rawRequest = entry => {
  const url = new URL(entry.url);
  const headers = Object.entries(entry.request_headers || {}).map(([key, value]) => `${key}: ${value}`).join("\n");
  return `${entry.method} ${url.pathname}${url.search} HTTP/1.1\nHost: ${url.host}\n${headers}${entry.request_body ? "\n\n" + entry.request_body : ""}`;
};
const rawResponse = entry => {
  const headers = Object.entries(entry.response_headers || {}).map(([key, value]) => `${key}: ${value}`).join("\n");
  return `HTTP/1.1 ${entry.status ?? ""}\n${headers}${entry.response_body ? "\n\n" + entry.response_body : ""}`;
};

export function TrafficTable({ entries, selected, onSelect, sequenceFor, sortable = false, sort, onSort, widths, onResizeStart }) {
  const arrow = field => sort?.field === field ? <span className="sort-arrow">{sort.dir === "asc" ? "▲" : "▼"}</span> : "";
  const header = (label, field, index, className = "") => <th className={(sortable ? "sortable " : "") + className} onClick={sortable ? () => onSort(field) : undefined}>{label}{arrow(field)}{onResizeStart && <div className="col-rh" onMouseDown={event => onResizeStart(index, event)} onClick={event => event.stopPropagation()} />}</th>;
  return <table className="traffic-table"><colgroup>{widths?.map((width, index) => <col key={index} style={{ width: width != null ? width + "px" : undefined }} />)}</colgroup><thead><tr>{header("#", "_seq", 0, "tr-num")}{header("Time", "created_at", 1, "tr-ts")}{header("Source", "source", 2)}{header("User", "username", 3)}{header("Method", "method", 4)}{header("Status", "status", 5)}{header("URL", "url", 6)}{header("Duration", "duration_ms", 7, "tr-dur")}</tr></thead><tbody>{entries.map((entry, index) => <tr key={entry.id} className={'traffic-row' + (selected?.id === entry.id ? ' selected' : '')} onClick={() => onSelect(selected?.id === entry.id ? null : entry)}><td className="tr-num">{sequenceFor(entry, index)}</td><td className="tr-ts">{formatTime(entry.created_at)}</td><td><span className={'src-badge src-' + entry.source}>{entry.source}</span></td><td className="tr-user">{entry.username || '-'}</td><td className="tr-method">{entry.method}</td><td><span className={'status-pill ' + statusClass(entry.status)}>{entry.status ?? '-'}</span></td><td className="tr-url" title={entry.url}>{entry.url}</td><td className="tr-dur">{entry.duration_ms != null ? entry.duration_ms + 'ms' : '-'}</td></tr>)}</tbody></table>;
}

export function TrafficDetail({ entry, onClose }) {
  const [layout, setLayout] = useState(readTrafficLayout);
  const layoutRef = useRef(layout);
  const detailWrapRef = useRef(null);
  const detailRef = useRef(null);
  if (!entry) return null;

  const updateLayout = patch => {
    const next = { ...layoutRef.current, ...patch };
    layoutRef.current = next;
    setLayout(next);
  };
  const saveLayout = () => {
    try {
      localStorage.setItem(TRAFFIC_LAYOUT_KEY, JSON.stringify(layoutRef.current));
    } catch {}
  };
  const startResize = (event, axis) => {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.clientX;
    const startY = event.clientY;
    const panel = detailWrapRef.current?.parentElement;
    const detailWrap = detailWrapRef.current;
    const detail = detailRef.current;
    const panelRect = panel?.getBoundingClientRect();
    const detailRect = detail?.getBoundingClientRect();
    const startDetailHeight = detailWrap?.getBoundingClientRect().height || detailRect?.height || 0;
    const startRequestWidth = layoutRef.current.requestWidth;
    const availableWidth = Math.max(1, (detailRect?.width || 1) - 8);
    const panelHeight = panelRect?.height || 1;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = axis === "y" ? "row-resize" : "col-resize";
    document.body.style.userSelect = "none";

    const onMove = moveEvent => {
      if (axis === "y") {
        const nextHeight = clamp(startDetailHeight - (moveEvent.clientY - startY), panelHeight * MIN_DETAIL_HEIGHT / 100, panelHeight * MAX_DETAIL_HEIGHT / 100);
        updateLayout({ detailHeight: nextHeight / panelHeight * 100 });
      } else {
        const nextWidth = clamp(startRequestWidth + (moveEvent.clientX - startX) / availableWidth * 100, MIN_PANE_WIDTH, MAX_PANE_WIDTH);
        updateLayout({ requestWidth: nextWidth });
      }
    };
    const onEnd = () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onEnd);
      document.removeEventListener("pointercancel", onEnd);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      saveLayout();
    };
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onEnd);
    document.addEventListener("pointercancel", onEnd);
  };
  const adjustLayout = (axis, direction) => {
    if (axis === "y") {
      updateLayout({ detailHeight: clamp((layout.detailHeight ?? 50) + direction * 2, MIN_DETAIL_HEIGHT, MAX_DETAIL_HEIGHT) });
    } else {
      updateLayout({ requestWidth: clamp(layout.requestWidth + direction * 2, MIN_PANE_WIDTH, MAX_PANE_WIDTH) });
    }
    saveLayout();
  };
  const handleKeyDown = (event, axis) => {
    const direction = axis === "y"
      ? event.key === "ArrowUp" ? 1 : event.key === "ArrowDown" ? -1 : 0
      : event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!direction) return;
    event.preventDefault();
    adjustLayout(axis, direction);
  };
  const detailHeight = layout.detailHeight == null ? undefined : { flex: `0 0 ${layout.detailHeight}%` };
  const requestWidth = layout.requestWidth;
  const executionLabel = entry.code_execution_id
    ? `Python execution #${entry.code_execution_id}${entry.batch_id ? ` · batch ${entry.batch_id}${entry.batch_index != null ? ` [${entry.batch_index}]` : ""}` : ""}${entry.agent_id ? ` · ${entry.agent_id}${entry.agent_step != null ? ` step ${entry.agent_step}` : ""}` : ""}`
    : null;
  return <div className="traffic-detail-wrap" ref={detailWrapRef} style={detailHeight}>
    {executionLabel && <div className="traffic-provenance">{executionLabel}{entry.owasp_category ? ` · ${entry.owasp_category}` : ""}{entry.test_class ? ` · ${entry.test_class}` : ""}</div>}
    <div className="traffic-detail-resizer" role="separator" aria-label="Resize request and response display height" aria-orientation="horizontal" aria-valuemin={MIN_DETAIL_HEIGHT} aria-valuemax={MAX_DETAIL_HEIGHT} aria-valuenow={Math.round(layout.detailHeight ?? 50)} tabIndex="0" onPointerDown={event => startResize(event, "y")} onKeyDown={event => handleKeyDown(event, "y")}><span className="traffic-resizer-grip" aria-hidden="true" /></div>
    <div className="traffic-detail" ref={detailRef} style={{ gridTemplateColumns: `minmax(0, ${requestWidth}fr) 8px minmax(0, ${100 - requestWidth}fr)` }}>
      <div className="traffic-pane"><div className="traffic-pane-label">REQUEST — {entry.method} {entry.url}</div><pre className="traffic-raw">{rawRequest(entry)}</pre></div>
      <div className="traffic-pane-divider" role="separator" aria-label="Resize request and response panels" aria-orientation="vertical" aria-valuemin={MIN_PANE_WIDTH} aria-valuemax={MAX_PANE_WIDTH} aria-valuenow={Math.round(requestWidth)} tabIndex="0" onPointerDown={event => startResize(event, "x")} onKeyDown={event => handleKeyDown(event, "x")}><span className="traffic-resizer-grip" aria-hidden="true" /></div>
      <div className="traffic-pane"><div className="traffic-pane-label"><span>RESPONSE — {entry.status ?? '-'} {entry.duration_ms != null ? '(' + entry.duration_ms + 'ms)' : ''}</span><button className="btn ghost sm" onClick={onClose} style={{marginLeft:'auto', paddingRight:'8px'}}>✕</button></div><pre className="traffic-raw">{rawResponse(entry)}</pre></div>
    </div>
  </div>;
}
