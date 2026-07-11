import { useCallback, useEffect, useRef, useState } from "react";
import { usePolling } from "./usePolling";

/** Fetches records after a cursor, deduplicates them, and exposes reset/load controls. */
export function useIncrementalCollection(loadAfter, {
  enabled = true,
  intervalMs,
  getId = item => item.id,
  getCursor = item => item.id,
  maxItems = Infinity
} = {}) {
  const [items, setItems] = useState([]);
  const cursorRef = useRef(0);
  const loadMore = useCallback(async () => {
    const next = await loadAfter(cursorRef.current);
    if (!next?.length) return [];
    setItems(previous => {
      const known = new Set(previous.map(getId));
      const additions = next.filter(item => !known.has(getId(item)));
      const merged = [...previous, ...additions];
      const last = merged.at(-1);
      if (last) cursorRef.current = getCursor(last);
      return merged.length > maxItems ? merged.slice(-maxItems) : merged;
    });
    return next;
  }, [getCursor, getId, loadAfter, maxItems]);
  const reset = useCallback(() => {
    cursorRef.current = 0;
    setItems([]);
  }, []);
  useEffect(reset, [reset, loadAfter]);
  usePolling(loadMore, { enabled, intervalMs, immediate: enabled });
  return { items, setItems, loadMore, reset, cursorRef };
}
