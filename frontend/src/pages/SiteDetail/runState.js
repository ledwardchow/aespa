export const isCrawlerAgentActive = (agent, crawlStopping = false) => (
  crawlStopping || agent?.status === "active"
);

// The dynamic scan status is delivered separately from the parent run record.
// Keep the parent status in sync so controls that depend on it update when a
// scan finishes without requiring a page reload.
export const runStatusFromThinkingStatus = (thinkingStatus, currentStatus) => {
  const status = thinkingStatus?.status;
  if (status === "running" || status === "analysing" || status === "analyzing" || status === "stopping") {
    return "running";
  }
  if (status === "paused" || status === "stopped" || status === "failed") {
    return status;
  }
  if (status === "complete") {
    return thinkingStatus.run_outcome === "incomplete" ? "incomplete" : "complete";
  }
  return currentStatus;
};
