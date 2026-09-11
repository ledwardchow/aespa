import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { useEventStream } from "./useEventStream.js";

class FakeEventSource {
  static instances = [];
  constructor(url) {
    this.url = url;
    this.close = vi.fn();
    FakeEventSource.instances.push(this);
  }
}
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  FakeEventSource.instances = [];
});

test("handlers update without reconnecting and retry timers stop on unmount", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("EventSource", FakeEventSource);
  const first = vi.fn(),
    next = vi.fn();
  const { rerender, unmount } = renderHook(
    ({ onMessage }) => useEventStream("/events", { onMessage }),
    { initialProps: { onMessage: first } },
  );
  const source = FakeEventSource.instances[0];
  act(() => source.onmessage({ data: "one" }));
  rerender({ onMessage: next });
  act(() => source.onmessage({ data: "two" }));
  expect(first).toHaveBeenCalledTimes(1);
  expect(next).toHaveBeenCalledWith({ data: "two" });
  expect(FakeEventSource.instances).toHaveLength(1);
  act(() => source.onerror({}));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1000);
  });
  expect(FakeEventSource.instances).toHaveLength(2);
  act(() => FakeEventSource.instances[1].onerror({}));
  unmount();
  await vi.runAllTimersAsync();
  expect(FakeEventSource.instances).toHaveLength(2);
});

test("switching URLs closes the old subscription", () => {
  vi.stubGlobal("EventSource", FakeEventSource);
  const { rerender, unmount } = renderHook(({ url }) => useEventStream(url), {
    initialProps: { url: "/web/1/events" },
  });
  const old = FakeEventSource.instances[0];
  rerender({ url: "/api/1/events" });
  expect(old.close).toHaveBeenCalledTimes(1);
  expect(FakeEventSource.instances[1].url).toBe("/api/1/events");
  unmount();
  expect(FakeEventSource.instances[1].close).toHaveBeenCalledTimes(1);
});
