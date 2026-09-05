import { afterEach, expect, test, vi } from "vitest";
import { registerServiceWorker } from "./registerServiceWorker";

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
