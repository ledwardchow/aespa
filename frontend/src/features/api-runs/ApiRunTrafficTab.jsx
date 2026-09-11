import * as apiRunsApi from "../../shared/api/apiRuns.js";
import { useState, useEffect, useRef, useCallback } from "react";

import { useIncrementalCollection } from "../../shared/hooks/useIncrementalCollection.js";
import { TrafficDetail, TrafficTable } from "../../shared/ui/TrafficView.jsx";
import { nav } from "../../shared/navigation/router.js";
import { runHref } from "../../shared/navigation/links.ts";

export function ApiRunTrafficTab({ runId, scanRunning, coverageFilter }) {
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const tableRef = useRef(null);
  const loadAfter = useCallback((cursor) => apiRunsApi.getApiTraffic(runId, cursor), [runId]);
  const { items: traffic, reset } = useIncrementalCollection(loadAfter, {
    enabled: true,
    intervalMs: 4000,
  });
  const refreshTotal = useCallback(
    () =>
      apiRunsApi
        .getApiTrafficCount(runId)
        .then((result) => setTotal(result.count || 0))
        .catch(() => {}),
    [runId],
  );
  useEffect(() => {
    refreshTotal();
  }, [refreshTotal, traffic.length]);
  useEffect(() => {
    if (autoScroll && tableRef.current) {
      tableRef.current.scrollTop = tableRef.current.scrollHeight;
    }
  }, [traffic.length, autoScroll]);
  let filtered = filter
    ? traffic.filter((entry) =>
        (entry.url + entry.method + (entry.status ?? "") + entry.source + (entry.purpose || ""))
          .toLowerCase()
          .includes(filter.toLowerCase()),
      )
    : traffic;
  if (coverageFilter?.cellIds?.length) {
    const cellIds = new Set(coverageFilter.cellIds);
    filtered = filtered.filter((entry) => cellIds.has(entry.coverage_cell_id));
  }
  return (
    <div className="traffic-panel">
      <div className="traffic-toolbar">
        <input
          className="traffic-filter"
          placeholder="Filter…"
          value={filter}
          onInput={(event) => setFilter(event.target.value)}
        />
        <span className="traffic-count-label">
          {filtered.length} shown{total > filtered.length ? ` of ${total}` : ""}
        </span>
        {coverageFilter?.cellIds?.length ? (
          <span className="traffic-coverage-filter">
            OWASP {coverageFilter.category || "cell"}
            <button
              className="btn ghost sm"
              aria-label="Clear OWASP traffic filter"
              onClick={() => nav(runHref({ runKind: "api", runId }, "traffic"))}
            >
              ✕
            </button>
          </span>
        ) : null}
        <label className="traffic-autoscroll">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(event) => setAutoScroll(event.target.checked)}
          />
          Auto-scroll
        </label>
        <button
          className="btn ghost sm"
          onClick={() => {
            reset();
            setSelected(null);
          }}
        >
          Clear
        </button>
      </div>
      <div className="traffic-table-wrap" ref={tableRef}>
        <TrafficTable
          entries={filtered}
          selected={selected}
          onSelect={setSelected}
          sequenceFor={(_, index) => index + 1}
        />
        {filtered.length === 0 && (
          <div className="subtle" style={{ padding: 24, textAlign: "center" }}>
            {scanRunning
              ? "Capturing traffic…"
              : "No traffic recorded yet. Start a scan to generate traffic."}
          </div>
        )}
      </div>
      <TrafficDetail entry={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

// Build the agent list from a raw agent-log API response, preserving task history.
