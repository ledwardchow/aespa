import { afterEach, expect, test, vi } from "vitest";
import { getSastSourceCosts } from "./sastSourceCosts";

afterEach(() => vi.unstubAllGlobals());

test("counts each SAST source once and keeps unavailable estimates separate", async () => {
  const signal = new AbortController().signal;
  const responses: Record<string, unknown> = {
    "/api/test-runs/10/leads": [
      { producer_run_type: "sast", producer_run_id: 2 },
      { producer_run_type: "sast", producer_run_id: 2 },
      { producer_run_type: "sast", producer_run_id: 3 },
      { producer_run_type: "sast", producer_run_id: 4 },
      { producer_run_type: "web", producer_run_id: 5 },
    ],
    "/api/sast-runs/2": { name: "Source analysis" },
    "/api/sast-runs/2/token-usage": {
      estimated_cost_available: true,
      estimated_total_cost_usd: 3.19,
      by_model: { model: { estimated_cost_available: true } },
    },
    "/api/sast-runs/3": { name: "Partially priced" },
    "/api/sast-runs/3/token-usage": {
      estimated_cost_available: true,
      estimated_total_cost_usd: 1,
      by_model: {
        priced: { estimated_cost_available: true },
        unknown: { estimated_cost_available: false },
      },
    },
  };
  const fetch = vi.fn(async (url: string) =>
    Object.hasOwn(responses, url)
      ? new Response(JSON.stringify(responses[url]))
      : new Response("Not found", { status: 404 }),
  );
  vi.stubGlobal("fetch", fetch);
  expect(await getSastSourceCosts(10, signal)).toEqual([
    { runId: 2, name: "Source analysis", cost: 3.19 },
    { runId: 3, name: "Partially priced", cost: null },
    { runId: 4, name: "SAST run #4", cost: null },
  ]);
  expect(fetch.mock.calls.filter(([url]) => url === "/api/sast-runs/2/token-usage")).toHaveLength(
    1,
  );
  expect(fetch.mock.calls).toHaveLength(7);
});

test("does not fetch SAST runs when no SAST leads are loaded", async () => {
  const fetch = vi.fn(async () => new Response("[]"));
  vi.stubGlobal("fetch", fetch);
  expect(await getSastSourceCosts(10, new AbortController().signal)).toEqual([]);
  expect(fetch).toHaveBeenCalledTimes(1);
});
