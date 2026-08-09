// Run / scan status pill. Maps a status string to a CSS badge variant
// (.badge.<variant> in styles.css) so every page colours statuses the same way.
// Previously each page inlined its own ternary and they had drifted — some used
// "success"/"warning" (which had no CSS rule and rendered colourless).
const VARIANT = {
  completed: "ok",
  complete: "ok",
  scanned: "ok",
  running: "running",
  scanning: "running",
  analyzing: "running",
  analysing: "running",
  crawling: "running",
  stopping: "stopping",
  failed: "danger",
  cancelled: "danger",
  error: "danger",
  // Campaign / campaign-member statuses (services/campaigns.py).
  draft: "neutral",
  pending: "neutral",
  sast_running: "running",
  correlating: "running",
  dast_running: "running",
  awaiting_review: "warning",
  stopped: "danger",
  interrupted: "warning",
  incomplete: "warning",
  skipped: "neutral",
  proposed: "neutral",
  approved: "ok",
  rejected: "danger"
};

const LABEL_OVERRIDE = {
  analyzing: "analysing",
  sast_running: "scanning code",
  correlating: "matching context",
  awaiting_review: "awaiting review",
  dast_running: "testing live targets",
  incomplete: "incomplete — resume available"
};

export function StatusBadge({ status, className = "" }) {
  const variant = VARIANT[status] || "neutral";
  const label = LABEL_OVERRIDE[status] || status;
  return <span className={`badge ${variant} ${className}`.trim()}>{label}</span>;
}
