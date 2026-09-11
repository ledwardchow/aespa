import { normaliseAgentStatus } from "../../shared/runs/AgentStatusRows.jsx";

const FIXED_AGENTS = [
  {
    id: "sast-repository-modeller",
    name: "Repository Modeller",
    task: "Waiting to model the repository",
    deepOnly: true,
  },
  {
    id: "sast-threat-modeller",
    name: "Threat Modeller",
    task: "Waiting to model threats",
    deepOnly: true,
  },
  { id: "sast-scanner", name: "SAST Analyst", task: "Waiting to analyse source" },
];

const GROUPS = [
  {
    id: "sast-injection-workers",
    name: "Injection Workers",
    classGroup: "injection",
    task: "No injection analysis queued",
  },
  {
    id: "sast-access-workers",
    name: "Access Control Workers",
    classGroup: "access",
    task: "No access-control analysis queued",
  },
  {
    id: "sast-logic-workers",
    name: "Logic Workers",
    classGroup: "logic",
    task: "No business-logic analysis queued",
  },
  {
    id: "sast-sink-workers",
    name: "Sink Workers",
    classGroup: "sink",
    task: "No sink analysis queued",
  },
  {
    id: "sast-validators",
    name: "Candidate Validators",
    classGroup: "validator",
    task: "No candidate validation queued",
  },
];

const FINAL_AGENTS = [
  {
    id: "sast-closure-analyst",
    name: "Closure Analyst",
    task: "Waiting for closure review",
    deepOnly: true,
  },
  {
    id: "sast-attack-path",
    name: "Attack Path Analyst",
    task: "Waiting for validated candidates",
  },
];

function eventTime(value) {
  if (!value) return "--:--:--";
  return new Date(value).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function inferClassGroup(row) {
  if (row.parent_id === "sast-validators" || /^sast-validator-\d+$/.test(row.agent_id || "")) {
    return "validator";
  }
  if (row.class_group) return row.class_group;
  const role = String(row.role || "").toLowerCase();
  return ["injection", "access", "logic", "sink"].find((group) => role.includes(`${group} worker`));
}

export function sastGroupHasActiveAgent(rows, classGroup) {
  return (rows || []).some(
    (row) => inferClassGroup(row) === classGroup && normaliseAgentStatus(row.status) === "active",
  );
}

function inferredWorkerName(row) {
  if (row.display_name) return row.display_name;
  if (row.worker_key) return row.worker_key;
  const task = String(row.current_task || "");
  const workerMatch = task.match(
    /^(?:Queued analysis worker|Started analysis worker|Analysis (?:finished|failed|paused|stopped) for) (.+)$/,
  );
  if (workerMatch) return workerMatch[1];
  const candidate = String(row.agent_id || "").match(/^sast-validator-(\d+)$/)?.[1];
  return candidate ? `Candidate ${candidate}` : row.role || row.agent_id || "Worker";
}

function buildAgents(rows) {
  const agents = new Map();
  for (const row of rows || []) {
    if (!row.agent_id) continue;
    const existing = agents.get(row.agent_id) || {
      id: row.agent_id,
      name: row.display_name || row.role || row.agent_id,
      role: row.role || "Agent",
      status: "idle",
      task: "",
      outcome: "",
      taskHistory: [],
      classGroup: inferClassGroup(row),
    };
    existing.name = inferClassGroup(row) ? inferredWorkerName(row) : row.role || existing.name;
    existing.role = row.role || existing.role;
    existing.status = row.status || existing.status;
    existing.task = row.current_task || existing.task;
    existing.outcome = row.outcome || "";
    existing.classGroup = inferClassGroup(row) || existing.classGroup;
    const historyEntry = {
      id: row.id,
      ts: eventTime(row.created_at),
      task: row.current_task || "",
      outcome: row.outcome || "",
      status: row.status || "idle",
    };
    const previous = existing.taskHistory[existing.taskHistory.length - 1];
    if (
      !previous ||
      previous.status !== historyEntry.status ||
      previous.task !== historyEntry.task ||
      previous.outcome !== historyEntry.outcome
    ) {
      existing.taskHistory.push(historyEntry);
    }
    agents.set(row.agent_id, existing);
  }
  return agents;
}

function aggregateStatus(children, parent) {
  const statuses = children.map((child) => normaliseAgentStatus(child.status));
  const parentStatus = normaliseAgentStatus(parent?.status);
  if (statuses.includes("active") || parentStatus === "active") return "active";
  if (statuses.includes("paused") || parentStatus === "paused") return "paused";
  if (statuses.includes("queued") || parentStatus === "queued") return "queued";
  if (statuses.includes("failed") || parentStatus === "failed") return "failed";
  if (children.length || parentStatus === "complete") return "complete";
  return "idle";
}

function groupTask(children, emptyTask) {
  if (!children.length) return emptyTask;
  const counts = new Map();
  for (const child of children) {
    const status = normaliseAgentStatus(child.status);
    counts.set(status, (counts.get(status) || 0) + 1);
  }
  return ["active", "queued", "paused", "complete", "failed"]
    .filter((status) => counts.has(status))
    .map((status) => `${counts.get(status)} ${status}`)
    .join(", ");
}

export function buildSastAgentRoster(rows, analysisMode = "deep", scanRunning = false) {
  const agents = buildAgents(rows);
  const fixed = FIXED_AGENTS.filter((agent) => analysisMode === "deep" || !agent.deepOnly).map(
    (placeholder) => {
      const agent = agents.get(placeholder.id);
      if (agent) return { ...agent, name: placeholder.name };
      return {
        ...placeholder,
        status: placeholder.id === "sast-scanner" && scanRunning ? "active" : "idle",
        task:
          placeholder.id === "sast-scanner" && scanRunning
            ? "Preparing static analysis"
            : placeholder.task,
        taskHistory: [],
      };
    },
  );
  const groups = GROUPS.map((group) => {
    const children = [...agents.values()].filter(
      (agent) => agent.id !== "sast-validator" && agent.classGroup === group.classGroup,
    );
    const parent = group.classGroup === "validator" ? agents.get("sast-validator") : null;
    return {
      ...group,
      status: aggregateStatus(children, parent),
      task: groupTask(children, parent?.task || group.task),
      children,
    };
  });
  const final = FINAL_AGENTS.filter((agent) => analysisMode === "deep" || !agent.deepOnly).map(
    (placeholder) => {
      const agent = agents.get(placeholder.id);
      return agent
        ? { ...agent, name: placeholder.name }
        : { ...placeholder, status: "idle", taskHistory: [] };
    },
  );
  return [...fixed, ...groups, ...final];
}
