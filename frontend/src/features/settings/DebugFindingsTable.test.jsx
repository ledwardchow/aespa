import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { DebugFindingsTable } from "./DebugFindingsTable.jsx";

test("orders debug findings by normalized severity and title", () => {
  const findings = [
    ["Low issue", "low"],
    ["Zeta high issue", "HIGH "],
    ["Info issue", "informational"],
    ["Alpha high issue", "high"],
    ["Critical issue", "critical"],
    ["Medium issue", "medium"],
  ].map(([title, severity]) => ({ title, severity }));

  render(<DebugFindingsTable findings={findings} />);
  expect(
    [...document.querySelectorAll(".findings-table .finding-group-row")].map((row) =>
      row.querySelector(".finding-title").textContent.replace("▸", "").trim(),
    ),
  ).toEqual([
    "Critical issue",
    "Alpha high issue",
    "Zeta high issue",
    "Medium issue",
    "Low issue",
    "Info issue",
  ]);
  expect(screen.getByText("info").className).toContain("sev-info");
});
