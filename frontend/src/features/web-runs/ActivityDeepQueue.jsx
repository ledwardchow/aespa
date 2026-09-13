import { useEffect, useState } from "react";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { truncUrl } from "../../shared/lib/urls.js";
import { stepDescription, stepSupportingDetail } from "./ActivitySpecialists.jsx";

const TERMINAL = new Set(["complete", "stopped", "failed", "idle"]);
const readableLabel = (value) => value?.replaceAll("_", " ");
const taskStatusLabel = (status) =>
  ["finding", "inconclusive"].includes(status) ? "Complete" : readableLabel(status);

function taskStatusClass(status) {
  if (status === "running" || status === "active") return "agent-badge-active";
  if (status === "failed") return "agent-badge-failed";
  if (status === "queued") return "agent-badge-queued";
  return "agent-badge-complete";
}

function CheckRow({ check }) {
  return (
    <div className="deep-check-row">
      <span className={`agent-badge ${taskStatusClass(check.status)}`}>
        {taskStatusLabel(check.status)}
      </span>
      <strong>{readableLabel(check.attack_class)}</strong>
      {check.owasp_category && <span>{check.owasp_category}</span>}
      {check.parameter && <code>{check.parameter}</code>}
      {check.session_label && <span>Compare: {readableLabel(check.session_label)}</span>}
      <span className="subtle deep-check-hypothesis">{check.hypothesis}</span>
    </div>
  );
}

function VariantRow({ variant, worker }) {
  const pivots = variant.pivot_history || [];
  const steps = worker?.stepHistory || [];
  return (
    <div className="deep-variant-row">
      <div className="deep-variant-heading">
        <span className={`agent-badge ${taskStatusClass(variant.status)}`}>
          {taskStatusLabel(variant.status)}
        </span>
        <strong>{readableLabel(variant.kind)}</strong>
        <span className="deep-queue-task-detail">{readableLabel(variant.strategy)}</span>
        {variant.finding_count > 0 && (
          <span className="agent-badge deep-queue-findings-badge">
            {variant.finding_count} {variant.finding_count === 1 ? "finding" : "findings"}
          </span>
        )}
      </div>
      <div className="deep-variant-purpose">{variant.current_purpose || variant.purpose}</div>
      {variant.difference && <div className="subtle">Difference: {variant.difference}</div>}
      {variant.identities?.length > 0 && (
        <div className="subtle">Identity: {variant.identities.map(readableLabel).join(", ")}</div>
      )}
      {pivots.length > 0 && (
        <div className="deep-variant-pivots">
          {pivots.map((pivot, index) => (
            <div className="subtle" key={`${pivot.at || index}-${index}`}>
              Pivoted to: {pivot.to || String(pivot)}
            </div>
          ))}
        </div>
      )}
      {worker && (
        <details className="deep-worker-trace" open={worker.status === "active" ? true : undefined}>
          <summary className="deep-worker-trace-heading">
            <strong>Worker trace</strong>
            <span className={`agent-badge ${taskStatusClass(worker.status)}`}>
              {worker.status === "active" ? "Active" : "Done"}
            </span>
            <span className="subtle">{worker.currentTask}</span>
          </summary>
          <div className="deep-worker-trace-body">
            {steps.length > 0 ? (
              <div className="agent-task-history">
                {steps
                  .slice()
                  .reverse()
                  .map((step, index) => {
                    const description = stepDescription(step);
                    const supportingDetail = stepSupportingDetail(step);
                    return (
                      <div className="agent-history-entry" key={`${step.ts || index}-${index}`}>
                        <span className="activity-ts">{step.ts}</span>
                        <span className="agent-step-description" title={description}>
                          {step.step ? `Step ${step.step}: ` : ""}
                          {description}
                        </span>
                        {supportingDetail && (
                          <span className="agent-history-outcome" title={supportingDetail}>
                            {supportingDetail}
                          </span>
                        )}
                      </div>
                    );
                  })}
              </div>
            ) : (
              <div className="subtle">Waiting for the first worker step.</div>
            )}
          </div>
        </details>
      )}
    </div>
  );
}

function DeepTaskRow({ task, testerNumber, expanded, onToggle, agentsById }) {
  const checks = task.checks || [];
  const inputs = task.inputs || [];
  const identities = task.identities || [];
  const variants = task.variants || [];
  return (
    <div className="deep-task-group">
      <button
        type="button"
        className="agent-row agent-row--complete deep-task-toggle"
        aria-expanded={expanded}
        onClick={onToggle}
      >
        <span className={`deep-expand-icon${expanded ? " is-open" : ""}`}>›</span>
        <span className={`agent-dot${task.status === "running" ? " agent-dot--active" : ""}`} />
        <span className="agent-role-name">
          Tester {testerNumber} · {readableLabel(task.task_kind || task.attack_class)}
        </span>
        <span className="deep-queue-statuses">
          <span className={`agent-badge ${taskStatusClass(task.status)}`}>
            {taskStatusLabel(task.status)}
          </span>
          {task.finding_count > 0 && (
            <span className="agent-badge deep-queue-findings-badge">
              {task.finding_count} {task.finding_count === 1 ? "finding" : "findings"}
            </span>
          )}
        </span>
        <span className="agent-current-task deep-queue-task">
          <span className="deep-queue-task-summary" title={task.target_url}>
            {task.task_kind === "operation"
              ? `${task.http_method} ${truncUrl(task.route_template || task.target_url, 82)}`
              : `${task.title} · ${task.http_method} ${truncUrl(task.route_template || task.target_url, 72)}`}
          </span>
          <span className="deep-queue-task-details">
            <span className="deep-queue-task-detail">{checks.length} checks</span>
            <span className="deep-queue-task-detail">
              {variants.length} {variants.length === 1 ? "variant" : "variants"}
            </span>
            {inputs.length > 0 && (
              <span className="deep-queue-task-detail" title={inputs.join(", ")}>
                {inputs.length} {inputs.length === 1 ? "input" : "inputs"}
              </span>
            )}
            {identities.length > 0 && (
              <span className="deep-queue-task-detail" title={identities.join(", ")}>
                {identities.length} identity{" "}
                {identities.length === 1 ? "comparison" : "comparisons"}
              </span>
            )}
          </span>
        </span>
        <span className="subtle">
          P{task.priority}
          {task.worker_id ? ` · ${task.worker_id}` : ""}
        </span>
      </button>
      {expanded && (
        <div className="deep-check-list">
          <div className="deep-expanded-label">Execution variants</div>
          {variants.map((variant) => (
            <VariantRow
              variant={variant}
              worker={agentsById.get(variant.worker_id)}
              key={variant.id}
            />
          ))}
          <div className="deep-expanded-label">Tester checks</div>
          {checks.map((check) => (
            <CheckRow check={check} key={check.id} />
          ))}
        </div>
      )}
    </div>
  );
}

export function ActivityDeepQueue({ runId, thinkingStatus, agents = [] }) {
  const [queue, setQueue] = useState(null);
  const [error, setError] = useState("");
  const [expandedTasks, setExpandedTasks] = useState(() => new Set());

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

  const toggleTask = (taskId) =>
    setExpandedTasks((current) => {
      const next = new Set(current);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });

  if (error) return <div className="alert error">{error}</div>;
  if (!queue)
    return (
      <div className="subtle" style={{ padding: 24 }}>
        Loading Deep queue…
      </div>
    );

  const counts = queue.counts || {};
  const planning = queue.planning || {};
  const completedCount = (counts.finding || 0) + (counts.inconclusive || 0);
  const findingCount = (queue.tasks || []).reduce(
    (total, task) => total + (task.finding_count || 0),
    0,
  );
  const agentsById = new Map(agents.map((agent) => [agent.id, agent]));
  return (
    <div className="agents-panel">
      <div className="deep-queue-summary">
        <span>
          <strong>{queue.total}</strong> testers
        </span>
        <span>
          {planning.complete || 0}/{planning.total ?? queue.total} planned
        </span>
        {(planning.active || 0) > 0 && <span>{planning.active} planning now</span>}
        <span>{queue.variants_total || 0} variants</span>
        <span>{queue.checks_total || 0} checks</span>
        <span>{counts.queued || 0} waiting</span>
        <span>{counts.running || 0} active</span>
        <span>{completedCount} complete</span>
        <span>{findingCount} findings</span>
        <span>{counts.failed || 0} failed</span>
      </div>
      {(queue.tasks || []).map((task, index) => (
        <DeepTaskRow
          task={task}
          testerNumber={index + 1}
          expanded={expandedTasks.has(task.id)}
          onToggle={() => toggleTask(task.id)}
          agentsById={agentsById}
          key={task.id}
        />
      ))}
      {queue.total === 0 && (
        <div className="subtle" style={{ padding: 24 }}>
          The queue is built when the Deep scan starts.
        </div>
      )}
    </div>
  );
}
