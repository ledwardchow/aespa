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
    "Injection Workers",
    "Access Control Workers",
    "Logic Workers",
    "Sink Workers",
    "Candidate Validators",
    "Closure Analyst",
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
  expect(validators.children[0].name).toBe("Candidate 17");
});

test("light scans omit deep-only agent panes", () => {
  const roster = buildSastAgentRoster([], "light", false);
  const ids = roster.map((entry) => entry.id);

  expect(ids).not.toContain("sast-repository-modeller");
  expect(ids).not.toContain("sast-threat-modeller");
  expect(ids).not.toContain("sast-closure-analyst");
  expect(ids).toContain("sast-scanner");
  expect(ids).toContain("sast-injection-workers");
  expect(ids).toContain("sast-attack-path");
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
