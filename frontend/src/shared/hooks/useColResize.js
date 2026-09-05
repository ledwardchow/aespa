import { useState, useCallback, useEffect, useRef } from "react";

export function useColResize(storageKey, defaults) {
  const [widths, setWidths] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
      if (
        Array.isArray(saved) &&
        saved.length === defaults.length &&
        saved.every((value) => value === null || (Number.isFinite(value) && value >= 36))
      )
        return saved;
    } catch {
      /* Use defaults when storage is unavailable or malformed. */
    }
    return defaults;
  });
  const cleanupRef = useRef(() => {});
  useEffect(() => () => cleanupRef.current(), []);
  const startResize = useCallback(
    (index, event) => {
      event.preventDefault();
      event.stopPropagation();
      cleanupRef.current();
      const startX = event.clientX;
      const cell = event.currentTarget.closest("th");
      const startWidth = widths[index] ?? (cell ? cell.offsetWidth : 100);
      let nextWidths = widths;
      const onMove = (move) => {
        nextWidths = [...widths];
        nextWidths[index] = Math.max(36, startWidth + move.clientX - startX);
        setWidths(nextWidths);
      };
      const cleanup = () => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      const onUp = () => {
        cleanup();
        try {
          localStorage.setItem(storageKey, JSON.stringify(nextWidths));
        } catch {
          /* Optional preference. */
        }
      };
      cleanupRef.current = cleanup;
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    },
    [storageKey, widths],
  );
  return [widths, startResize];
}
