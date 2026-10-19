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

test("lists finished scans and benchmarks only missing results with selected ground truth", async () => {
  const user = userEvent.setup();
  render(<CompletedScanBenchmarks {...props} />);
  expect(screen.getByText("Completed shop scan")).toBeTruthy();
  expect(screen.getByText("Stopped shop scan")).toBeTruthy();
  expect(screen.queryByLabelText("Ground truth for bulk benchmarks")).toBeNull();
  await user.click(screen.getByRole("checkbox", { name: "Select Completed shop scan" }));
  await user.click(screen.getByRole("button", { name: "Benchmark selected" }));
  const button = screen.getByRole("button", { name: "Benchmark 1 selected scans" });
  expect(button.disabled).toBe(true);
  await user.selectOptions(screen.getByLabelText("Ground truth for bulk benchmarks"), "4");
  expect(screen.queryByLabelText("Bulk evaluation model")).toBeNull();
  await user.click(button);
  expect(benchmarkUnbenchmarked).toHaveBeenCalledWith({
    run_kind: "site",
    run_ids: [1],
    dataset_id: 4,
  });
  expect((await screen.findByText(/Benchmarked 1 scans/)).textContent).toContain(
    "Benchmarked 1 scans",
  );
  expect(props.onChange).toHaveBeenCalled();
  await user.selectOptions(screen.getByLabelText("Benchmark status"), "all");
  await user.click(
    screen.getByRole("button", { name: "Open benchmark for Benchmarked shop scan" }),
  );
  expect(props.onOpen).toHaveBeenCalledWith(8);
});

test("benchmarks a stopped scan", async () => {
  const user = userEvent.setup();
  render(<CompletedScanBenchmarks {...props} />);
  await user.click(screen.getByRole("checkbox", { name: "Select Stopped shop scan" }));
  await user.click(screen.getByRole("button", { name: "Benchmark selected" }));
  await user.selectOptions(screen.getByLabelText("Ground truth for bulk benchmarks"), "4");
  await user.click(screen.getByRole("button", { name: "Benchmark 1 selected scans" }));
  expect(benchmarkUnbenchmarked).toHaveBeenCalledWith({
    run_kind: "site",
    run_ids: [3],
    dataset_id: 4,
  });
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
  expect(screen.getByText(/0 need a benchmark/)).toBeTruthy();
  expect(screen.queryByRole("link", { name: "Source" })).toBeNull();
});

test("shows completed legacy SAST evaluations in the benchmarked filter", async () => {
  const user = userEvent.setup();
  render(
    <CompletedScanBenchmarks
      {...props}
      category="sast"
      targets={{ sites: [], apis: [], sast_runs: [{ id: 7, name: "Source", status: "completed" }] }}
      legacy={[{ id: 3, sast_run_id: 7, status: "completed" }]}
    />,
  );
  await user.selectOptions(screen.getByLabelText("Benchmark status"), "done");
  expect(screen.getByRole("link", { name: "Open benchmark" }).getAttribute("href")).toBe(
    "#/benchmark-lab/evaluations/3",
  );
  expect(screen.getByRole("checkbox", { name: "Select Source" }).disabled).toBe(true);
});

for (const category of ["api"]) {
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
    expect(screen.queryByRole("checkbox", { name: "Select Benchmarked shop scan" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Benchmarked shop scan" })).toBeNull();
    await user.click(screen.getByRole("checkbox", { name: "Select Forum one" }));
    expect(all.indeterminate).toBe(true);
    await user.click(all);
    expect(all.checked).toBe(true);
    await user.click(all);
    expect(all.checked).toBe(false);
    await user.click(screen.getByRole("checkbox", { name: "Select Forum one" }));
    await user.click(screen.getByRole("checkbox", { name: "Select Forum two" }));
    await user.click(screen.getByRole("button", { name: "Benchmark selected" }));
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
    expect(screen.getByRole("button", { name: "Benchmark selected" })).toBeTruthy();
  });
}

test("DAST filters scans before selecting a batch", async () => {
  const user = userEvent.setup();
  render(<CompletedScanBenchmarks {...props} />);
  expect(screen.queryByRole("link", { name: "Benchmarked shop scan" })).toBeNull();
  await user.type(screen.getByLabelText("Search scans"), "stopped");
  expect(screen.queryByRole("link", { name: "Completed shop scan" })).toBeNull();
  await user.click(screen.getByRole("checkbox", { name: "Select Stopped shop scan" }));
  expect(screen.getByText("1 scans selected")).toBeTruthy();
  await user.clear(screen.getByLabelText("Search scans"));
  await user.selectOptions(screen.getByLabelText("Benchmark status"), "all");
  expect(screen.getByRole("link", { name: "Benchmarked shop scan" })).toBeTruthy();
  await user.selectOptions(screen.getByLabelText("Application"), "1");
  expect(screen.getByRole("link", { name: "Stopped shop scan" })).toBeTruthy();
});
