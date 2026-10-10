import { act, render, screen, within } from "@testing-library/react";
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
  expect(screen.getByLabelText("Display").value).toBe("optimal");
  expect(screen.getByRole("img", { name: "Optimal: best findings for cost" })).toBeTruthy();
  const point = (name) =>
    screen.queryByRole("button", { name: new RegExp(`^(?:Optimal, )?${name},`) });
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
  expect(
    screen.queryAllByRole("button", {
      name: /^(?:Optimal, )?(DAST only|Combined scan|Source scan),/,
    }),
  ).toHaveLength(0);
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
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?Combined scan,/ })).toBeNull();
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?Source scan,/ })).toBeNull();
  await user.click(types);
  expect(screen.getByRole("button", { name: /^(?:Optimal, )?Combined scan,/ })).toBeTruthy();
  await user.click(screen.getByLabelText("Model"));
  const models = within(screen.getByLabelText("Model").parentElement).getByRole("checkbox", {
    name: "Select all",
  });
  await user.click(models);
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?Combined scan,/ })).toBeNull();
  await user.click(models);
  expect(screen.getByRole("button", { name: /^(?:Optimal, )?Combined scan,/ })).toBeTruthy();
});

test("shows immediate point details on hover and keyboard focus", async () => {
  const user = userEvent.setup();
  render(<SiteSummary results={results} onOpen={vi.fn()} />);
  const point = screen.getByRole("button", { name: /^(?:Optimal, )?Combined scan,/ });
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
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?No findings,/ })).toBeNull();
  await user.selectOptions(screen.getByLabelText("Compare by"), "date");
  expect(
    screen.getByRole("img", { name: "Scan date versus full and partial findings" }),
  ).toBeTruthy();
  expect(screen.getByRole("button", { name: /^(?:Optimal, )?Combined scan,/ })).toBeTruthy();
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?No findings,/ })).toBeNull();
});

test("plots severity score and leaves analyses without a score out of that view", async () => {
  const user = userEvent.setup();
  const scored = results.map((result, index) => ({
    ...result,
    score: index === 0 ? 0 : index === 1 ? 5 : null,
    category_counts: index === 1 ? { "A01: Broken Access Control": 2, "A03: Injection": 1 } : null,
    category_totals: index === 1 ? { "A01: Broken Access Control": 3, "A03: Injection": 2 } : null,
  }));
  render(<SiteSummary results={scored} onOpen={vi.fn()} />);
  expect(screen.getByRole("option", { name: "Scan cost/matched findings" })).toBeTruthy();
  await user.selectOptions(screen.getByLabelText("Compare by"), "score");
  expect(
    screen.getByRole("img", { name: "Scan cost versus severity-weighted score" }),
  ).toBeTruthy();
  expect(screen.getByText("Score", { selector: "text" })).toBeTruthy();
  expect(screen.getByRole("button", { name: /DAST only,.*0 score/ })).toBeTruthy();
  expect(screen.getByRole("button", { name: /Combined scan,.*5 score/ })).toBeTruthy();
  expect(screen.queryByRole("button", { name: /Source scan,/ })).toBeNull();
  expect(screen.getByText(/1 matching analysis has no saved score/)).toBeTruthy();
  expect(screen.getByRole("img", { name: "Optimal: best score for cost" })).toBeTruthy();
  await user.hover(screen.getByRole("button", { name: /Combined scan,.*5 score/ }));
  const tooltip = screen.getByRole("tooltip");
  expect(tooltip.textContent).toContain("Matched / ground truth by OWASP category");
  expect(tooltip.textContent).toContain("A01: Broken Access Control2/3");
  expect(tooltip.textContent).toContain("A03: Injection1/2");
});

test("plots score by scan date even when scan cost is unavailable", async () => {
  const user = userEvent.setup();
  const dated = results.map((result) => ({
    ...result,
    score: result.id + 2,
    scan_cost_usd: null,
    scan_started_at: `2026-09-30T0${result.id}:00:00Z`,
  }));
  render(<SiteSummary results={dated} onOpen={vi.fn()} />);
  expect(screen.getByRole("option", { name: "Scan date/matched findings" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "Scan date/score" })).toBeTruthy();
  await user.selectOptions(screen.getByLabelText("Compare by"), "date-score");
  expect(screen.getByLabelText("Display").value).toBe("model");
  expect(screen.getByRole("heading", { name: "Scan date and score" })).toBeTruthy();
  expect(
    screen.getByRole("img", { name: "Scan date versus severity-weighted score" }),
  ).toBeTruthy();
  expect(screen.getByRole("button", { name: /Combined scan,.*4 score/ })).toBeTruthy();
  await user.selectOptions(screen.getByLabelText("Display"), "optimal");
  expect(screen.getByLabelText("Compare by").value).toBe("score");
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
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?Combined scan,/ })).toBeNull();
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?DAST only,/ })).toBeNull();
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?Source scan,/ })).toBeNull();
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

test("model legend toggles points and trendlines together across axes", async () => {
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
  await user.selectOptions(screen.getByLabelText("Display"), "model");
  const legend = screen.getByRole("button", { name: /^Shared model(?:, Optimal)?$/, exact: true });
  expect(legend.getAttribute("aria-pressed")).toBe("true");
  expect(screen.getByRole("img", { name: "Shared model linear trend" }).textContent).toContain(
    "Shared model",
  );
  await user.selectOptions(screen.getByLabelText("Compare by"), "date");
  expect(screen.getByRole("img", { name: "Shared model linear trend" })).toBeTruthy();
  await user.click(legend);
  expect(screen.queryByRole("img", { name: "Shared model linear trend" })).toBeNull();
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?DAST only,/ })).toBeNull();
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?Combined scan,/ })).toBeNull();
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?Source scan,/ })).toBeNull();
  expect(legend.getAttribute("aria-pressed")).toBe("false");
  await user.click(legend);
  expect(screen.getByRole("img", { name: "Shared model linear trend" })).toBeTruthy();
  expect(screen.getByRole("button", { name: /^(?:Optimal, )?Combined scan,/ })).toBeTruthy();
});

test("single-scan models stay enabled in the legend and share dropdown visibility", async () => {
  const user = userEvent.setup();
  render(
    <SiteSummary
      results={[
        ...results,
        {
          ...results[0],
          id: 4,
          run_name: "Single scan",
          scan_models: { primary: { name: "Single model" } },
        },
      ]}
      onOpen={vi.fn()}
    />,
  );
  const legend = screen.getByRole("button", { name: /^Single model(?:, Optimal)?$/, exact: true });
  expect(legend.disabled).toBe(false);
  expect(legend.getAttribute("aria-pressed")).toBe("true");
  await user.click(legend);
  expect(legend.getAttribute("aria-pressed")).toBe("false");
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?Single scan,/ })).toBeNull();
  expect(screen.queryByLabelText("Single model single scan")).toBeNull();
  expect(screen.getByRole("button", { name: /^(?:Optimal, )?Combined scan,/ }).style.opacity).toBe(
    "1",
  );
  await user.hover(legend);
  expect(screen.getByRole("button", { name: /^(?:Optimal, )?Combined scan,/ }).style.opacity).toBe(
    "1",
  );
  await user.click(screen.getByLabelText("Model"));
  const checkbox = screen.getByRole("checkbox", { name: "Single model", exact: true });
  expect(checkbox.checked).toBe(false);
  await user.click(checkbox);
  expect(legend.getAttribute("aria-pressed")).toBe("true");
  expect(screen.getByRole("button", { name: /^(?:Optimal, )?Single scan,/ })).toBeTruthy();
  await user.click(checkbox);
  expect(legend.getAttribute("aria-pressed")).toBe("false");
  await user.click(legend);
  expect(checkbox.checked).toBe(true);
});

test("display modes select only their own lines across axes and filters", async () => {
  const user = userEvent.setup();
  const pairs = [
    ...results,
    ...results.map((result) => ({
      ...result,
      id: result.id + 3,
      scan_cost_usd: result.scan_cost_usd + 1,
      summary: { full: result.summary.full + 2, partial: 0 },
    })),
  ].map((result) => ({ ...result, scan_started_at: `2026-09-${20 + result.id}T09:00:00Z` }));
  render(<SiteSummary results={pairs} onOpen={vi.fn()} />);
  expect(screen.getByLabelText("Display").value).toBe("optimal");
  expect(screen.queryByRole("option", { name: "Standard" })).toBeNull();
  expect(screen.queryByRole("img", { name: "Shared model linear trend" })).toBeNull();
  await user.selectOptions(screen.getByLabelText("Display"), "model");
  expect(screen.getByRole("img", { name: "Shared model linear trend" })).toBeTruthy();
  expect(screen.queryByRole("img", { name: "Optimal: best findings for cost" })).toBeNull();
  await user.selectOptions(screen.getByLabelText("Display"), "scan-type");
  expect(screen.queryByRole("img", { name: "Shared model linear trend" })).toBeNull();
  for (const type of ["DAST", "DAST with SAST Leads", "SAST"])
    expect(screen.getByRole("img", { name: `${type} scan type linear trend` })).toBeTruthy();
  await user.selectOptions(screen.getByLabelText("Compare by"), "date");
  expect(screen.getByLabelText("Display").value).toBe("scan-type");
  await user.click(screen.getByRole("button", { name: "DAST", exact: true }));
  expect(screen.queryByRole("img", { name: "DAST scan type linear trend" })).toBeNull();
  expect(screen.queryByRole("button", { name: /^DAST only,/ })).toBeNull();
  expect(screen.getByRole("img", { name: "SAST scan type linear trend" })).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "DAST", exact: true }));
  expect(screen.getByRole("img", { name: "DAST scan type linear trend" })).toBeTruthy();
  await user.selectOptions(screen.getByLabelText("Display"), "optimal");
  expect(screen.getByLabelText("Compare by").value).toBe("cost");
  expect(screen.queryByRole("img", { name: "SAST scan type linear trend" })).toBeNull();
});

test("scan type legend can hide single scans that have no trendline", async () => {
  const user = userEvent.setup();
  render(<SiteSummary results={results} onOpen={vi.fn()} />);
  await user.selectOptions(screen.getByLabelText("Display"), "scan-type");
  expect(screen.queryAllByRole("img", { name: /scan type linear trend$/ })).toHaveLength(0);
  const toggle = screen.getByRole("button", { name: "SAST", exact: true });
  expect(toggle.disabled).toBe(false);
  await user.click(toggle);
  expect(screen.queryByRole("button", { name: /^Source scan,/ })).toBeNull();
});

test("legend hover previews models and scan types and restores the graph on leave", async () => {
  const user = userEvent.setup();
  render(
    <SiteSummary
      results={[
        ...results,
        {
          ...results[0],
          id: 4,
          run_name: "Other scan",
          scan_models: { primary: { name: "Other model" } },
        },
      ]}
      onOpen={vi.fn()}
    />,
  );
  await user.selectOptions(screen.getByLabelText("Display"), "model");
  const sharedPoint = screen.getByRole("button", { name: /^(?:Optimal, )?DAST only,/ });
  const sourcePoint = screen.getByRole("button", { name: /^(?:Optimal, )?Source scan,/ });
  const otherPoint = screen.getByRole("button", { name: /^(?:Optimal, )?Other scan,/ });
  const trend = screen.getByRole("img", { name: "Shared model linear trend" });
  const single = screen.getByLabelText("Other model single scan").parentElement;
  const legend = screen.getByRole("button", { name: /^Shared model(?:, Optimal)?$/, exact: true });
  await user.hover(legend);
  expect(sharedPoint.style.opacity).toBe("1");
  expect(sourcePoint.style.opacity).toBe("1");
  expect(trend.style.opacity).toBe("1");
  expect(otherPoint.style.opacity).toBe("0.15");
  expect(single.style.opacity).toBe("0.15");
  expect(legend.getAttribute("aria-pressed")).toBe("true");
  await user.unhover(legend);
  expect(otherPoint.style.opacity).toBe("1");
  expect(single.style.opacity).toBe("1");
  // Single-scan models preview their points too.
  const otherLegend = screen.getByRole("button", {
    name: /^Other model(?:, Optimal)?$/,
    exact: true,
  });
  expect(otherLegend.disabled).toBe(false);
  await user.hover(otherLegend);
  expect(otherPoint.style.opacity).toBe("1");
  expect(single.style.opacity).toBe("1");
  expect(sharedPoint.style.opacity).toBe("0.15");
  expect(trend.style.opacity).toBe("0.15");
  await user.unhover(otherLegend);
  const typeLegend = screen.getByRole("button", { name: "DAST", exact: true });
  await user.hover(typeLegend);
  expect(sharedPoint.style.opacity).toBe("1");
  expect(otherPoint.style.opacity).toBe("1");
  expect(sourcePoint.style.opacity).toBe("0.15");
  expect(trend.style.opacity).toBe("0.15");
  await user.unhover(typeLegend);
  expect(sourcePoint.style.opacity).toBe("1");
  act(() => legend.focus());
  expect(await screen.findByRole("button", { name: /^(?:Optimal, )?Other scan,/ })).toBeTruthy();
  expect(otherPoint.style.opacity).toBe("0.15");
  act(() => legend.blur());
  await user.hover(otherPoint);
  expect(sharedPoint.style.opacity).toBe("1");
});

test("Optimal display connects the best cost results and marks their models, following filters", async () => {
  const user = userEvent.setup();
  const scans = [
    { cost: 0.1, count: 10, model: "A" },
    { cost: 0.2, count: 15, model: "B" },
    { cost: 0.3, count: 12, model: "C" },
    { cost: 0.4, count: 20, model: "D" },
    { cost: null, count: 30, model: "Unknown cost" },
  ].map((scan, index) => ({
    ...results[0],
    id: index + 1,
    run_name: `Scan ${index}`,
    scan_cost_usd: scan.cost,
    scan_models: { primary: { name: scan.model } },
    summary: { full: scan.count, partial: 0 },
    scan_started_at: "2026-10-03T00:00:00Z",
  }));
  render(<SiteSummary results={scans} onOpen={vi.fn()} />);
  await user.selectOptions(screen.getByLabelText("Compare by"), "date");
  await user.selectOptions(screen.getByLabelText("Display"), "optimal");
  expect(screen.getByLabelText("Compare by").value).toBe("cost");
  const line = screen.getByRole("img", { name: "Optimal: best findings for cost" });
  expect(line.querySelector("polyline").getAttribute("points").split(" ")).toHaveLength(3);
  expect(line.querySelector("text").textContent).toBe("Optimal");
  expect(screen.getByLabelText("A optimal model").textContent).toBe("A");
  expect(screen.getByLabelText("B optimal model").textContent).toBe("B");
  expect(screen.getByLabelText("D optimal model").textContent).toBe("D");
  expect(screen.queryByLabelText("C optimal model")).toBeNull();
  expect(screen.getByRole("button", { name: "A, Optimal", exact: true })).toBeTruthy();
  expect(screen.getByRole("button", { name: "B, Optimal", exact: true })).toBeTruthy();
  expect(screen.getByRole("button", { name: "C", exact: true })).toBeTruthy();
  expect(
    screen.getByRole("button", { name: /^Optimal, Scan 0,/ }).querySelectorAll("circle"),
  ).toHaveLength(2);
  await user.click(screen.getByLabelText("Model", { selector: "summary" }));
  await user.click(screen.getByRole("checkbox", { name: "C", exact: true }));
  await user.click(screen.getByRole("checkbox", { name: "B", exact: true }));
  expect(screen.getByRole("button", { name: "C, Optimal", exact: true })).toBeTruthy();
  expect(screen.getByLabelText("C optimal model").textContent).toBe("C");
  await user.selectOptions(screen.getByLabelText("Compare by"), "date");
  expect(screen.getByLabelText("Display").value).toBe("model");
  expect(screen.queryByRole("img", { name: "Optimal: best findings for cost" })).toBeNull();
});

test("defaults hide non-optimal single-result models and preserve explicit visibility choices", async () => {
  const user = userEvent.setup();
  const scans = [
    { model: "Repeated", cost: 0.1, count: 10 },
    { model: "Repeated", cost: 0.2, count: 11 },
    { model: "Optimal single", cost: 0.3, count: 20 },
    { model: "Hidden single", cost: 0.4, count: 12 },
    { model: "Tied single", cost: 0.3, count: 20 },
  ].map((scan, index) => ({
    ...results[0],
    id: index + 1,
    run_name: scan.model + index,
    scan_models: { primary: { name: scan.model } },
    scan_cost_usd: scan.cost,
    summary: { full: scan.count, partial: 0 },
    scan_started_at: "2026-10-03T00:00:00Z",
  }));
  const { rerender } = render(<SiteSummary results={[]} onOpen={vi.fn()} />);
  rerender(<SiteSummary results={scans} onOpen={vi.fn()} />);
  const hidden = screen.getByRole("button", { name: "Hidden single", exact: true });
  expect(hidden.getAttribute("aria-pressed")).toBe("false");
  expect(screen.queryByRole("button", { name: /^(?:Optimal, )?Hidden single3,/ })).toBeNull();
  expect(
    screen
      .getByRole("button", { name: /^Repeated(?:, Optimal)?$/, exact: true })
      .getAttribute("aria-pressed"),
  ).toBe("true");
  expect(
    screen
      .getByRole("button", { name: /^Optimal single(?:, Optimal)?$/, exact: true })
      .getAttribute("aria-pressed"),
  ).toBe("true");
  expect(
    screen
      .getByRole("button", { name: /^Tied single(?:, Optimal)?$/, exact: true })
      .getAttribute("aria-pressed"),
  ).toBe("true");
  await user.click(hidden);
  expect(screen.getByRole("button", { name: /^(?:Optimal, )?Hidden single3,/ })).toBeTruthy();
  rerender(<SiteSummary results={[...scans]} onOpen={vi.fn()} />);
  expect(hidden.getAttribute("aria-pressed")).toBe("true");
  await user.selectOptions(screen.getByLabelText("Compare by"), "date");
  expect(screen.getByRole("button", { name: /^(?:Optimal, )?Hidden single3,/ })).toBeTruthy();
  await user.click(screen.getByLabelText("Model", { selector: "summary" }));
  const selectAll = screen.getAllByRole("checkbox", { name: "Select all", exact: true }).at(-1);
  await user.click(selectAll);
  expect(hidden.getAttribute("aria-pressed")).toBe("false");
  await user.click(selectAll);
  expect(hidden.getAttribute("aria-pressed")).toBe("true");
});

test("point label guides draw above every scan point with an outline and source marker", () => {
  const { container } = render(<SiteSummary results={results} onOpen={vi.fn()} />);
  const guide = container.querySelector('[data-guide-label="Shared model"]');
  const points = [...container.querySelectorAll(".benchmark-chart-point")];
  for (const point of points)
    expect(
      guide.compareDocumentPosition(point) & window.Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy();
  const [outline, line] = guide.querySelectorAll("line");
  expect(Number(outline.getAttribute("stroke-width"))).toBeGreaterThan(
    Number(line.getAttribute("stroke-width")),
  );
  expect(line.getAttribute("stroke-opacity")).toBeNull();
  const marker = guide.querySelector("circle");
  expect(marker.getAttribute("cx")).toBe(line.getAttribute("x1"));
  expect(marker.getAttribute("cy")).toBe(line.getAttribute("y1"));
});
