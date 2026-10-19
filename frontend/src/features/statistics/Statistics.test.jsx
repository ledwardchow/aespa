import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import * as statisticsApi from "../../shared/api/statistics.js";
import { StatisticsPage } from "./Statistics.jsx";

vi.mock("../../shared/api/statistics.js");

beforeEach(() => {
  vi.clearAllMocks();
  statisticsApi.getLLMStatistics.mockResolvedValue({
    rows: [],
    totals: { requests: 2, input_tokens: 120 },
    available_months: ["2026-10"],
    legacy_months: [],
  });
});

test("switches between monthly, all-time, daily, and weekly usage", async () => {
  const user = userEvent.setup();
  render(<StatisticsPage />);

  await waitFor(() =>
    expect(statisticsApi.getLLMStatistics).toHaveBeenCalledWith({
      view: "monthly",
      month: expect.stringMatching(/^\d{4}-\d{2}$/),
    }),
  );
  await user.click(screen.getByRole("button", { name: "All-time" }));
  await waitFor(() =>
    expect(statisticsApi.getLLMStatistics).toHaveBeenLastCalledWith({ view: "all_time" }),
  );

  await user.click(screen.getByRole("button", { name: "Daily" }));
  await waitFor(() =>
    expect(statisticsApi.getLLMStatistics).toHaveBeenLastCalledWith({
      view: "daily",
      date: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
    }),
  );
  await user.click(screen.getByRole("button", { name: "Weekly" }));
  await waitFor(() =>
    expect(statisticsApi.getLLMStatistics).toHaveBeenLastCalledWith({
      view: "weekly",
      date: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
    }),
  );
});

test("custom dates are inclusive and invalid ranges do not load", async () => {
  const user = userEvent.setup();
  render(<StatisticsPage />);
  await screen.findByText("2 calls");
  await user.click(screen.getByRole("button", { name: "Custom" }));
  fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-10-17" } });
  fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2026-10-19" } });
  await waitFor(() =>
    expect(statisticsApi.getLLMStatistics).toHaveBeenLastCalledWith({
      view: "custom",
      start: "2026-10-17",
      end: "2026-10-19",
    }),
  );

  const calls = statisticsApi.getLLMStatistics.mock.calls.length;
  fireEvent.change(screen.getByLabelText("End date"), { target: { value: "" } });
  expect(screen.getByText("Choose an end date on or after the start date.")).toBeTruthy();
  expect(statisticsApi.getLLMStatistics).toHaveBeenCalledTimes(calls);
});

test("date views explain monthly-only history", async () => {
  const month = new Date().toISOString().slice(0, 7);
  statisticsApi.getLLMStatistics.mockImplementation(async ({ view }) => ({
    rows: [],
    totals: {},
    available_months: [month],
    legacy_months: view === "daily" ? [month] : [],
  }));
  const user = userEvent.setup();
  render(<StatisticsPage />);
  await user.click(screen.getByRole("button", { name: "Daily" }));
  expect(await screen.findByText(/Older usage in .* was saved by month only/)).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Monthly" }));
  await waitFor(() => expect(screen.queryByText(/Older usage in/)).toBeNull());
});

test("groups models and fast mode by provider with provider cost totals", async () => {
  statisticsApi.getLLMStatistics.mockResolvedValue({
    rows: [
      {
        month: "2026-10",
        provider: "openai",
        model: "gpt-test",
        service_tier: "",
        requests: 2,
        estimated_total_cost_usd: 2.5,
      },
      {
        month: "2026-10",
        provider: "openai",
        model: "gpt-test",
        service_tier: "priority",
        requests: 1,
        estimated_total_cost_usd: 5,
      },
      {
        month: "2026-10",
        provider: "anthropic",
        model: "claude-test",
        service_tier: "",
        requests: 1,
        estimated_total_cost_usd: 3,
      },
    ],
    totals: { requests: 4 },
    available_months: ["2026-10"],
    legacy_months: [],
  });
  render(<StatisticsPage />);

  const openAI = (await screen.findByRole("heading", { name: "OpenAI" })).closest(".panel");
  const anthropic = screen.getByRole("heading", { name: "Anthropic" }).closest(".panel");
  expect(screen.getAllByRole("table")).toHaveLength(2);
  expect(within(openAI).getByText("$7.50")).toBeTruthy();
  expect(within(openAI).getByText("Fast mode")).toBeTruthy();
  expect(within(openAI).getAllByText("gpt-test")).toHaveLength(2);
  expect(within(anthropic).getAllByText("$3.00")).toHaveLength(2);
  expect(within(anthropic).queryByText("Fast mode")).toBeNull();
});
