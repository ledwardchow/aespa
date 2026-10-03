import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import * as api from "../../shared/api/benchmarkLab.js";
import { GroundTruthDatasets } from "./GroundTruthDatasets.jsx";

vi.mock("../../shared/api/benchmarkLab.js");

test("save app assignment and custom label, then handle protected deletion", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn();
  api.updateBenchmarkDatasetDetails.mockResolvedValue({});
  api.deleteBenchmarkDataset.mockRejectedValue(new Error("Delete saved benchmarks first"));
  render(
    <GroundTruthDatasets
      datasets={[{ id: 3, name: "truth.json", item_count: 2 }]}
      targets={{ sites: [{ id: 1, name: "Bank" }], apis: [{ id: 1, name: "Bank API" }] }}
      onChange={onChange}
    />,
  );
  await user.selectOptions(screen.getByLabelText("App or API"), "api:1");
  await user.type(screen.getByLabelText("Custom label"), "Bank truth");
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(api.updateBenchmarkDatasetDetails).toHaveBeenCalledWith(3, {
    label: "Bank truth",
    target_kind: "api",
    target_id: 1,
  });
  expect(onChange).toHaveBeenCalledOnce();
  await user.click(screen.getByRole("button", { name: "Delete", exact: true }));
  expect(api.deleteBenchmarkDataset).not.toHaveBeenCalled();
  await user.click(
    within(screen.getByRole("group", { name: "Confirm deletion" })).getByRole("button", {
      name: "Delete dataset",
    }),
  );
  expect((await screen.findByRole("alert")).textContent).toContain("Delete saved benchmarks first");
});
