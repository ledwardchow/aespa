import { afterEach, beforeEach, expect, test, vi } from "vitest";

beforeEach(() => {
  vi.resetModules();
  window.history.replaceState(null, "", "/#/settings/authentication");
});
afterEach(() => vi.unstubAllGlobals());

test("remembers the cookie session without storing the authentication key", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify({ authenticated: true, csrf_token: "csrf" })));
  vi.stubGlobal("fetch", fetch);
  const session = await import("./session.ts");
  await session.initializeAuth();
  expect(session.getAuthState()).toEqual({ status: "signed-in", csrfToken: "csrf" });
  expect(fetch).toHaveBeenCalledWith(
    "/api/auth/session",
    expect.objectContaining({ credentials: "same-origin", cache: "no-store" }),
  );
  expect(window.location.hash).toBe("#/settings/authentication");
  expect(localStorage.getItem("authentication-key")).toBeNull();
});

test("consumes a launcher secret once and removes it before the first request", async () => {
  window.history.replaceState(
    null,
    "",
    "/#aespa-login=ticket&next=%23%2Fsettings%2Fauthentication",
  );
  const fetch = vi.fn().mockImplementation(async (url) => {
    expect(window.location.hash).toBe("#/settings/authentication");
    return new Response(
      JSON.stringify(
        url.endsWith("exchange")
          ? { authenticated: true, csrf_token: "csrf" }
          : { authenticated: false },
      ),
    );
  });
  vi.stubGlobal("fetch", fetch);
  const session = await import("./session.ts");
  await Promise.all([session.initializeAuth(), session.initializeAuth()]);
  expect(fetch.mock.calls.filter(([url]) => url.endsWith("exchange"))).toHaveLength(1);
  expect(fetch).toHaveBeenCalledWith(
    "/api/auth/exchange",
    expect.objectContaining({ body: JSON.stringify({ token: "ticket" }) }),
  );
});

test("a launcher link cannot redirect to an external page", async () => {
  window.history.replaceState(null, "", "/#aespa-login=ticket&next=https%3A%2F%2Fexample.org");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async () => new Response('{"authenticated":false}')),
  );
  const session = await import("./session.ts");
  await session.initializeAuth();
  expect(window.location.hash).toBe("#/");
});

test("adds CSRF to management writes and extension administration only", async () => {
  const fetch = vi
    .fn()
    .mockImplementation(async () => new Response('{"authenticated":true,"csrf_token":"csrf"}'));
  vi.stubGlobal("fetch", fetch);
  const session = await import("./session.ts");
  await session.initializeAuth();
  const restore = session.installAuthFetch();
  try {
    await window.fetch("/api/sites", { method: "POST" });
    await window.fetch("/extension/aespa.api/admin/tokens", { method: "POST" });
    await window.fetch("/extension/aespa.api/v1/scans", {
      method: "POST",
      headers: { Authorization: "Bearer integration" },
    });
    await window.fetch("https://example.org/api/sites", { method: "POST" });
    expect(fetch.mock.calls[1][1].headers.get("X-AESPA-CSRF")).toBe("csrf");
    expect(fetch.mock.calls[2][1].headers.get("X-AESPA-CSRF")).toBe("csrf");
    expect(fetch.mock.calls[3][1].headers).toEqual({ Authorization: "Bearer integration" });
    expect(fetch.mock.calls[4][1].headers).toBeUndefined();
  } finally {
    restore();
  }
});

test("an expired management session returns to sign-in while integration failures do not", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(new Response('{"authenticated":true,"csrf_token":"csrf"}'))
    .mockImplementation(async () => new Response("", { status: 401 }));
  vi.stubGlobal("fetch", fetch);
  const session = await import("./session.ts");
  await session.initializeAuth();
  const restore = session.installAuthFetch();
  try {
    await window.fetch("/extension/aespa.api/v1/scans");
    expect(session.getAuthState().status).toBe("signed-in");
    await window.fetch("/api/sites");
    expect(session.getAuthState().status).toBe("signed-out");
    expect(window.location.hash).toBe("#/settings/authentication");
  } finally {
    restore();
  }
});
