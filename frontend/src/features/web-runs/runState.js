export const isCrawlerAgentActive = (agent, crawlStopping = false) =>
  crawlStopping || agent?.status === "active";

export const RUN_PRIMARY_ACTION = Object.freeze({
  START_CRAWL: "start_crawl",
  START_PENTEST: "start_pentest",
  RESUME_PENTEST: "resume_pentest",
});

export const resolveRunPrimaryAction = ({
  hasCrawlResult,
  canStartCrawl,
  canStartPentest,
  canResumePentest,
}) => {
  if (!hasCrawlResult) {
    return canStartCrawl ? RUN_PRIMARY_ACTION.START_CRAWL : null;
  }
  if (canResumePentest) return RUN_PRIMARY_ACTION.RESUME_PENTEST;
  if (canStartPentest) return RUN_PRIMARY_ACTION.START_PENTEST;
  return null;
};

// The dynamic scan status is delivered separately from the parent run record.
// Keep the parent status in sync so controls that depend on it update when a
// scan finishes without requiring a page reload.
export const runStatusFromThinkingStatus = (thinkingStatus, currentStatus) => {
  const status = thinkingStatus?.status;
  if (
    status === "running" ||
    status === "analysing" ||
    status === "analyzing" ||
    status === "stopping"
  ) {
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
