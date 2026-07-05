import { useState, useCallback } from "react";

// Shared helpers/constants for the SiteDetail page and its tab/panel components.

const SCOPE_IN_COLOR = "#3b82f6";
const SCOPE_OUT_COLOR = "#ef4444";
export const scopeColor = d => d.in_scope === false ? SCOPE_OUT_COLOR : SCOPE_IN_COLOR;
const DYNAMIC_SCAN_ACTIVE_STATUSES = ["running", "analysing", "stopping"];
export const isDynamicScanActive = status => DYNAMIC_SCAN_ACTIVE_STATUSES.includes(status);

// Per-user palette (index into credentials array)
const USER_PALETTE = ["#f97316", "#06b6d4", "#a855f7", "#f59e0b", "#10b981", "#ec4899"];
const USER_BOTH_COLOR = "#6366f1"; // accessible to all users
const USER_NONE_COLOR = "#6b7691"; // not tagged (pre-multi-user crawl)
export const userColor = (d, credentials) => {
  const ab = d.accessible_by || [];
  if (!credentials || credentials.length === 0 || ab.length === 0) return USER_NONE_COLOR;
  if (ab.length >= credentials.length) return USER_BOTH_COLOR;
  const idx = credentials.findIndex(c => ab.includes(c.id));
  return idx >= 0 ? USER_PALETTE[idx % USER_PALETTE.length] : USER_NONE_COLOR;
};
export function runWorkflowStatus(run, opts = {}) {
  if (!run) return {
    key: "pending",
    label: "pending"
  };
  const thinkingStatus = opts.thinkingStatus || run.thinking_status || "idle";
  if (opts.crawlStopping) return {
    key: "stopping",
    label: "stopping crawl"
  };
  if (opts.thinkingStopping || thinkingStatus === "stopping") return {
    key: "stopping",
    label: "stopping Dynamic Scan"
  };
  if (run.status === "running") return {
    key: "running",
    label: "crawling"
  };
  if (run.status === "failed") return {
    key: "danger",
    label: "crawl failed"
  };
  if (thinkingStatus === "running") return {
    key: "running",
    label: "Dynamic Scan"
  };
  if (thinkingStatus === "analysing") return {
    key: "running",
    label: "analysing Dynamic Scan"
  };
  if (thinkingStatus === "failed") return {
    key: "danger",
    label: "Dynamic Scan failed"
  };
  if (run.status === "stopped") return {
    key: "neutral",
    label: "crawl stopped"
  };
  if (thinkingStatus === "stopped") return {
    key: "neutral",
    label: "Dynamic Scan stopped"
  };
  if (thinkingStatus === "complete") return {
    key: "ok",
    label: "Dynamic Scan complete"
  };
  if (run.status === "complete") return {
    key: "ok",
    label: "complete"
  };
  return {
    key: "neutral",
    label: run.status || "pending"
  };
}
export const workflowBadge = (run, opts = {}) => {
  const st = runWorkflowStatus(run, opts);
  return <span className={"badge " + st.key}>{st.label}</span>;
};

// ── Column resize hook ────────────────────────────────────────────────────────
export function useColResize(storageKey, defaults) {
  const [widths, setWidths] = useState(() => {
    try {
      const s = localStorage.getItem(storageKey);
      if (s) return JSON.parse(s);
    } catch  {}
    return defaults;
  });
  const startResize = useCallback((idx, e) => {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX;
    const th = e.currentTarget.closest("th");
    const startW = widths[idx] ?? (th ? th.offsetWidth : 100);
    const onMove = ev => {
      const newW = Math.max(36, startW + ev.clientX - startX);
      setWidths(prev => {
        const n = [...prev];
        n[idx] = newW;
        return n;
      });
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      setWidths(prev => {
        try {
          localStorage.setItem(storageKey, JSON.stringify(prev));
        } catch  {}
        return prev;
      });
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [storageKey, widths]);
  return [widths, startResize];
}
