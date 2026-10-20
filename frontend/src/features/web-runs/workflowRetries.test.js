import { expect, test } from "vitest";

import { activityPresentation } from "./activityPresentation.js";
import { crawlerAgentForRetries } from "./workflowRetries.js";

test("crawler stays active until every workflow retry finishes", () => {
  const idle = {
    id: "crawler",
    role: "Crawler",
    status: "complete",
    currentTask: "Crawl complete",
  };
  const retries = {
    1: { status: "running", workflow_name: "Add address" },
    2: { status: "running", workflow_name: "Place order" },
  };
  const first = crawlerAgentForRetries(idle, retries);
  expect(first).toMatchObject({
    status: "active",
    currentTask: "Continuing 2 workflows",
    workflowRetryActive: true,
  });
  expect(crawlerAgentForRetries(idle, { ...retries, 1: { status: "complete" } }).status).toBe(
    "active",
  );
  expect(crawlerAgentForRetries(idle, { 1: { status: "complete" }, 2: { status: "error" } })).toBe(
    idle,
  );
});

test("workflow retry task takes precedence over old crawl events", () => {
  const crawler = crawlerAgentForRetries(
    {
      id: "crawler",
      role: "Crawler",
      status: "complete",
      crawlEvents: [{ stageLabel: "Crawling pages", url: "https://example.test", done: false }],
    },
    { 1: { status: "submitting", workflow_name: "Add address" } },
  );
  const view = activityPresentation({
    run: { status: "complete" },
    thinkingStatus: { status: "idle" },
    aliceIsThinking: false,
    activityLog: [],
  });
  expect(view.agentCurrentTask(crawler)).toBe("Continuing Add address");
});

test("main crawl activity is preserved while a workflow retry runs", () => {
  const crawling = { id: "crawler", role: "Crawler", status: "active", currentTask: "Crawling" };
  expect(
    crawlerAgentForRetries(crawling, { 1: { status: "running", workflow_name: "Add address" } }),
  ).toBe(crawling);
});
