import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import {
  EfficiencyView,
  ObligationsView,
  RepositoryModelView,
  ThreatModelView,
} from "./SemanticAnalysisView.jsx";

test("renders repository facts and completeness warnings", () => {
  render(
    <RepositoryModelView
      model={{
        nodes: [
          {
            id: "operation-1",
            kind: "operation",
            type: "route",
            name: "GET /accounts",
            component_key: "src/accounts.py",
            evidence: ["src/accounts.py:12"],
            confidence: 0.9,
          },
        ],
        warnings: [
          {
            key: "unmapped_worker",
            status: "unresolved",
            message: "A queue worker could not be mapped.",
          },
        ],
        stats: { production_files: 4 },
      }}
    />,
  );

  expect(screen.getByText("GET /accounts")).toBeTruthy();
  expect(screen.getByText("A queue worker could not be mapped.")).toBeTruthy();
  expect(screen.getByText("90%")).toBeTruthy();
});

test("renders threat scenarios and semantic closure evidence", () => {
  const { unmount } = render(
    <ThreatModelView
      threatModel={{
        summary: "One source-backed scenario.",
        assets: [{ id: "asset-1", name: "Account records" }],
        stores: [{ id: "store-1", name: "MySQL database" }],
        files_reviewed: 4,
        quality: { status: "partial", reasons: ["One trust boundary remains open."] },
        scenarios: [
          {
            scenario_key: "scenario-1",
            title: "Protect account access",
            status: "planned",
            priority: "high",
            confidence: 0.8,
            actor: "authenticated user",
            security_objective: "enforce ownership",
          },
        ],
      }}
    />,
  );
  expect(screen.getByText("Protect account access")).toBeTruthy();
  expect(screen.getByText("Account records")).toBeTruthy();
  expect(screen.getByText("MySQL database")).toBeTruthy();
  expect(screen.getByText("One trust boundary remains open.")).toBeTruthy();
  expect(screen.getByText("Partial")).toBeTruthy();
  unmount();

  render(
    <ObligationsView
      planning={{
        obligations: [
          {
            obligation_key: "obligation-1",
            title: "Check ownership",
            security_question: "Can one user read another account?",
            obligation_type: "threat_scenario",
            priority: "high",
            status: "candidate",
            evidence: ["src/accounts.py:12"],
          },
        ],
      }}
      closure={{ status: "full", closure_candidates_created: 1, reasons: [] }}
      report={{ candidates: 1, discovery_summary: "Threat-directed review completed." }}
    />,
  );
  expect(screen.getByText("Check ownership")).toBeTruthy();
  expect(screen.getByText("Required security checks")).toBeTruthy();
  expect(screen.getByText("Security checks")).toBeTruthy();
  expect(screen.getByText("1 candidates recovered")).toBeTruthy();
});

test.each([
  [ThreatModelView, { threatModel: {} }, "Threat model"],
  [ObligationsView, { planning: {}, closure: {}, report: {} }, "Security check analysis"],
  [RepositoryModelView, { model: {} }, "Repository model"],
])("renders a running empty state for %s", (View, props, label) => {
  const { unmount } = render(<View {...props} status="running" />);

  expect(screen.getByText(`${label} is not ready yet.`)).toBeTruthy();
  expect(screen.getByText("This analysis will appear as the scan progresses.")).toBeTruthy();
  expect(screen.queryByText(/Run the scan again/)).toBeNull();
  unmount();
});

test("renders per-phase efficiency telemetry", () => {
  render(
    <EfficiencyView
      telemetry={[
        {
          phase: "discovery",
          strategy: "threat_directed",
          elapsed_ms: 1250,
          files_read: 3,
          unique_spans_read: 4,
          candidates_emitted: 2,
          candidates_confirmed: 1,
          candidates_dismissed: 1,
          caps_json: "[]",
        },
      ]}
      report={{ reportable: 1 }}
    />,
  );
  expect(screen.getByText("threat directed")).toBeTruthy();
  expect(screen.getByText("2 emitted · 1 confirmed · 1 dismissed")).toBeTruthy();
});

test("shows repository model reconciliation failures", () => {
  render(
    <RepositoryModelView
      model={{
        nodes: [],
        warnings: [],
        reconciliation: {
          status: "failed",
          warning: "Model provider is unavailable.",
        },
      }}
    />,
  );

  expect(screen.getByText("model reconciliation")).toBeTruthy();
  expect(screen.getByText("Model provider is unavailable.")).toBeTruthy();
});

test.each([
  [
    "running",
    "Efficiency telemetry is being collected.",
    "This analysis will appear after the scan finishes and the final report is ready.",
  ],
  [
    "scanning",
    "Efficiency telemetry is being collected.",
    "This analysis will appear after the scan finishes and the final report is ready.",
  ],
  [
    "pending",
    "Efficiency telemetry has not been collected yet.",
    "Start the SAST scan to generate this analysis.",
  ],
  [
    "paused",
    "Efficiency telemetry is waiting for the scan to finish.",
    "Resume the scan to continue collecting this analysis.",
  ],
  [
    "failed",
    "Efficiency telemetry was not generated.",
    "The scan ended before the final report was ready.",
  ],
  [
    "completed",
    "Efficiency telemetry is not available for this run.",
    "Run the scan again with the current SAST workflow to generate this analysis.",
  ],
])("renders a %s efficiency empty state", (status, label, message) => {
  render(<EfficiencyView telemetry={[]} report={{}} status={status} />);

  expect(screen.getByText(label)).toBeTruthy();
  expect(screen.getByText(message)).toBeTruthy();
});
