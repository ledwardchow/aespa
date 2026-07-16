import { useColResize } from "./_helpers";
import { parseDate } from "../../lib/utilities";

export function ScannerSessionsPanel({
  data,
  refresh,
  onUpdate
}) {
  const [sessColW, startSessResize] = useColResize("colw:sessions", [150, 100, 180, null, 180, 170, 150]);
  const sessions = data?.sessions || [];
  const counts = data?.counts || {};
  const kinds = Object.entries(counts).filter(([kind]) => !["total", "active", "inactive"].includes(kind)).sort(([a], [b]) => a.localeCompare(b));
  const fmtAge = iso => {
    if (!iso) return "—";
    try {
      return parseDate(iso).toLocaleString();
    } catch {
      return iso;
    }
  };
  const renameSession = async session => {
    const next = prompt("Session label", session.label);
    if (next === null) return;
    try {
      await onUpdate(session.id, {
        label: next
      });
      await refresh();
    } catch (e) {
      alert(e.message);
    }
  };
  const setSessionActive = async (session, isActive) => {
    const verb = isActive ? "Reactivate" : "Deactivate";
    if (!confirm(`${verb} session "${session.label}"?`)) return;
    try {
      await onUpdate(session.id, {
        is_active: isActive
      });
      await refresh();
    } catch (e) {
      alert(e.message);
    }
  };
  return <div className="intel-panel">
      <div className="intel-toolbar">
        <div className="intel-title">
          <span>Scanner Sessions</span>
          <span className="subtle">{counts.total || 0} durable label{(counts.total || 0) === 1 ? "" : "s"}; auth material is redacted</span>
        </div>
        <div className="intel-filter">
          <button className="btn ghost sm" onClick={refresh}>Refresh</button>
        </div>
      </div>

      <div className="intel-counts">
        <div className="task-summary-card"><span className="task-summary-value">{counts.total || 0}</span><span className="task-summary-label">Total</span></div>
        <div className="task-summary-card"><span className="task-summary-value">{counts.active || 0}</span><span className="task-summary-label">Active</span></div>
        {kinds.map(([kind, count]) => <div key={kind} className="task-summary-card">
            <span className="task-summary-value">{count}</span>
            <span className="task-summary-label">{kind.replace(/_/g, " ")}</span>
          </div>)}
        {sessions.length === 0 && <div className="subtle">No scanner sessions have been recorded yet. Start a Structured or Dynamic Scan to populate durable session labels.</div>}
      </div>

      <div className="intel-table-wrap">
        <table className="intel-table scanner-session-table">
          <colgroup>{sessColW.map((w, i) => <col key={i} style={{
            width: w != null ? w + "px" : undefined
          }} />)}</colgroup>
          <thead>
            <tr>
              <th>Label <div className="col-rh" onMouseDown={e => startSessResize(0, e)} onClick={e => e.stopPropagation()} /></th>
              <th>Kind <div className="col-rh" onMouseDown={e => startSessResize(1, e)} onClick={e => e.stopPropagation()} /></th>
              <th>Originating account <div className="col-rh" onMouseDown={e => startSessResize(2, e)} onClick={e => e.stopPropagation()} /></th>
              <th>Auth material <div className="col-rh" onMouseDown={e => startSessResize(3, e)} onClick={e => e.stopPropagation()} /></th>
              <th>Source <div className="col-rh" onMouseDown={e => startSessResize(4, e)} onClick={e => e.stopPropagation()} /></th>
              <th>Updated <div className="col-rh" onMouseDown={e => startSessResize(5, e)} onClick={e => e.stopPropagation()} /></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sessions.map(s => <tr key={s.id}>
                <td><div className="intel-primary mono">{s.label}</div>{!s.is_active && <span className="task-status status-skipped">inactive</span>}</td>
                <td><span className={"task-status status-" + (s.kind === "anonymous" ? "skipped" : "confirmed")}>{s.kind}</span></td>
                <td>{s.account_label || s.username ? <div className="intel-primary">{s.account_label || s.username}</div> : <span className="subtle">Unknown account</span>}{s.credential_id ? <div className="intel-meta">credential #{s.credential_id}</div> : ""}</td>
                <td>
                  <div className="session-material-row">
                    <span className="intel-kind">Cookies</span>
                    <span>{(s.cookie_names || []).length ? s.cookie_names.join(", ") : "none"}</span>
                  </div>
                  <div className="session-material-row">
                    <span className="intel-kind">Headers</span>
                    <span>{(s.header_names || []).length ? s.header_names.join(", ") : "none"}</span>
                  </div>
                  {s.token_hint && <div className="intel-meta">token: {s.token_hint}</div>}
                </td>
                <td>{s.source || "scanner"}</td>
                <td>{fmtAge(s.updated_at)}</td>
                <td>
                  <div className="row session-actions">
                    <button className="btn secondary sm" onClick={() => renameSession(s)}>Rename</button>
                    {s.is_active ? <button className="btn danger-outline sm" onClick={() => setSessionActive(s, false)}>Deactivate</button> : <button className="btn secondary sm" onClick={() => setSessionActive(s, true)}>Reactivate</button>}
                  </div>
                </td>
              </tr>)}
          </tbody>
        </table>
      </div>
    </div>;
}
