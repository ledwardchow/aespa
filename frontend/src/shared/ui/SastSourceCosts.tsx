import { useCallback, useState } from "react";
import { getSastSourceCosts, type SastSourceCost } from "../api/sastSourceCosts";
import { usePolling } from "../hooks/usePolling.js";
import { fmtUsd } from "./TokenUsageBar.jsx";

export function SastSourceCosts({ runId }: { runId: number }) {
  const [loaded, setLoaded] = useState<{
    runId: number;
    sources: SastSourceCost[];
    failed: boolean;
  } | null>(null);
  const load = useCallback(
    async (signal: AbortSignal) => {
      try {
        const sources = await getSastSourceCosts(runId, signal);
        if (!signal.aborted) setLoaded({ runId, sources, failed: false });
      } catch {
        if (!signal.aborted) setLoaded({ runId, sources: [], failed: true });
      }
    },
    [runId],
  );
  usePolling(load, { intervalMs: 10_000 });
  if (loaded?.runId !== runId) return null;
  if (loaded.failed) return <div className="activity-token-bar">Could not load SAST costs</div>;
  return loaded.sources.map((source) => (
    <div
      className="activity-token-bar"
      key={source.runId}
      title="Full cost of the SAST run that supplied leads. Excluded from this DAST run's totals."
    >
      <span className="token-bar-label">SAST cost</span>
      <span className="token-model-name">{source.name}</span>
      <span className="token-bar-cost">
        {source.cost === null ? "Cost unavailable" : `≈${fmtUsd(source.cost)} est. cost`}
      </span>
      <span className="token-bar-empty">Separate from this run</span>
    </div>
  ));
}
