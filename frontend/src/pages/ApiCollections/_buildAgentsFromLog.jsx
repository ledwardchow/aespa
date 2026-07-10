

export function _buildAgentsFromLog(rows) {
  const map = new Map();
  for (const r of rows) {
    const id = r.agent_id;
    const ts = r.created_at ? new Date(r.created_at).toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    }) : "--:--:--";
    const existing = map.get(id) || {
      id,
      name: r.role || id,
      status: r.status || "idle",
      task: r.current_task || "",
      taskHistory: []
    };
    existing.name = r.role || existing.name;
    existing.status = r.status || existing.status;
    existing.task = r.current_task || existing.task;
    existing.taskHistory.push({
      ts,
      task: r.current_task || "",
      outcome: r.outcome || ""
    });
    map.set(id, existing);
  }
  return [...map.values()];
}

// ── ApiRunStatusTab ────────────────────────────────────────────────────────────

