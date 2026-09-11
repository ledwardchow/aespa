import { StrictMode } from "react";
import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { usePolling } from "./usePolling.js";
import { useIncrementalCollection } from "./useIncrementalCollection.js";

afterEach(() => vi.useRealTimers());

test("slow requests do not overlap and unmount cancels the active request", async () => {
  vi.useFakeTimers();
  let complete;
  const load = vi.fn(
    () =>
      new Promise((resolve) => {
        complete = resolve;
      }),
  );
  const { unmount } = renderHook(() => usePolling(load, { intervalMs: 100 }));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(500);
  });
  expect(load).toHaveBeenCalledTimes(1);
  await act(async () => {
    complete();
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(100);
  });
  expect(load).toHaveBeenCalledTimes(2);
  const signal = load.mock.calls[1][0];
  unmount();
  expect(signal.aborted).toBe(true);
  expect(vi.getTimerCount()).toBe(0);
});

test("StrictMode cleanup leaves only one live request and timer", () => {
  vi.useFakeTimers();
  const load = vi.fn(() => new Promise(() => {}));
  const wrapper = ({ children }) => <StrictMode>{children}</StrictMode>;
  const { unmount } = renderHook(() => usePolling(load, { intervalMs: 100 }), { wrapper });
  expect(load.mock.calls.filter(([signal]) => !signal.aborted)).toHaveLength(1);
  expect(vi.getTimerCount()).toBe(1);
  unmount();
  expect(load.mock.calls.every(([signal]) => signal.aborted)).toBe(true);
});

test("incremental collections ignore previous run responses and deduplicate each batch", async () => {
  let resolveOld;
  const oldLoad = vi.fn(
    () =>
      new Promise((resolve) => {
        resolveOld = resolve;
      }),
  );
  const newLoad = vi.fn().mockResolvedValue([{ id: 2 }, { id: 2 }, { id: 3 }]);
  const { result, rerender } = renderHook(
    ({ loader }) => useIncrementalCollection(loader, { enabled: false }),
    { initialProps: { loader: oldLoad } },
  );
  let pending;
  act(() => {
    pending = result.current.loadMore();
  });
  rerender({ loader: newLoad });
  await act(async () => {
    await result.current.loadMore();
  });
  await act(async () => {
    resolveOld([{ id: 1 }]);
    await pending;
  });
  expect(result.current.items).toEqual([{ id: 2 }, { id: 3 }]);
  expect(result.current.cursorRef.current).toBe(3);
  await act(async () => {
    await result.current.loadMore();
  });
  expect(newLoad.mock.calls[1][0]).toBe(3);
  expect(result.current.items).toHaveLength(2);
});
