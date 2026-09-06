import { afterEach, expect, test, vi } from "vitest";
import { recoverFromPreloadError, registerServiceWorker } from "./registerServiceWorker";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

test("Vite development never registers a caching worker", () => {
  vi.stubEnv("PROD", false);
  const register = vi.fn();
  Object.defineProperty(navigator, "serviceWorker", { value: { register }, configurable: true });
  registerServiceWorker();
  window.dispatchEvent(new Event("load"));
  expect(register).not.toHaveBeenCalled();
});

test("production registers the existing worker after the document loads", () => {
  vi.stubEnv("PROD", true);
  const register = vi.fn().mockResolvedValue({});
  Object.defineProperty(navigator, "serviceWorker", { value: { register }, configurable: true });
  registerServiceWorker();
  window.dispatchEvent(new Event("load"));
  expect(register).toHaveBeenCalledWith("/sw.js");
});

test("a failed lazy route reloads once to pick up the current entry script", () => {
  const storage = new Map<string, string>();
  const sessionStorage = {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
  } as Storage;
  const reload = vi.fn();
  const firstEvent = new Event("vite:preloadError", { cancelable: true });

  recoverFromPreloadError(firstEvent, { storage: sessionStorage, reload });
  recoverFromPreloadError(new Event("vite:preloadError", { cancelable: true }), {
    storage: sessionStorage,
    reload,
  });

  expect(firstEvent.defaultPrevented).toBe(true);
  expect(reload).toHaveBeenCalledTimes(1);
});
