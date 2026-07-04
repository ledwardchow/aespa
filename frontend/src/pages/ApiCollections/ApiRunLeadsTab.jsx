import { useState, useEffect, useCallback, useContext } from "react";
import { LeadsPanel } from "./LeadsPanel";
import { api, formatError } from "../../lib/api";
import { SCAN_MODE_OPTIONS, SCAN_MODE_DEFINITIONS, ScanModeDefinitions, scanModeLabel, csv, defaultPolicyForm, policyToForm, policyPayload } from "../../lib/policy";
import { aliceSessionSubscribe, _aliceFlushRecovery } from "../../lib/aliceSession";
import { IconSites, IconApis, IconSettings, IconPlus, IconCheck, IconPlay, IconStop, IconShield, IconChevronLeft, IconChevronRight, IconBug, IconMessageSquare, IconSend, IconBrain } from "../../components/Icons";


export function ApiRunLeadsTab({
  runId,
  scanRunning
}) {
  const [leads, setLeads] = useState(null);
  const [loading, setLoading] = useState(true);
  const load = () => {
    setLoading(true);
    api.getApiRunLeads(runId).then(d => {
      setLeads(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  };
  useEffect(() => {
    load();
  }, [runId, load]);
  useEffect(() => {
    if (!scanRunning) return;
    const t = setInterval(load, 6000);
    return () => clearInterval(t);
  }, [
	scanRunning,
	runId,
	load
]);
  return <LeadsPanel leads={leads} loading={loading} scanRunning={scanRunning} exportName={`api-run-${runId}`} emptyMsg="No scan leads for this collection yet. Run a SAST scan first." />;
}

// ── ApiRunSessionsTab ──────────────────────────────────────────────────────────

// ── ApiRunFindingsTab ──────────────────────────────────────────────────────────

