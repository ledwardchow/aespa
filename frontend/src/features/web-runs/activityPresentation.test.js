import { describe, expect, test } from "vitest";

import {
  activityPresentation,
  routeScannerEventToActiveTeamTester,
  teamCoordinatorStatus,
} from "./activityPresentation.js";

function presentation(coverageMode) {
  return activityPresentation({
    run: { coverage_mode: coverageMode },
    thinkingStatus: { status: "running" },
    aliceIsThinking: false,
    activityLog: [],
  });
}

describe("Team agent labels", () => {
  test("keeps the scanner coordinator active as Test Co-ordinator in Team mode", () => {
    const view = presentation("team");

    expect(view.agentRoleLabel({ id: "scanner", role: "Test Lead" })).toBe("Test Co-ordinator");
    expect(view.defaultAgentRoster().find((agent) => agent.id === "scanner")?.role).toBe(
      "Test Co-ordinator",
    );
    expect(view.defaultAgentRoster().find((agent) => agent.id === "scanner")?.status).toBe(
      "active",
    );
  });

  test("uses the new names for saved and live Team members", () => {
    const view = presentation("team");

    expect(view.agentRoleLabel({ id: "team-primary", role: "Primary Test Lead" })).toBe(
      "Primary Tester",
    );
    expect(view.agentRoleLabel({ id: "team-independent", role: "Independent Test Lead" })).toBe(
      "Pair Tester",
    );
    expect(view.agentRoleLabel({ id: "team-closer", role: "Coverage and Chain Test Lead" })).toBe(
      "QA Tester",
    );
  });

  test("routes legacy scanner step events to the active Pair Tester", () => {
    const patch = routeScannerEventToActiveTeamTester(
      {
        id: "scanner",
        role: "Test Lead",
        status: "active",
        currentTask: "Step 3: Testing an identity boundary",
      },
      { id: "team-independent", role: "Pair Tester", status: "active" },
    );

    expect(patch).toMatchObject({
      id: "team-independent",
      role: "Pair Tester",
      currentTask: "Step 3: Testing an identity boundary",
    });
  });

  test("does not route Team co-ordinator lifecycle events", () => {
    const patch = routeScannerEventToActiveTeamTester(
      {
        id: "scanner",
        role: "Test Lead",
        status: "active",
        currentTask: "Dynamic scan started",
      },
      { id: "team-primary", role: "Primary Tester", status: "active" },
    );

    expect(patch.id).toBe("scanner");
  });

  test("keeps the co-ordinator active on the current tester assignment", () => {
    expect(
      teamCoordinatorStatus(
        { id: "team-independent", role: "Pair Tester", status: "active" },
        "Perform an independent second look.",
      ),
    ).toEqual({
      id: "scanner",
      role: "Test Co-ordinator",
      status: "active",
      currentTask: "Co-ordinating Pair Tester: Perform an independent second look.",
    });
  });

  test("does not replace the Team co-ordinator task with the shared scan log", () => {
    const view = activityPresentation({
      run: { coverage_mode: "team" },
      thinkingStatus: { status: "running" },
      aliceIsThinking: false,
      activityLog: [
        {
          phase: "thinking_step",
          status: "deciding",
          message: "Step 12: LLM deciding next action…",
          data: { step: 12 },
        },
      ],
    });
    const coordinator = {
      id: "scanner",
      role: "Test Co-ordinator",
      status: "active",
      currentTask: "Co-ordinating Pair Tester: Perform an independent second look.",
      taskHistory: [{ task: "Co-ordinating Pair Tester" }],
    };

    expect(view.agentCurrentTask(coordinator)).toBe(
      "Co-ordinating Pair Tester: Perform an independent second look.",
    );
    expect(view.agentTaskHistory(coordinator)).toEqual(coordinator.taskHistory);
  });

  test("keeps the Test Lead label outside Team mode", () => {
    const view = presentation("standard");

    expect(view.agentRoleLabel({ id: "scanner", role: "Test Lead" })).toBe("Test Lead");
  });
});
