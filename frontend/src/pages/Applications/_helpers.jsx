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
