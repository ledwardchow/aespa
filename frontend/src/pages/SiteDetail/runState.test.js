import assert from "node:assert/strict";
import test from "node:test";

import { isCrawlerAgentActive, resolveRunPrimaryAction, RUN_PRIMARY_ACTION, runStatusFromThinkingStatus } from "./runState.js";

test("crawler activity follows its own agent state", () => {
  assert.equal(isCrawlerAgentActive({ status: "active" }), true);
  assert.equal(isCrawlerAgentActive({ status: "complete" }), false);
  assert.equal(isCrawlerAgentActive({ status: "failed" }), false);
});

test("crawler can remain active while the Test Lead runs concurrently", () => {
  const run = { status: "running", phase: "scanning" };
  const crawler = { status: "active" };

  assert.equal(run.phase, "scanning");
  assert.equal(isCrawlerAgentActive(crawler), true);
});

test("crawler remains active while a stop request is unwinding", () => {
  assert.equal(isCrawlerAgentActive({ status: "complete" }, true), true);
});

test("the combined run action starts with crawling when no crawl result exists", () => {
  assert.equal(resolveRunPrimaryAction({ hasCrawlResult: false, canStartCrawl: true, canStartPentest: true, canResumePentest: true }), RUN_PRIMARY_ACTION.START_CRAWL);
});

test("the combined run action starts a pentest after crawling", () => {
  assert.equal(resolveRunPrimaryAction({ hasCrawlResult: true, canStartCrawl: true, canStartPentest: true, canResumePentest: false }), RUN_PRIMARY_ACTION.START_PENTEST);
});

test("the combined run action resumes an available pentest", () => {
  assert.equal(resolveRunPrimaryAction({ hasCrawlResult: true, canStartCrawl: true, canStartPentest: true, canResumePentest: true }), RUN_PRIMARY_ACTION.RESUME_PENTEST);
});

test("the combined run action hides when its required action is unavailable", () => {
  assert.equal(resolveRunPrimaryAction({ hasCrawlResult: false, canStartCrawl: false, canStartPentest: true, canResumePentest: true }), null);
  assert.equal(resolveRunPrimaryAction({ hasCrawlResult: true, canStartCrawl: true, canStartPentest: false, canResumePentest: false }), null);
});

test("dynamic scan terminal events update the parent run status", () => {
  assert.equal(runStatusFromThinkingStatus({ status: "running" }, "complete"), "running");
  assert.equal(runStatusFromThinkingStatus({ status: "stopped" }, "running"), "stopped");
  assert.equal(runStatusFromThinkingStatus({ status: "failed" }, "running"), "failed");
  assert.equal(runStatusFromThinkingStatus({ status: "complete", run_outcome: "incomplete" }, "running"), "incomplete");
  assert.equal(runStatusFromThinkingStatus({ status: "idle" }, "complete"), "complete");
});
