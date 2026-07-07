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
  analysing: "running",
  crawling: "running",
  stopping: "stopping",
  failed: "danger",
  cancelled: "danger",
  error: "danger"
};

export function StatusBadge({ status, className = "" }) {
  const variant = VARIANT[status] || "neutral";
  return <span className={`badge ${variant} ${className}`.trim()}>{status}</span>;
}
