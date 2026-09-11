import { useCallback, useEffect, useRef } from "react";

/** Loads immediately when requested and skips overlapping ticks for the same loader. */
export function usePolling(callback, { enabled = true, intervalMs, immediate = true } = {}) {
  const activeRef = useRef(null);
  const poll = useCallback(async () => {
    if (activeRef.current?.callback === callback) return;
    const request = { callback, controller: new AbortController() };
    activeRef.current = request;
    try {
      await callback(request.controller.signal);
    } catch (error) {
      if (!request.controller.signal.aborted) console.error("Polling callback failed", error);
    } finally {
      if (activeRef.current === request) activeRef.current = null;
    }
  }, [callback]);

  useEffect(() => {
    if (immediate) void poll();
    const timer = enabled && intervalMs ? setInterval(poll, intervalMs) : null;
    return () => {
      if (timer !== null) clearInterval(timer);
      if (activeRef.current?.callback === callback) {
        activeRef.current.controller.abort();
        activeRef.current = null;
      }
    };
  }, [callback, enabled, immediate, intervalMs, poll]);
}
