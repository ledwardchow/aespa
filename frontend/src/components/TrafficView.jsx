import { parseDate } from "../lib/utilities";

const statusClass = status => !status ? "" : status < 300 ? "tr-2xx" : status < 400 ? "tr-3xx" : status < 500 ? "tr-4xx" : "tr-5xx";
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
  if (!entry) return null;
  return <div className="traffic-detail"><div className="traffic-pane"><div className="traffic-pane-label">REQUEST — {entry.method} {entry.url}<button className="btn ghost sm" onClick={onClose}>✕</button></div><pre className="traffic-raw">{rawRequest(entry)}</pre></div><div className="traffic-pane"><div className="traffic-pane-label">RESPONSE — {entry.status ?? '-'} {entry.duration_ms != null ? '(' + entry.duration_ms + 'ms)' : ''}</div><pre className="traffic-raw">{rawResponse(entry)}</pre></div></div>;
}
