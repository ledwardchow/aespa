import { WebRunSastLeadsTab } from "../../shared/leads/RunLeadsTab.jsx";

export function ApiRunLeadsTab({ runId, scanRunning, initialLeadRef }) {
  return (
    <WebRunSastLeadsTab
      runId={runId}
      scanRunning={scanRunning}
      runKind="api"
      initialLeadRef={initialLeadRef}
    />
  );
}

// ── ApiRunSessionsTab ──────────────────────────────────────────────────────────

// ── ApiRunFindingsTab ──────────────────────────────────────────────────────────
