import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { benchmarkUnbenchmarked } from "../../shared/api/benchmarkBulk.ts";
import { CompletedScanBenchmarks } from "./CompletedScanBenchmarks.jsx";

vi.mock("../../shared/api/benchmarkBulk.ts");
vi.mock("../../shared/api/benchmarkLab.js");
const props = {
  category: "site",
  targets: {
    sites: [
      {
        id: 1,
        name: "Shop",
        runs: [
          { id: 1, name: "Completed shop scan", status: "complete" },
          { id: 2, name: "Benchmarked shop scan", status: "complete" },
          { id: 3, name: "Stopped shop scan", status: "stopped" },
        ],
      },
    ],
    apis: [],
    sast_runs: [],
  },
  results: [{ id: 8, run_kind: "site", run_id: 2 }],
  legacy: [],
  datasets: [{ id: 4, name: "Shop truth", item_count: 1 }],
  models: [{ id: 6, name: "Evaluator" }],
  onChange: vi.fn().mockResolvedValue(undefined),
  onOpen: vi.fn(),
};
beforeEach(() => {
  vi.clearAllMocks();
  benchmarkUnbenchmarked.mockResolvedValue({ completed: [1], skipped: [2], failures: [] });
});

test("lists completed scans and benchmarks only missing results with selected ground truth", async () => {
  const user = userEvent.setup();
  render(<CompletedScanBenchmarks {...props} />);
  expect(screen.getByText("Completed shop scan")).toBeTruthy();
  expect(screen.queryByText("Stopped shop scan")).toBeNull();
  const button = screen.getByRole("button", { name: "Benchmark 1 unbenchmarked scans" });
  expect(button.disabled).toBe(true);
  await user.selectOptions(screen.getByLabelText("Ground truth for bulk benchmarks"), "4");
  await user.selectOptions(screen.getByLabelText("Bulk evaluation model"), "6");
  await user.click(button);
  expect(benchmarkUnbenchmarked).toHaveBeenCalledWith({
    run_kind: "site",
    dataset_id: 4,
    evaluation_model_id: 6,
  });
  expect((await screen.findByRole("status")).textContent).toContain("Benchmarked 1 scans");
  expect(props.onChange).toHaveBeenCalled();
  await user.click(
    screen.getByRole("button", { name: "Open benchmark for Benchmarked shop scan" }),
  );
  expect(props.onOpen).toHaveBeenCalledWith(8);
});

test("counts completed legacy SAST evaluations as benchmarked", () => {
  render(
    <CompletedScanBenchmarks
      {...props}
      category="sast"
      targets={{ sites: [], apis: [], sast_runs: [{ id: 7, name: "Source", status: "completed" }] }}
      legacy={[{ id: 3, sast_run_id: 7, status: "completed" }]}
    />,
  );
  expect(screen.getByRole("link", { name: "Open benchmark" }).getAttribute("href")).toBe(
    "#/benchmark-lab/evaluations/3",
  );
  expect(screen.getByRole("button", { name: "Benchmark 0 unbenchmarked scans" }).disabled).toBe(
    true,
  );
});
