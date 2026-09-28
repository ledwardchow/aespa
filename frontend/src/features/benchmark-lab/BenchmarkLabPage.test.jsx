import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import * as benchmarkApi from "../../shared/api/benchmarkLab.js";
import * as settingsApi from "../../shared/api/settings.js";
import { BenchmarkLabPage } from "./BenchmarkLabPage.jsx";

vi.mock("../../shared/api/benchmarkLab.js");
vi.mock("../../shared/api/settings.js");

beforeEach(() => {
  vi.clearAllMocks();
  benchmarkApi.listBenchmarkTargets.mockResolvedValue({
    sites: [
      {
        id: 1,
        name: "Shop",
        dataset: { id: 3, name: "Shop truth", item_count: 2 },
        runs: [
          {
            id: 9,
            name: "Shop scan",
            status: "complete",
            default_evaluation_model: { id: 6, name: "Test Lead model" },
          },
        ],
      },
    ],
    apis: [{ id: 2, name: "Shop API", dataset: null, runs: [] }],
    sast_runs: [{ id: 7, name: "Source scan", status: "completed" }],
  });
  benchmarkApi.listBenchmarkDatasets.mockResolvedValue([
    { id: 3, name: "Shop truth", item_count: 2 },
  ]);
  benchmarkApi.listBenchmarkResults.mockResolvedValue([]);
  benchmarkApi.listBenchmarkEvaluations.mockResolvedValue([]);
  settingsApi.listLLMModels.mockResolvedValue([
    { id: 6, name: "Test Lead model" },
    { id: 8, name: "Evaluator model" },
  ]);
  benchmarkApi.createBenchmarkResult.mockResolvedValue({
    id: 4,
    run_kind: "site",
    target_kind: "site",
    run_id: 9,
    target_id: 1,
    run_name: "Shop scan",
    comparison: { method: "model", model: { id: 6, name: "Test Lead model" } },
    scan_models: {
      test_lead: { id: 9, name: "Scan Test Lead", model: "scan-model" },
      sast: [
        {
          run_id: 7,
          run_name: "Source scan",
          model: { id: 10, name: "SAST agent", model: "sast-model" },
        },
      ],
    },
    created_at: "2026-09-27T00:00:00Z",
    summary: { full: 1, partial: 0, missing: 1 },
    ground_truth: {
      name: "Shop truth",
      items: [
        { external_id: "GT-1", title: "SQL injection" },
        { external_id: "GT-2", title: "Missing logging" },
      ],
    },
    findings: [{ id: 12, reference: "SITE-001", title: "SQL injection" }],
    rows: [
      { external_id: "GT-1", disposition: "full", finding_ids: [12], reason: "Matched" },
      { external_id: "GT-2", disposition: "missing", finding_ids: [], reason: "No match" },
    ],
  });
});

test("compares a Site scan and shows every ground truth finding", async () => {
  const user = userEvent.setup();
  render(<BenchmarkLabPage />);
  await user.selectOptions(await screen.findByLabelText("Site"), "1");
  await user.click(screen.getByRole("tab", { name: "New" }));
  await user.selectOptions(screen.getByLabelText("Completed scan"), "9");
  await user.click(screen.getByRole("button", { name: "Compare scan" }));

  expect(benchmarkApi.createBenchmarkResult).toHaveBeenCalledWith({
    run_kind: "site",
    run_id: 9,
  });
  expect(await screen.findByText(/GT-1 - SQL injection/)).toBeTruthy();
  expect(screen.getByText(/GT-2 - Missing logging/)).toBeTruthy();
  expect(screen.getByText("SITE-001")).toBeTruthy();
  expect(screen.getByText("Compared by Test Lead model")).toBeTruthy();
  expect(screen.getByText("Test Lead model: Scan Test Lead (scan-model)")).toBeTruthy();
  expect(screen.getByText("SAST model (Source scan): SAST agent (sast-model)")).toBeTruthy();
});

test("allows an explicit evaluation model", async () => {
  const user = userEvent.setup();
  render(<BenchmarkLabPage />);
  await user.selectOptions(await screen.findByLabelText("Site"), "1");
  await user.click(screen.getByRole("tab", { name: "New" }));
  await user.selectOptions(screen.getByLabelText("Completed scan"), "9");
  expect(
    screen.getByRole("option", { name: "Scan's Test Lead model: Test Lead model" }),
  ).toBeTruthy();
  await user.selectOptions(screen.getByLabelText("Evaluation model"), "8");
  await user.click(screen.getByRole("button", { name: "Compare scan" }));
  expect(benchmarkApi.createBenchmarkResult).toHaveBeenCalledWith({
    run_kind: "site",
    run_id: 9,
    evaluation_model_id: 8,
  });
});

test("requires a model when the scan has no Test Lead model", async () => {
  const user = userEvent.setup();
  benchmarkApi.listBenchmarkTargets.mockResolvedValue({
    sites: [
      {
        id: 1,
        name: "Shop",
        dataset: { id: 3, name: "Shop truth", item_count: 2 },
        runs: [{ id: 9, name: "Shop scan", status: "complete", default_evaluation_model: null }],
      },
    ],
    apis: [],
    sast_runs: [],
  });
  render(<BenchmarkLabPage />);
  await user.selectOptions(await screen.findByLabelText("Site"), "1");
  await user.click(screen.getByRole("tab", { name: "New" }));
  await user.selectOptions(screen.getByLabelText("Completed scan"), "9");
  expect(screen.getByRole("button", { name: "Compare scan" }).disabled).toBe(true);
  await user.selectOptions(screen.getByLabelText("Evaluation model"), "8");
  expect(screen.getByRole("button", { name: "Compare scan" }).disabled).toBe(false);
  expect(screen.queryByRole("option", { name: "Rules only" })).toBeNull();
});

test("deletes a saved comparison result", async () => {
  const user = userEvent.setup();
  const result = await benchmarkApi.createBenchmarkResult();
  benchmarkApi.listBenchmarkResults.mockResolvedValue([result]);
  benchmarkApi.deleteBenchmarkResult.mockResolvedValue(undefined);
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
  try {
    render(<BenchmarkLabPage />);
    await user.selectOptions(await screen.findByLabelText("Site"), "1");
    await user.click(screen.getByRole("tab", { name: "Analyses" }));
    await user.click(screen.getByRole("button", { name: "Open Shop scan" }));
    await user.click(screen.getByRole("button", { name: "Delete result" }));
    expect(benchmarkApi.deleteBenchmarkResult).toHaveBeenCalledWith(4);
    expect(screen.queryByText("Compared by Test Lead model")).toBeNull();
  } finally {
    confirm.mockRestore();
  }
});

test("Site summary plots saved DAST and SAST analyses and filters both", async () => {
  const user = userEvent.setup();
  const dast = { ...(await benchmarkApi.createBenchmarkResult()), scan_cost_usd: 0.42 };
  const sast = {
    ...dast,
    id: 5,
    run_kind: "sast",
    run_name: "Source scan",
    scan_cost_usd: 0.15,
    scan_models: { test_lead: null, sast: [{ run_id: 7, model: { name: "SAST agent" } }] },
  };
  benchmarkApi.listBenchmarkResults.mockResolvedValue([dast, sast]);
  render(<BenchmarkLabPage />);
  await user.selectOptions(await screen.findByLabelText("Site"), "1");
  expect(screen.getByRole("button", { name: /Shop scan, DAST, Scan Test Lead/ })).toBeTruthy();
  expect(screen.getByRole("button", { name: /Source scan, SAST, SAST agent/ })).toBeTruthy();
  await user.click(screen.getByRole("checkbox", { name: "SAST" }));
  expect(screen.queryByRole("button", { name: /Source scan, SAST, SAST agent/ })).toBeNull();
  await user.click(screen.getByRole("checkbox", { name: "SAST" }));
  await user.click(screen.getByRole("checkbox", { name: "SAST agent" }));
  expect(screen.queryByRole("button", { name: /Source scan, SAST, SAST agent/ })).toBeNull();
  await user.click(screen.getByRole("tab", { name: "Analyses" }));
  expect(screen.getByRole("button", { name: "Open Source scan" })).toBeTruthy();
});

test("Site includes older SAST analyses that used its ground truth", async () => {
  const user = userEvent.setup();
  const result = {
    ...(await benchmarkApi.createBenchmarkResult()),
    id: 6,
    run_kind: "sast",
    target_kind: null,
    target_id: null,
    dataset_id: 3,
    run_name: "Older source scan",
    scan_cost_usd: 0.2,
  };
  benchmarkApi.listBenchmarkResults.mockResolvedValue([result]);
  render(<BenchmarkLabPage />);
  await user.selectOptions(await screen.findByLabelText("Site"), "1");
  await user.click(screen.getByRole("tab", { name: "Analyses" }));
  expect(screen.getByRole("button", { name: "Open Older source scan" })).toBeTruthy();
});

test("SAST can choose saved Site ground truth", async () => {
  const user = userEvent.setup();
  benchmarkApi.createBenchmarkResult.mockResolvedValue({
    ...(await benchmarkApi.createBenchmarkResult()),
    id: 5,
    run_kind: "sast",
    run_id: 7,
    target_id: null,
  });
  render(<BenchmarkLabPage />);
  await user.click(await screen.findByRole("tab", { name: "SAST" }));
  await user.selectOptions(screen.getByLabelText("Completed SAST scan"), "7");
  await user.selectOptions(screen.getByLabelText("Ground truth"), "3");
  await user.selectOptions(screen.getByLabelText("Evaluation model"), "6");
  await user.click(screen.getByRole("button", { name: "Compare scan" }));
  expect(benchmarkApi.createBenchmarkResult).toHaveBeenCalledWith({
    run_kind: "sast",
    run_id: 7,
    dataset_id: 3,
    evaluation_model_id: 6,
  });
});
