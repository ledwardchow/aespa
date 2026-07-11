import { useEffect, useRef } from "react";

/**
 * Visibility-aware EventSource with explicit exponential reconnects.
 * Handlers are held in refs so callers can pass inline callbacks safely.
 */
export function useEventStream(url, handlers = {}, {
  enabled = true,
  initialRetryMs = 1000,
  maxRetryMs = 30000
} = {}) {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    if (!enabled || !url || typeof EventSource === "undefined") return;
    let source = null;
    let retryTimer = null;
    let retryMs = initialRetryMs;
    let disposed = false;

    const close = () => {
      if (source) source.close();
      source = null;
    };
    const connect = () => {
      if (disposed || (typeof document !== "undefined" && document.hidden)) return;
      close();
      source = new EventSource(url);
      source.onopen = event => {
        retryMs = initialRetryMs;
        handlersRef.current.onOpen?.(event);
      };
      source.onmessage = event => handlersRef.current.onMessage?.(event);
      source.onerror = event => {
        handlersRef.current.onError?.(event);
        close();
        if (disposed) return;
        retryTimer = setTimeout(() => {
          retryTimer = null;
          connect();
        }, retryMs);
        retryMs = Math.min(maxRetryMs, retryMs * 2);
      };
    };
    const onVisibilityChange = () => {
      if (document.hidden) {
        if (retryTimer) clearTimeout(retryTimer);
        retryTimer = null;
        close();
      } else {
        retryMs = initialRetryMs;
        connect();
      }
    };
    connect();
    if (typeof document !== "undefined") document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      close();
      if (typeof document !== "undefined") document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [enabled, initialRetryMs, maxRetryMs, url]);
}
