import { afterEach, expect, test, vi } from "vitest";
import { getFindings, updateFinding } from "./findings.ts";
afterEach(() => vi.unstubAllGlobals());
test("web and API findings with matching IDs use separate URLs and preserve the abort signal", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response("[]", { status: 200 }));
  vi.stubGlobal("fetch", fetch);
  const abort = new AbortController();
  await getFindings({ runKind: "web", runId: 1 }, abort.signal);
  expect(fetch.mock.calls[0]).toEqual([
    "/api/test-runs/1/findings",
    expect.objectContaining({ signal: abort.signal }),
  ]);
  fetch.mockResolvedValueOnce(new Response("[]"));
  await getFindings({ runKind: "api", runId: 1 });
  expect(fetch.mock.calls[1][0]).toBe("/api/api-test-runs/1/findings");
  fetch.mockResolvedValueOnce(new Response("{}"));
  await updateFinding({ runKind: "api", runId: 1 }, 7, { title: "Changed", cvss_score: null });
  expect(fetch.mock.calls[2]).toEqual([
    "/api/api-test-runs/1/findings/7",
    expect.objectContaining({ method: "PATCH", body: '{"title":"Changed","cvss_score":null}' }),
  ]);
});
