import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { modelName, SiteSummary } from "./SiteSummary.jsx";

const results = [
  {
    id: 1,
    run_name: "DAST only",
    run_kind: "site",
    scan_models: { primary: { name: "Shared model" } },
  },
  {
    id: 2,
    run_name: "Combined scan",
    run_kind: "site",
    scan_models: { primary: { name: "Shared model" }, sast: [{ run_id: 7 }] },
  },
  {
    id: 3,
    run_name: "Source scan",
    run_kind: "sast",
    scan_models: { primary: { name: "Shared model" } },
  },
].map((result) => ({
  ...result,
  scan_cost_usd: result.id / 10,
  summary: { full: result.id, partial: 0 },
}));

test("separates scan types with independent filters and shapes for the same model", async () => {
  const user = userEvent.setup();
  const onOpen = vi.fn();
  render(<SiteSummary results={results} onOpen={onOpen} />);
  const point = (name) => screen.queryByRole("button", { name: new RegExp(`^${name},`) });
  expect(point("DAST only").querySelector("circle")).toBeTruthy();
  expect(point("Combined scan").querySelector("rect")).toBeTruthy();
  expect(point("Source scan").querySelector("path")).toBeTruthy();
  await user.click(screen.getByLabelText("Scan type", { selector: "summary" }));
  await user.click(screen.getByRole("checkbox", { name: "DAST", exact: true }));
  expect(point("DAST only")).toBeNull();
  expect(point("Combined scan")).toBeTruthy();
  expect(point("Source scan")).toBeTruthy();
  await user.click(screen.getByRole("checkbox", { name: "DAST", exact: true }));
  await user.click(screen.getByRole("checkbox", { name: "DAST with SAST Leads", exact: true }));
  expect(point("DAST only")).toBeTruthy();
  expect(point("Combined scan")).toBeNull();
  await user.click(point("DAST only"));
  expect(onOpen).toHaveBeenCalledWith(1);
  await user.click(screen.getByLabelText("Model"));
  await user.click(screen.getByRole("checkbox", { name: "Shared model" }));
  expect(screen.queryAllByRole("button")).toHaveLength(0);
});

test("select all clears and restores each dropdown with a partial selection indicator", async () => {
  const user = userEvent.setup();
  render(<SiteSummary results={results} onOpen={vi.fn()} />);
  await user.click(screen.getByLabelText("Scan type", { selector: "summary" }));
  const types = within(
    screen.getByLabelText("Scan type", { selector: "summary" }).parentElement,
  ).getByRole("checkbox", { name: "Select all" });
  expect(types.checked).toBe(true);
  await user.click(screen.getByRole("checkbox", { name: "DAST", exact: true }));
  expect(types.indeterminate).toBe(true);
  await user.click(types);
  expect(types.checked).toBe(true);
  expect(types.indeterminate).toBe(false);
  await user.click(types);
  expect(screen.queryByRole("button", { name: /^Combined scan,/ })).toBeNull();
  expect(screen.queryByRole("button", { name: /^Source scan,/ })).toBeNull();
  await user.click(types);
  expect(screen.getByRole("button", { name: /^Combined scan,/ })).toBeTruthy();
  await user.click(screen.getByLabelText("Model"));
  const models = within(screen.getByLabelText("Model").parentElement).getByRole("checkbox", {
    name: "Select all",
  });
  await user.click(models);
  expect(screen.queryByRole("button", { name: /^Combined scan,/ })).toBeNull();
  await user.click(models);
  expect(screen.getByRole("button", { name: /^Combined scan,/ })).toBeTruthy();
});

test("shows immediate point details on hover and keyboard focus", async () => {
  const user = userEvent.setup();
  render(<SiteSummary results={results} onOpen={vi.fn()} />);
  const point = screen.getByRole("button", { name: /^Combined scan,/ });
  await user.hover(point);
  expect(screen.getByRole("tooltip").textContent).toContain("Combined scan");
  expect(screen.getByRole("tooltip").textContent).toContain("Shared model");
  expect(screen.getByRole("tooltip").textContent).toContain("DAST with SAST Leads");
  await user.unhover(point);
  expect(screen.queryByRole("tooltip")).toBeNull();
  point.focus();
  expect(await screen.findByRole("tooltip")).toBeTruthy();
});

test("hides zero findings and plots scan dates even when cost is unavailable", async () => {
  const user = userEvent.setup();
  const dated = results.map((result) => ({
    ...result,
    scan_started_at: `2026-09-30T0${result.id}:00:00Z`,
    scan_cost_usd: null,
  }));
  render(
    <SiteSummary
      results={[
        ...dated,
        {
          ...results[0],
          id: 9,
          run_name: "No findings",
          summary: { full: 0, partial: 0 },
          scan_started_at: "2026-09-30T12:00:00Z",
        },
      ]}
      onOpen={vi.fn()}
    />,
  );
  expect(screen.queryByRole("button", { name: /^No findings,/ })).toBeNull();
  await user.selectOptions(screen.getByLabelText("Compare by"), "date");
  expect(
    screen.getByRole("img", { name: "Scan date versus full and partial findings" }),
  ).toBeTruthy();
  expect(screen.getByRole("button", { name: /^Combined scan,/ })).toBeTruthy();
  expect(screen.queryByRole("button", { name: /^No findings,/ })).toBeNull();
});

test("groups model names by the last slash or dot segment", async () => {
  const user = userEvent.setup();
  const aliases = ["provider/region.sonnet", "global.vendor.sonnet", "sonnet"];
  render(
    <SiteSummary
      results={results.map((result, i) => ({
        ...result,
        scan_models: { ...result.scan_models, primary: { name: aliases[i] } },
      }))}
      onOpen={vi.fn()}
    />,
  );
  await user.click(screen.getByLabelText("Model"));
  expect(screen.getByRole("checkbox", { name: "sonnet", exact: true })).toBeTruthy();
  await user.click(screen.getByRole("checkbox", { name: "sonnet", exact: true }));
  expect(screen.queryByRole("button", { name: /^Combined scan,/ })).toBeNull();
  expect(screen.queryByRole("button", { name: /^DAST only,/ })).toBeNull();
  expect(screen.queryByRole("button", { name: /^Source scan,/ })).toBeNull();
});

test.each([
  ["qwen3.8-27b", "qwen3.8-27b"],
  ["qwen/qwen3.8-27b", "qwen3.8-27b"],
  ["global.vendor.qwen3.8-27b", "qwen3.8-27b"],
  ["provider/region.vendor.qwen3.8-27b", "qwen3.8-27b"],
  ["global.anthropic.claude-4.5-sonnet", "claude-4.5-sonnet"],
  ["openai/gpt-4.1-mini", "gpt-4.1-mini"],
  ["vendor.model-3.8.1", "model-3.8.1"],
  ["global.anthropic.claude-sonnet-5", "claude-sonnet-5"],
])("normalizes %s to %s without losing version numbers", (name, expected) => {
  expect(modelName({ scan_models: { primary: { name } } })).toBe(expected);
});

test("legend toggles labeled fits and recalculates when filtering or changing axes", async () => {
  const user = userEvent.setup();
  render(
    <SiteSummary
      results={results.map((result) => ({
        ...result,
        scan_started_at: `2026-09-30T0${result.id}:00:00Z`,
      }))}
      onOpen={vi.fn()}
    />,
  );
  const legend = screen.getByRole("button", { name: "Shared model", exact: true });
  expect(legend.getAttribute("aria-pressed")).toBe("true");
  expect(screen.getByRole("img", { name: "Shared model linear trend" }).textContent).toContain(
    "Shared model",
  );
  await user.selectOptions(screen.getByLabelText("Compare by"), "date");
  expect(screen.getByRole("img", { name: "Shared model linear trend" })).toBeTruthy();
  await user.click(legend);
  expect(screen.queryByRole("img", { name: "Shared model linear trend" })).toBeNull();
  expect(legend.getAttribute("aria-pressed")).toBe("false");
  await user.click(legend);
  expect(screen.getByRole("img", { name: "Shared model linear trend" })).toBeTruthy();
});

test("scan type trendlines start off and fit only visible scans of each type", async () => {
  const user = userEvent.setup();
  const repeated = results.flatMap((result) => [
    result,
    {
      ...result,
      id: result.id + 10,
      run_name: `${result.run_name} again`,
      scan_cost_usd: result.scan_cost_usd + 0.1,
      summary: { full: result.summary.full + 1, partial: 0 },
    },
  ]);
  render(<SiteSummary results={repeated} onOpen={vi.fn()} />);
  const types = ["DAST", "DAST with SAST Leads", "SAST"];
  const controls = within(screen.getByRole("group", { name: "Scan type trendlines" }));
  for (const type of types) {
    expect(controls.getByRole("checkbox", { name: `${type} trendline` }).checked).toBe(false);
    expect(screen.queryByRole("img", { name: `${type} linear trend` })).toBeNull();
    await user.click(controls.getByRole("checkbox", { name: `${type} trendline` }));
    expect(screen.getByRole("img", { name: `${type} linear trend` })).toBeTruthy();
  }
  await user.click(screen.getByLabelText("Scan type", { selector: "summary" }));
  await user.click(screen.getByRole("checkbox", { name: "DAST", exact: true }));
  expect(screen.queryByRole("img", { name: "DAST linear trend" })).toBeNull();
  expect(screen.getByRole("img", { name: "DAST with SAST Leads linear trend" })).toBeTruthy();
  await user.click(controls.getByRole("checkbox", { name: "SAST trendline" }));
  expect(screen.queryByRole("img", { name: "SAST linear trend" })).toBeNull();
});
