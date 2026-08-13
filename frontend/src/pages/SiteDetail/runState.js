export const isCrawlerAgentActive = (agent, crawlStopping = false) => (
  crawlStopping || agent?.status === "active"
);
