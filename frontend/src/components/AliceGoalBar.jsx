export function AliceGoalBar({ goal, running, onPause, onResume, onEdit, onClear }) {
  if (!goal || goal.status === "cleared") return null;
  const checkpoint = goal.checkpoint || {};
  const remaining = checkpoint.remaining_work;
  const detail = goal.pause_reason || goal.blocker || (Array.isArray(remaining) && remaining.length ? `${remaining.length} item${remaining.length === 1 ? "" : "s"} remaining` : "Working toward verified completion");

  return <div className={`alice-goal-bar alice-goal-bar--${goal.status}`}>
    <div className="alice-goal-copy">
      <span className="alice-goal-status">Goal · {goal.status.replace("_", " ")}</span>
      <span className="alice-goal-objective" title={goal.objective}>{goal.objective}</span>
      {detail && <span className="alice-goal-detail">{detail}</span>}
    </div>
    <div className="alice-goal-actions">
      {running && goal.status === "active" && <button onClick={onPause}>Pause</button>}
      {!running && ["paused", "waiting_input"].includes(goal.status) && <button onClick={onResume}>Resume</button>}
      {!running && !["completed", "blocked"].includes(goal.status) && <button onClick={onEdit}>Edit</button>}
      {!running && <button onClick={onClear}>Clear</button>}
    </div>
  </div>;
}
