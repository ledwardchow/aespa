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
  expect(screen.getByText("1 candidates recovered")).toBeTruthy();
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
