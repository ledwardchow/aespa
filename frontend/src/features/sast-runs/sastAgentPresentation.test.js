import { expect, test } from "vitest";

import { buildSastAgentRoster } from "./sastAgentPresentation.js";

test("builds fixed SAST panes and groups concurrent workers", () => {
  const rows = [
    {
      id: 1,
      agent_id: "sast-threat-modeller",
      role: "Threat Modeller",
      status: "complete",
      current_task: "Threat model complete",
      created_at: "2026-09-11T01:00:00Z",
    },
    {
      id: 2,
      agent_id: "sast-worker-10",
      role: "SAST Injection Worker",
      status: "spawned",
      current_task: "Queued analysis worker routes:injection",
      display_name: "routes:injection",
      class_group: "injection",
      created_at: "2026-09-11T01:00:01Z",
    },
    {
      id: 3,
      agent_id: "sast-worker-10",
      role: "SAST Injection Worker",
      status: "active",
      current_task: "routes:injection: reviewing 8 assigned checks",
      display_name: "routes:injection",
      class_group: "injection",
      created_at: "2026-09-11T01:00:02Z",
    },
    {
      id: 4,
      agent_id: "sast-worker-11",
      role: "SAST Injection Worker",
      status: "complete",
      current_task: "Analysis finished for handlers:injection",
      display_name: "handlers:injection",
      class_group: "injection",
      created_at: "2026-09-11T01:00:03Z",
    },
    {
      id: 5,
      agent_id: "sast-validator-17",
      role: "SAST Candidate Validator",
      status: "paused",
      current_task: "Validation paused for candidate 17",
      created_at: "2026-09-11T01:00:04Z",
    },
  ];

  const roster = buildSastAgentRoster(rows, "deep", true);

  expect(roster.map((entry) => entry.name)).toEqual([
    "Repository Modeller",
    "Threat Modeller",
    "SAST Analyst",
    "Review Workers",
    "Injection Workers",
    "Sink Workers",
    "Finding Validators",
    "Gap Reviewer",
    "Attack Path Analyst",
  ]);
  const injection = roster.find((entry) => entry.id === "sast-injection-workers");
  expect(injection.status).toBe("active");
  expect(injection.task).toBe("1 active, 1 complete");
  expect(injection.children.map((child) => child.name)).toEqual([
    "routes:injection",
    "handlers:injection",
  ]);
  expect(injection.children[0].taskHistory).toHaveLength(2);
  const validators = roster.find((entry) => entry.id === "sast-validators");
  expect(validators.status).toBe("paused");
  expect(validators.children[0].name).toBe("Finding 17");
});

test("light scans omit deep-only agent panes", () => {
  const roster = buildSastAgentRoster([], "light", false);
  const ids = roster.map((entry) => entry.id);

  expect(ids).not.toContain("sast-repository-modeller");
  expect(ids).not.toContain("sast-threat-modeller");
  expect(ids).not.toContain("sast-closure-analyst");
  expect(ids).toContain("sast-scanner");
  expect(ids).toContain("sast-review-workers");
  expect(ids).toContain("sast-sink-workers");
  expect(ids).not.toContain("sast-injection-workers");
  expect(ids).toContain("sast-attack-path");
});

test("groups route review workers", () => {
  const roster = buildSastAgentRoster(
    [
      {
        id: 1,
        agent_id: "sast-worker-1087",
        role: "SAST Review Worker",
        status: "active",
        current_task: "src/Controllers:3:review: reviewing 51 assigned items",
        created_at: "2026-09-28T09:56:30Z",
      },
    ],
    "light",
    true,
  );

  const review = roster.find((entry) => entry.id === "sast-review-workers");
  expect(review.status).toBe("active");
  expect(review.children).toHaveLength(1);
  expect(review.children[0].classGroup).toBe("review");
});

test("deduplicates repeated reconstructed lifecycle entries", () => {
  const duplicate = {
    agent_id: "sast-worker-1",
    role: "SAST Sink Worker",
    status: "active",
    current_task: "Started analysis worker sink-audit:1",
    display_name: "sink-audit:1",
    class_group: "sink",
    created_at: "2026-09-11T01:00:00Z",
  };
  const roster = buildSastAgentRoster(
    [
      { ...duplicate, id: "persisted" },
      { ...duplicate, id: "live" },
    ],
    "deep",
    true,
  );

  const sink = roster.find((entry) => entry.id === "sast-sink-workers");
  expect(sink.children[0].taskHistory).toHaveLength(1);
});

test("lists unfinished workers before completed ones", () => {
  const row = (id, agentId, status) => ({
    id,
    agent_id: agentId,
    role: "SAST Candidate Validator",
    status,
    current_task: `${status} ${agentId}`,
    created_at: `2026-09-28T10:14:0${id}Z`,
  });
  const roster = buildSastAgentRoster(
    [
      row(1, "sast-validator-0", "complete"),
      row(2, "sast-validator-1", "complete"),
      row(3, "sast-validator-2", "spawned"),
      row(4, "sast-validator-3", "active"),
      row(5, "sast-validator-4", "complete"),
    ],
    "light",
    true,
  );

  const validators = roster.find((entry) => entry.id === "sast-validators");
  expect(validators.children.map((child) => child.id)).toEqual([
    "sast-validator-3",
    "sast-validator-2",
    "sast-validator-0",
    "sast-validator-1",
    "sast-validator-4",
  ]);
  expect(validators.task).toBe("1 active, 1 queued, 3 complete");
});

test("stopped scans do not show stale validator activity", () => {
  const rows = [
    { id: 1, agent_id: "sast-validator", role: "SAST Validator", status: "active" },
    { id: 2, agent_id: "sast-validator-1", role: "SAST Candidate Validator", status: "failed" },
    { id: 3, agent_id: "sast-validator-2", role: "SAST Candidate Validator", status: "complete" },
  ];

  const validators = buildSastAgentRoster(rows, "light", false).find(
    (entry) => entry.id === "sast-validators",
  );
  expect(validators.status).toBe("paused");
  expect(validators.task).toBe("1 complete, 1 failed");
  expect(validators.children.every((child) => child.status !== "active")).toBe(true);
});
