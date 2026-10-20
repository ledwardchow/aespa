// Several workflows can run at once, so retry progress is tracked per note id.

export function isRetryBusy(progress) {
  return ["submitting", "running"].includes(progress?.status);
}

export function anyRetryBusy(retries) {
  return Object.values(retries).some(isRetryBusy);
}

export function crawlerAgentForRetries(agent, retries) {
  const busy = Object.values(retries).filter(isRetryBusy);
  if (!busy.length || agent?.status === "active") return agent;
  const name = busy[0]?.workflow_name;
  const currentTask =
    busy.length > 1
      ? `Continuing ${busy.length} workflows`
      : name
        ? `Continuing ${name}`
        : "Continuing a workflow";
  return {
    id: "crawler",
    role: "Crawler",
    ...agent,
    status: "active",
    currentTask,
    workflowRetryActive: true,
  };
}

export function retriesByNote(status) {
  return Object.fromEntries((status?.retries || []).map((item) => [item.note_id, item]));
}

// Combine the server's retry list with retries this page has just started.
// A retry that was running here but is missing on the server lost its progress.
export function mergeRetries(current, server) {
  const next = { ...server };
  for (const [noteId, local] of Object.entries(current)) {
    if (local.status === "submitting" && !isRetryBusy(next[noteId])) {
      next[noteId] = local;
      continue;
    }
    if (next[noteId]) continue;
    if (local.status === "running") {
      next[noteId] = {
        ...local,
        status: "error",
        error: "Workflow progress was lost. Check Workflows for a saved result.",
      };
    }
  }
  return next;
}
