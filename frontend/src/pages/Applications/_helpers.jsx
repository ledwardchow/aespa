// Shared formatting/labels for the Applications & Campaigns feature.
// Kept tiny and dependency-free — no giant shared-state module, just pure helpers.

export function formatBytes(bytes) {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i++;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[i]}`;
}

export function shortHash(sha256) {
  return sha256 ? sha256.slice(0, 10) : "—";
}

// The user-visible stage sequence described in docs/architecture.md §18 and
// the plan (Draft -> Scanning code -> Matching context -> Waiting for review
// -> Testing live targets -> Complete). "stopped"/"failed"/"interrupted" are
// not part of the forward sequence — they are terminal/paused states handled
// separately by the banner.
export const CAMPAIGN_STAGES = [
  { key: "draft", label: "Draft" },
  { key: "sast_running", label: "Scanning code" },
  { key: "correlating", label: "Matching context" },
  { key: "awaiting_review", label: "Waiting for review" },
  { key: "dast_running", label: "Testing live targets" },
  { key: "completed", label: "Complete" }
];

export function stageIndex(status) {
  const idx = CAMPAIGN_STAGES.findIndex(s => s.key === status);
  return idx;
}

const ACTIVE_RUN_STATUSES = new Set(["running", "scanning", "analysing", "analyzing", "crawling", "stopping"]);

export function campaignMemberDisplayStatus(member) {
  return member?.run_status || member?.status;
}

function campaignMemberIsRunning(member) {
  return member?.status === "running" || ACTIVE_RUN_STATUSES.has(member?.run_status);
}

function campaignMemberIsComplete(member) {
  return ["complete", "completed"].includes(campaignMemberDisplayStatus(member));
}

// A manually resumed child scan updates its member row before the parent
// campaign status. The linked child run can also be resumed from its own
// page, so use its current status when the campaign payload provides it.
export function campaignDisplayStatus(campaign) {
  if (!campaign) return undefined;

  // The orchestrator's persisted stage is authoritative while it is active.
  // Child rows can still show their previous terminal state for a moment just
  // after Resume, which must not make an active campaign look complete.
  if (["sast_running", "correlating", "dast_running"].includes(campaign.status)) {
    return campaign.status;
  }

  const sourceMembers = campaign.source_members || [];
  const targetMembers = campaign.target_members || [];
  if (targetMembers.some(campaignMemberIsRunning)) {
    return "dast_running";
  }
  if (sourceMembers.some(campaignMemberIsRunning)) {
    return "sast_running";
  }

  const allMembers = [...sourceMembers, ...targetMembers];
  if (allMembers.length > 0 && allMembers.every(campaignMemberIsComplete)) {
    return "completed";
  }
  return campaign.status;
}

export function isTerminalPause(status) {
  return status === "stopped" || status === "failed" || status === "interrupted" || status === "incomplete";
}

export const MEMBER_STATUS_LABEL = {
  pending: "pending",
  running: "running",
  completed: "completed",
  failed: "failed",
  skipped: "skipped",
  incomplete: "incomplete — resume available"
};

export function severityClass(sev) {
  return ({
    critical: "sev-critical",
    high: "sev-high",
    medium: "sev-medium",
    low: "sev-low",
    info: "sev-info"
  })[sev] || "sev-medium";
}

export function safeParseJson(text, fallback) {
  if (!text) return fallback;
  try {
    return JSON.parse(text);
  } catch {
    return fallback;
  }
}

export function confidencePct(score) {
  return `${Math.round((score || 0) * 100)}%`;
}
