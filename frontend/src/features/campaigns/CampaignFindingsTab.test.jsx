import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import * as systemsApi from "../../shared/api/systems.js";
import { CampaignFindingsTab } from "./CampaignFindingsTab.jsx";

vi.mock("../../shared/api/systems.js");

test("orders campaign finding groups by severity and then title", async () => {
  systemsApi.getCampaignValidationCases.mockResolvedValue([]);
  systemsApi.getCampaignFindings.mockResolvedValue(
    [
      ["Low issue", "low"],
      ["Zeta high issue", "HIGH "],
      ["Info issue", "informational"],
      ["Alpha high issue", "high"],
      ["Critical issue", "critical"],
      ["Medium issue", "medium"],
    ].map(([title, severity], id) => ({
      id,
      reference: `F-${id}`,
      title,
      severity,
      target_type: "site",
      target_name: "Example",
    })),
  );

  render(<CampaignFindingsTab systemId={1} campaignId={2} />);
  await screen.findByText("Critical issue");
  expect(
    [...document.querySelectorAll(".campaign-findings-table .finding-group-row")].map((row) =>
      row.querySelector(".finding-title").textContent.trim(),
    ),
  ).toEqual([
    "Critical issue 1",
    "Alpha high issue 1",
    "Zeta high issue 1",
    "Medium issue 1",
    "Low issue 1",
    "Info issue 1",
  ]);
});
