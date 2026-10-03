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
  defaultModel: { id: 6, name: "Evaluator" },
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
  const button = screen.getByRole("button", { name: "Benchmark 0 selected scans" });
  expect(button.disabled).toBe(true);
  await user.selectOptions(screen.getByLabelText("Ground truth for bulk benchmarks"), "4");
  expect(screen.queryByLabelText("Bulk evaluation model")).toBeNull();
  await user.click(screen.getByRole("checkbox", { name: "Select Completed shop scan" }));
  await user.click(button);
  expect(benchmarkUnbenchmarked).toHaveBeenCalledWith({
    run_kind: "site",
    run_ids: [1],
    dataset_id: 4,
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
  expect(screen.getByRole("button", { name: "Benchmark 0 selected scans" }).disabled).toBe(true);
});

for (const category of ["site", "api"]) {
  test(`${category} allows individual, all, and application selection`, async () => {
    const user = userEvent.setup();
    const applications = [
      ...props.targets.sites,
      {
        id: 2,
        name: "Forum",
        runs: [
          { id: 4, name: "Forum one", status: "complete" },
          { id: 5, name: "Forum two", status: "complete" },
        ],
      },
    ];
    render(
      <CompletedScanBenchmarks
        {...props}
        category={category}
        targets={{ sites: applications, apis: applications, sast_runs: [] }}
        results={[{ id: 8, run_kind: category, run_id: 2 }]}
      />,
    );
    const all = screen.getByRole("checkbox", { name: "Select all unbenchmarked scans" });
    const shop = screen.getByRole("checkbox", { name: "Select all scans from Shop" });
    const forum = screen.getByRole("checkbox", { name: "Select all scans from Forum" });
    expect(screen.getByRole("checkbox", { name: "Select Benchmarked shop scan" }).disabled).toBe(
      true,
    );
    await user.click(screen.getByRole("checkbox", { name: "Select Forum one" }));
    expect(all.indeterminate).toBe(true);
    expect(forum.indeterminate).toBe(true);
    expect(shop.checked).toBe(false);
    await user.click(forum);
    expect(forum.checked).toBe(true);
    await user.click(all);
    expect(shop.checked).toBe(true);
    expect(all.checked).toBe(true);
    await user.click(all);
    expect(all.checked).toBe(false);
    expect(forum.checked).toBe(false);
    await user.click(forum);
    await user.selectOptions(screen.getByLabelText("Ground truth for bulk benchmarks"), "4");
    benchmarkUnbenchmarked.mockResolvedValue({
      completed: [4],
      skipped: [],
      failures: [{ run_id: 5, error: "Try again" }],
    });
    await user.click(screen.getByRole("button", { name: "Benchmark 2 selected scans" }));
    expect(benchmarkUnbenchmarked).toHaveBeenCalledWith({
      run_kind: category,
      run_ids: [4, 5],
      dataset_id: 4,
    });
    await screen.findByRole("status");
    expect(screen.getByRole("checkbox", { name: "Select Forum one" }).checked).toBe(false);
    expect(screen.getByRole("checkbox", { name: "Select Forum two" }).checked).toBe(true);
    expect(screen.getByRole("button", { name: "Benchmark 1 selected scans" })).toBeTruthy();
  });
}
