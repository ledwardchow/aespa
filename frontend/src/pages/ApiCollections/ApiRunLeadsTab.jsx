import { useState, useCallback } from "react";
import { LeadsPanel } from "./LeadsPanel";
import { api } from "../../lib/api";
import { usePolling } from "../../hooks/usePolling";


export function ApiRunLeadsTab({
  runId,
  scanRunning
}) {
  const [leads, setLeads] = useState(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => {
    setLoading(true);
    api.getApiRunLeads(runId).then(d => {
      setLeads(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [runId]);
  usePolling(load, { enabled: scanRunning, intervalMs: 6000 });
  return <LeadsPanel leads={leads} loading={loading} scanRunning={scanRunning} exportName={`api-run-${runId}`} emptyMsg="No scan leads for this collection yet. Run a SAST scan first." />;
}

// ── ApiRunSessionsTab ──────────────────────────────────────────────────────────

// ── ApiRunFindingsTab ──────────────────────────────────────────────────────────
