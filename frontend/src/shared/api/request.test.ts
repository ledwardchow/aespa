import { afterEach, expect, test, vi } from "vitest";
import { ApiError, importJson, req } from "./request";

afterEach(() => vi.unstubAllGlobals());

test("JSON requests preserve caller options and parse the response", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response('{"saved":true}'));
  vi.stubGlobal("fetch", fetch);
  const controller = new AbortController();
  expect(
    await req("/api/example", {
      method: "PATCH",
      body: { name: "Example" },
      signal: controller.signal,
    }),
  ).toEqual({ saved: true });
  const options = fetch.mock.calls[0][1];
  expect(options.method).toBe("PATCH");
  expect(options.body).toBe('{"name":"Example"}');
  expect(options.signal).toBe(controller.signal);
  expect(options.headers.get("Content-Type")).toBe("application/json");
});

test("multipart uploads let the browser set the boundary", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response("{}"));
  vi.stubGlobal("fetch", fetch);
  const data = new FormData();
  data.append("name", "Example");
  await req("/api/example", { method: "POST", body: data });
  expect(fetch.mock.calls[0][1].body).toBe(data);
  expect(fetch.mock.calls[0][1].headers.has("Content-Type")).toBe(false);
});

test("serialized imports are sent without double encoding", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response("{}"));
  vi.stubGlobal("fetch", fetch);
  await importJson("/api/import", '{"name":"Imported"}');
  expect(fetch.mock.calls[0][1].body).toBe('{"name":"Imported"}');
});

test.each([
  [204, "", null],
  [200, "", null],
  [200, '{"id":1}', { id: 1 }],
])("handles HTTP %s with body %s", async (status, body, result) => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body || null, { status })));
  expect(await req("/api/example")).toEqual(result);
});

test.each([
  [422, '{"detail":[{"loc":["body","name"],"msg":"Required"}]}', "body.name: Required"],
  [400, '{"detail":"Cannot save"}', "Cannot save"],
  [502, "<html>Proxy failed</html>", "502 Bad Gateway"],
])("preserves HTTP %s error details", async (status, body, message) => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(body, { status, statusText: status === 502 ? "Bad Gateway" : "" }),
      ),
  );
  await expect(req("/api/example")).rejects.toMatchObject({ name: "ApiError", status, message });
});

test("a successful malformed response has a useful error", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not JSON")));
  await expect(req("/api/example")).rejects.toThrow("invalid response");
});

test("network cancellation stays distinguishable from HTTP errors", async () => {
  const abort = new DOMException("Aborted", "AbortError");
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
  await expect(req("/api/example")).rejects.toBe(abort);
  expect(abort).not.toBeInstanceOf(ApiError);
});
