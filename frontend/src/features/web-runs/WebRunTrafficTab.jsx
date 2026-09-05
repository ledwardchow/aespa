import * as webRunsApi from "../../shared/api/webRuns.js";
import { useCallback, useEffect, useMemo, useState, useRef } from "react";

import { usePolling } from "../../shared/hooks/usePolling.js";
import { useColResize } from "../../shared/hooks/useColResize.js";
import { TrafficDetail, TrafficTable } from "../../shared/ui/TrafficView.jsx";

function parseExcludedExtensions(value) {
  return new Set(
    value
      .split(",")
      .map((part) => part.trim().toLowerCase())
      .filter(Boolean)
      .map((part) => (part.startsWith(".") ? part : `.${part}`)),
  );
}

function extractUrlHostname(url) {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return "";
  }
}

function extractUrlExtension(url) {
  try {
    const pathname = new URL(url).pathname || "";
    const slash = pathname.lastIndexOf("/");
    const segment = slash >= 0 ? pathname.slice(slash + 1) : pathname;
    const dot = segment.lastIndexOf(".");
    if (dot <= 0 || dot === segment.length - 1) return "";
    return segment.slice(dot).toLowerCase();
  } catch {
    return "";
  }
}

export function WebRunTrafficTab({
  runId,
  graph,
  active,
  captureActive,
  runStatus,
  onTotalChange,
}) {
  const [traffic, setTraffic] = useState([]);
  const [trafficTotal, setTrafficTotal] = useState(0);
  const [selectedTraffic, setSelectedTraffic] = useState(null);
  const [trafficFilter, setTrafficFilter] = useState("");
  const [excludedExtensionsInput, setExcludedExtensionsInput] = useState(".js, .css");
  const [showInScopeOnly, setShowInScopeOnly] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const [trafficSort, setTrafficSort] = useState({
    field: "_seq",
    dir: "asc",
  });
  const trafficTableRef = useRef(null);
  const lastTrafficIdRef = useRef(0);
  const [trafficColW, startTrafficResize] = useColResize("colw:traffic:v2", [
    30,
    88,
    68,
    70,
    62,
    52,
    null,
    66,
  ]);

  const updateTotal = useCallback(
    (total) => {
      setTrafficTotal(total);
      onTotalChange(total);
    },
    [onTotalChange],
  );

  useEffect(() => {
    setTraffic([]);
    lastTrafficIdRef.current = 0;
    setSelectedTraffic(null);
    webRunsApi
      .getTrafficCount(runId)
      .then((result) => updateTotal(result.count || 0))
      .catch(() => {});
  }, [runId, updateTotal]);

  const pollTraffic = useCallback(async () => {
    try {
      const entries = await webRunsApi.getTraffic(runId, lastTrafficIdRef.current);
      if (entries.length > 0) {
        lastTrafficIdRef.current = entries[entries.length - 1].id;
        setTraffic((previous) => {
          const stamped = entries.map((entry, index) => ({
            ...entry,
            _seq: previous.length + index + 1,
          }));
          const next = [...previous, ...stamped];
          return next.length > 2000 ? next.slice(-2000) : next;
        });
      }
      if (active || entries.length > 0) {
        const result = await webRunsApi.getTrafficCount(runId);
        updateTotal(result.count || 0);
      }
    } catch {}
  }, [active, runId, updateTotal]);
  const pollingActive = active || captureActive;
  usePolling(pollTraffic, {
    enabled: pollingActive,
    immediate: pollingActive,
    intervalMs: 2000,
  });

  const excludedExtensions = useMemo(
    () => parseExcludedExtensions(excludedExtensionsInput),
    [excludedExtensionsInput],
  );
  const inScopeHosts = useMemo(() => {
    const hosts = new Set();
    for (const node of graph?.nodes || []) {
      if (node?.in_scope === false || !node?.url) continue;
      const host = extractUrlHostname(node.url);
      if (host) hosts.add(host);
    }
    return hosts;
  }, [graph]);

  // ── Traffic helpers ────────────────────────────────────────────────────────
  const filteredTraffic = (() => {
    let list = trafficFilter
      ? traffic.filter(
          (e) =>
            e.url.toLowerCase().includes(trafficFilter.toLowerCase()) ||
            (e.method || "").toLowerCase().includes(trafficFilter.toLowerCase()) ||
            String(e.status || "").includes(trafficFilter) ||
            (e.source || "").toLowerCase().includes(trafficFilter.toLowerCase()),
        )
      : traffic;
    if (excludedExtensions.size > 0) {
      list = list.filter((entry) => {
        const ext = extractUrlExtension(entry.url);
        return !ext || !excludedExtensions.has(ext);
      });
    }
    if (showInScopeOnly && inScopeHosts.size > 0) {
      list = list.filter((entry) => inScopeHosts.has(extractUrlHostname(entry.url)));
    }
    const { field, dir } = trafficSort;
    const mul = dir === "asc" ? 1 : -1;
    const numeric = new Set(["_seq", "status", "duration_ms", "id"]);
    list = [...list].sort((a, b) => {
      let av = a[field],
        bv = b[field];
      if (numeric.has(field)) {
        av = av ?? -1;
        bv = bv ?? -1;
        return (av - bv) * mul;
      }
      return String(av ?? "").localeCompare(String(bv ?? "")) * mul;
    });
    return list;
  })();
  const onTrafficSort = (field) =>
    setTrafficSort((prev) =>
      prev.field === field
        ? {
            field,
            dir: prev.dir === "asc" ? "desc" : "asc",
          }
        : {
            field,
            dir: "asc",
          },
    );
  return (
    <div className="traffic-panel" style={{ display: active ? undefined : "none" }}>
      <div className="traffic-toolbar">
        <input
          className="traffic-filter"
          type="text"
          placeholder="Filter by URL, method or status…"
          value={trafficFilter}
          onInput={(e) => setTrafficFilter(e.target.value)}
        />
        <span className="traffic-count-label">
          {filteredTraffic.length} shown
          {trafficTotal > filteredTraffic.length ? ` of ${trafficTotal}` : ""}
        </span>
        <label className="traffic-autoscroll">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
          />
          Auto-scroll
        </label>
        <button
          className="btn ghost sm"
          onClick={async () => {
            try {
              await webRunsApi.clearTraffic(runId);
            } catch {}
            setTraffic([]);
            lastTrafficIdRef.current = 0;
            setSelectedTraffic(null);
            updateTotal(0);
          }}
        >
          Clear
        </button>
      </div>
      <div className="traffic-filter-panel">
        <div className="traffic-filter-panel-title">Filter</div>
        <div className="traffic-filter-panel-controls">
          <label className="traffic-filter-ext">
            <span>Exclude extensions</span>
            <input
              className="traffic-filter"
              type="text"
              placeholder=".js, .css, .png"
              value={excludedExtensionsInput}
              onInput={(e) => setExcludedExtensionsInput(e.target.value)}
            />
          </label>
          <label className="traffic-scope-only">
            <input
              type="checkbox"
              checked={showInScopeOnly}
              onChange={(e) => setShowInScopeOnly(e.target.checked)}
            />
            Show in-scope traffic only
          </label>
        </div>
      </div>

      <div className="traffic-table-wrap" ref={trafficTableRef}>
        <TrafficTable
          entries={filteredTraffic}
          selected={selectedTraffic}
          onSelect={setSelectedTraffic}
          sequenceFor={(entry, index) => entry._seq ?? index + 1}
          sortable
          sort={trafficSort}
          onSort={onTrafficSort}
          widths={trafficColW}
          onResizeStart={startTrafficResize}
        />
        {filteredTraffic.length === 0 && (
          <div
            className="subtle"
            style={{
              padding: "24px",
              textAlign: "center",
            }}
          >
            {runStatus === "running" || captureActive
              ? "Capturing traffic…"
              : "No traffic recorded yet. Start a crawl or scan."}
          </div>
        )}
      </div>
      <TrafficDetail entry={selectedTraffic} onClose={() => setSelectedTraffic(null)} />
    </div>
  );
}
