import { useCallback, useEffect, useRef, useState } from "react";
import { usePolling } from "./usePolling.js";

const recordId = (item) => item.id;

/** A cursor belongs to one loader; late responses from an old loader are discarded. */
export function useIncrementalCollection(
  loadAfter,
  { enabled = true, intervalMs, getId = recordId, getCursor = recordId, maxItems = Infinity } = {},
) {
  const [items, setItems] = useState([]);
  const cursorRef = useRef(0);
  const generationRef = useRef(0);
  const reset = useCallback(() => {
    generationRef.current += 1;
    cursorRef.current = 0;
    setItems([]);
  }, []);
  useEffect(() => {
    reset();
    return () => {
      generationRef.current += 1;
    };
  }, [reset, loadAfter]);

  const loadMore = useCallback(
    async (signal) => {
      const generation = generationRef.current;
      const next = await loadAfter(cursorRef.current, signal);
      if (signal?.aborted || generation !== generationRef.current || !next?.length) return [];
      // Advance outside a React state updater, which may be called twice in StrictMode.
      cursorRef.current = getCursor(next.at(-1));
      setItems((previous) => {
        const known = new Set(previous.map(getId));
        const additions = next.filter((item) => {
          const id = getId(item);
          if (known.has(id)) return false;
          known.add(id);
          return true;
        });
        const merged = [...previous, ...additions];
        return merged.length > maxItems ? merged.slice(-maxItems) : merged;
      });
      return next;
    },
    [getCursor, getId, loadAfter, maxItems],
  );
  usePolling(loadMore, { enabled, intervalMs, immediate: enabled });
  return { items, setItems, loadMore, reset, cursorRef };
}
