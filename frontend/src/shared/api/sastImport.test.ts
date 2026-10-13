import { afterEach, expect, test, vi } from "vitest";
import { searchSastImportSources } from "./sastImport.ts";

afterEach(() => vi.unstubAllGlobals());

test("uses server pages and keeps API run identity in the URL", async () => {
  const data = { items: [], total: 0, page: 2, page_size: 10 };
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(data)));
  vi.stubGlobal("fetch", fetch);
  expect(
    await searchSastImportSources("api", 4, "source.zip", 2, new AbortController().signal),
  ).toEqual(data);
  expect(fetch.mock.calls[0][0]).toBe(
    "/api/api-test-runs/4/sast-runs/available?q=source.zip&page=2&page_size=10",
  );
});

test("supports a running older backend without claiming exact import counts", async () => {
  const data = Array.from({ length: 23 }, (_, id) => ({
    id: id + 1,
    name: "Portal",
    source_filename: "source.zip",
    leads_count: 4,
  }));
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(data)))),
  );
  const result = await searchSastImportSources("web", 1, "SOURCE", 3, new AbortController().signal);
  expect(result.total).toBe(23);
  expect(result.items).toHaveLength(3);
  expect(result.items[0].new_count).toBeUndefined();
  const byId = await searchSastImportSources("web", 1, "12", 1, new AbortController().signal);
  expect(byId.items.map((scan) => scan.id)).toEqual([12]);
});

test("file previews and imports use multipart data and explicit preview state", async () => {
  const { importLeadReport } = await import("./sastImport.ts");
  const fetch = vi
    .fn()
    .mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ imported: 1 }))));
  vi.stubGlobal("fetch", fetch);
  const file = new File(["## Finding\n- Severity: high"], "report.md");
  await importLeadReport("api", 3, file, true);
  await importLeadReport("api", 3, file, false);
  expect(fetch.mock.calls[0][0]).toBe("/api/api-test-runs/3/import-report");
  expect(fetch.mock.calls[0][1].body.get("preview")).toBe("true");
  expect(fetch.mock.calls[1][1].body.get("preview")).toBe("false");
  expect(fetch.mock.calls[0][1].body.get("file").name).toBe("report.md");
  expect(fetch.mock.calls[0][1].headers.has("Content-Type")).toBe(false);
});
