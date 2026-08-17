import assert from "node:assert/strict";
import test from "node:test";

import { isCrawlerAgentActive, runStatusFromThinkingStatus } from "./runState.js";

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

test("dynamic scan terminal events update the parent run status", () => {
  assert.equal(runStatusFromThinkingStatus({ status: "running" }, "complete"), "running");
  assert.equal(runStatusFromThinkingStatus({ status: "stopped" }, "running"), "stopped");
  assert.equal(runStatusFromThinkingStatus({ status: "failed" }, "running"), "failed");
  assert.equal(runStatusFromThinkingStatus({ status: "complete", run_outcome: "incomplete" }, "running"), "incomplete");
  assert.equal(runStatusFromThinkingStatus({ status: "idle" }, "complete"), "complete");
});
