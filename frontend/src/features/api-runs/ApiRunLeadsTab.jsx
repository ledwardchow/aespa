import { WebRunSastLeadsTab } from "../../shared/leads/RunLeadsTab.jsx";

export function ApiRunLeadsTab({ runId, scanRunning }) {
  return <WebRunSastLeadsTab runId={runId} scanRunning={scanRunning} runKind="api" />;
}

// ── ApiRunSessionsTab ──────────────────────────────────────────────────────────

// ── ApiRunFindingsTab ──────────────────────────────────────────────────────────
