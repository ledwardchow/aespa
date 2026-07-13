import { WebRunSastLeadsTab } from "../SiteDetail/WebRunSastLeadsTab";


export function ApiRunLeadsTab({
  runId,
  scanRunning
}) {
  return <WebRunSastLeadsTab
    runId={runId}
    scanRunning={scanRunning}
    runKind="api"
  />;
}

// ── ApiRunSessionsTab ──────────────────────────────────────────────────────────

// ── ApiRunFindingsTab ──────────────────────────────────────────────────────────
