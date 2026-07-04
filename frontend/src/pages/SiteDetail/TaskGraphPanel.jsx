import { useColResize } from "../SiteDetail";
import { AttackSurfacePanel } from "./AttackSurfacePanel";
import { useRoute, nav } from "../../lib/router";
import { aliceSessionSubscribe, _aliceFlushRecovery } from "../../lib/aliceSession";
import { fmtDate, truncUrl, apiTranscriptText, markdownListValue, slugForFilename, leadsExportFilename, markdownExportFilename, findingsToMarkdown, workProgramToMarkdown, parseFindingsMarkdown, markdownBullet, stripMarkdownFence } from "../../lib/utilities";
import * as d3 from "d3";

export function TaskGraphPanel({
  data,
  reconSummary,
  subTab,
  onSubTab,
  refresh,
  seed,
  onClear,
  clearing
}) {
  const [taskColW, startTaskResize] = useColResize("colw:tasks", [88, 84, null, 86, 200]);
  const hypotheses = data?.hypotheses || [];
  const tasks = data?.tasks || [];
  const counts = data?.counts || {};
  const tasksByHypothesis = tasks.reduce((acc, task) => {
    const key = task.hypothesis_id || "none";
    (acc[key] = acc[key] || []).push(task);
    return acc;
  }, {});
  const statusLabel = status => (status || "queued").replace(/_/g, " ");
  const taskStatusCounts = ["queued", "running", "blocked", "done", "skipped"].map(status => [status, counts["task_" + status] || 0]).filter(([, count]) => count > 0);
  const orphanTasks = tasksByHypothesis.none || [];
  const priorityTone = p => p >= 88 ? "high" : p >= 78 ? "medium" : "low";
  const activeSubTab = subTab || "attack-surface";
  return <div className="task-panel">
      <div className="tasks-subtab-bar">
        <button className={"tasks-subtab-btn" + (activeSubTab === "attack-surface" ? " active" : "")} onClick={() => onSubTab("attack-surface")}>
          Attack Surface{reconSummary?.attack_classes?.length > 0 ? <span className="traffic-count">{reconSummary.attack_classes.length}</span> : ""}
        </button>
        <button className={"tasks-subtab-btn" + (activeSubTab === "task-queue" ? " active" : "")} onClick={() => onSubTab("task-queue")}>
          Task Queue{counts.tasks > 0 ? <span className="traffic-count">{counts.tasks}</span> : ""}
        </button>
      </div>

      {activeSubTab === "attack-surface" && <AttackSurfacePanel summary={reconSummary} />}

      {activeSubTab === "task-queue" && <>
      <div className="intel-toolbar">
        <div className="intel-title">
          <span>Hypothesis & Task Graph</span>
          <span className="subtle">{hypotheses.length} hypotheses · {tasks.length} tasks</span>
        </div>
        <div className="intel-filter">
          <button className="btn ghost sm" onClick={seed}>Seed from intelligence</button>
          <button className="btn ghost sm" onClick={refresh}>Refresh</button>
          {(hypotheses.length > 0 || tasks.length > 0) && <button className="btn danger-outline sm" disabled={clearing} onClick={onClear}>{clearing ? "Clearing…" : "Clear"}</button>}
        </div>
      </div>

      <div className="task-summary">
        <div className="task-summary-card">
          <span className="task-summary-value">{counts.hypotheses || 0}</span>
          <span className="task-summary-label">Hypotheses</span>
        </div>
        <div className="task-summary-card">
          <span className="task-summary-value">{counts.tasks || 0}</span>
          <span className="task-summary-label">Tasks</span>
        </div>
        {taskStatusCounts.map(([status, count]) => <div key={status} className="task-summary-card">
            <span className="task-summary-value">{count}</span>
            <span className="task-summary-label">{statusLabel(status)}</span>
          </div>)}
        {tasks.length === 0 && <div className="subtle">No task graph yet. Seed it from collected target intelligence, or start a Dynamic Scan.</div>}
      </div>

      <div className="task-list">
        {hypotheses.map(h => {
          const groupedTasks = tasksByHypothesis[h.id] || [];
          return <div key={h.id} className="hypothesis-card">
              <div className="hypothesis-card-head">
                <div>
                  <div className="hypothesis-card-title">{h.title}</div>
                  <div className="hypothesis-card-meta">
                    <span className={"task-priority " + priorityTone(h.priority)}>P{h.priority}</span>
                    <span className={"task-status status-" + h.status}>{statusLabel(h.status)}</span>
                    {h.owasp_category && <span className="owasp-badge">{h.owasp_category}</span>}
                    {h.attack_area && <span>{h.attack_area}</span>}
                    <span>{Math.round((h.confidence || 0) * 100)}% confidence</span>
                  </div>
                </div>
                <span className="task-count-pill">{groupedTasks.length} task{groupedTasks.length === 1 ? "" : "s"}</span>
              </div>
              <div className="hypothesis-rationale">{h.rationale || h.description}</div>
              {groupedTasks.length > 0 && <div className="task-table-wrap">
                  <table className="task-table" style={{
                tableLayout: "fixed"
              }}>
                    <colgroup>{taskColW.map((w, i) => <col key={i} style={{
                    width: w != null ? w + "px" : undefined
                  }} />)}</colgroup>
                    <thead>
                      <tr>
                        <th>Status <div className="col-rh" onMouseDown={e => startTaskResize(0, e)} onClick={e => e.stopPropagation()} /></th>
                        <th>Type <div className="col-rh" onMouseDown={e => startTaskResize(1, e)} onClick={e => e.stopPropagation()} /></th>
                        <th>Task <div className="col-rh" onMouseDown={e => startTaskResize(2, e)} onClick={e => e.stopPropagation()} /></th>
                        <th>Method <div className="col-rh" onMouseDown={e => startTaskResize(3, e)} onClick={e => e.stopPropagation()} /></th>
                        <th>Target <div className="col-rh" onMouseDown={e => startTaskResize(4, e)} onClick={e => e.stopPropagation()} /></th>
                      </tr>
                    </thead>
                    <tbody>
                      {groupedTasks.map(task => <tr key={task.id}>
                          <td><span className={"task-status status-" + task.status}>{statusLabel(task.status)}</span></td>
                          <td><span className="intel-kind">{task.task_type}</span></td>
                          <td>
                            <div className="intel-primary">{task.title}</div>
                            <div className="intel-evidence">{task.result_summary || task.description}</div>
                            {task.evidence && <div className="task-evidence">{task.evidence}</div>}
                          </td>
                          <td><span className="mono">{task.method || "-"}</span></td>
                          <td><span className="mono task-target" title={task.target_url}>{task.target_url ? truncUrl(task.target_url, 86) : "—"}</span></td>
                        </tr>)}
                    </tbody>
                  </table>
                </div>}
            </div>;
        })}
        {orphanTasks.length > 0 && <div className="hypothesis-card">
            <div className="hypothesis-card-title">Unlinked Tasks</div>
            <div className="task-table-wrap">
              <table className="task-table">
                <tbody>
                  {orphanTasks.map(task => <tr key={task.id}>
                      <td><span className={"task-status status-" + task.status}>{statusLabel(task.status)}</span></td>
                      <td>{task.title}</td>
                      <td><span className="mono">{task.target_url}</span></td>
                    </tr>)}
                </tbody>
              </table>
            </div>
          </div>}
      </div></>}
    </div>;
}
