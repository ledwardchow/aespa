import { useEffect, useState } from "react";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { truncUrl } from "../../shared/lib/urls.js";

const TERMINAL = new Set(["complete", "stopped", "failed", "idle"]);

function readableLabel(value) {
  return value?.replaceAll("_", " ");
}

export function ActivityDeepQueue({ runId, thinkingStatus }) {
  const [queue, setQueue] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stopped = false;
    const load = () =>
      webRunsApi
        .getDeepQueue(runId)
        .then((data) => {
          if (!stopped) setQueue(data);
        })
        .catch((requestError) => {
          if (!stopped) setError(requestError.message);
        });
    load();
    const status = thinkingStatus?.status || "idle";
    const timer = TERMINAL.has(status) ? null : window.setInterval(load, 2000);
    return () => {
      stopped = true;
      if (timer) window.clearInterval(timer);
    };
  }, [runId, thinkingStatus?.status]);

  if (error) return <div className="alert error">{error}</div>;
  if (!queue)
    return (
      <div className="subtle" style={{ padding: 24 }}>
        Loading Deep queue…
      </div>
    );

  const counts = queue.counts || {};
  return (
    <div className="agents-panel">
      <div className="deep-queue-summary">
        <span>
          <strong>{queue.total}</strong> tasks
        </span>
        <span>{counts.queued || 0} queued</span>
        <span>{counts.running || 0} active</span>
        <span>{counts.finding || 0} findings</span>
        <span>{counts.inconclusive || 0} inconclusive</span>
        <span>{counts.failed || 0} failed</span>
      </div>
      {(queue.tasks || []).map((task) => (
        <div className="agent-row agent-row--complete" key={task.id}>
          <span className={`agent-dot${task.status === "running" ? " agent-dot--active" : ""}`} />
          <span className="agent-role-name">
            #{task.id} {task.attack_class.replaceAll("_", " ")}
          </span>
          <span
            className={`agent-badge${task.status === "running" ? " agent-badge-active" : " agent-badge-complete"}`}
          >
            {task.status.toUpperCase()}
          </span>
          <span className="agent-current-task deep-queue-task">
            <span className="deep-queue-task-summary" title={task.target_url}>
              {task.title} · {task.http_method} {truncUrl(task.target_url, 72)}
            </span>
            {(task.parameter || task.session_label) && (
              <span className="deep-queue-task-details">
                {task.parameter && (
                  <span className="deep-queue-task-detail" title={`Input: ${task.parameter}`}>
                    Input: <code>{task.parameter}</code>
                  </span>
                )}
                {task.session_label && (
                  <span
                    className="deep-queue-task-detail"
                    title={`Identity comparison: ${readableLabel(task.session_label)}`}
                  >
                    Compare: {readableLabel(task.session_label)}
                  </span>
                )}
              </span>
            )}
          </span>
          <span className="subtle">
            P{task.priority}
            {task.worker_id ? ` · ${task.worker_id}` : ""}
          </span>
        </div>
      ))}
      {queue.total === 0 && (
        <div className="subtle" style={{ padding: 24 }}>
          The queue is built when the Deep scan starts.
        </div>
      )}
    </div>
  );
}
