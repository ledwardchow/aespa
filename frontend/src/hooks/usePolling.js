import { useCallback, useEffect, useRef } from "react";

/**
 * Loads once when the callback identity changes, then polls while enabled.
 * Overlapping requests are skipped so a slow response cannot build up a queue.
 */
export function usePolling(callback, {
  enabled = true,
  intervalMs,
  immediate = true
  } = {}) {
  const inFlightRef = useRef(null);
  const poll = useCallback(async () => {
    if (inFlightRef.current === callback) return;
    inFlightRef.current = callback;
    try {
      await callback();
    } catch (error) {
      console.error("Polling callback failed", error);
    } finally {
      if (inFlightRef.current === callback) inFlightRef.current = null;
    }
  }, [callback]);

  useEffect(() => {
    if (!immediate) return;
    void poll();
  }, [immediate, poll]);

  useEffect(() => {
    if (!enabled || !intervalMs) return;

    const id = setInterval(poll, intervalMs);
    return () => clearInterval(id);
  }, [enabled, intervalMs, poll]);
}
