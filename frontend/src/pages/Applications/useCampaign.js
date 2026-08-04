import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../../lib/api";
import { usePolling } from "../../hooks/usePolling";

const ACTIVE_STAGES = new Set(["sast_running", "correlating", "dast_running"]);

// Loads the campaign, keeps it fresh while a stage is active, and exposes the
// start/stop/retry/continue actions the header and Overview tab need. Kept
// separate from any one tab's own state so every tab can share one source of
// truth without re-fetching independently.
export function useCampaign(applicationId, campaignId) {
  const [campaign, setCampaign] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const mountedRef = useRef(true);
  // StrictMode-safe: the setup (not just cleanup) must run on every effect
  // invocation. In React StrictMode's dev-only mount→cleanup→remount replay,
  // the cleanup sets this false; without resetting it back to true here on
  // the following real mount, every subsequent load() would see a
  // permanently-false mountedRef and silently stop applying state updates.
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const load = useCallback(async () => {
    try {
      const c = await api.getCampaign(applicationId, campaignId);
      if (mountedRef.current) setCampaign(c);
    } catch (e) {
      if (mountedRef.current) setError(e.message);
    }
  }, [applicationId, campaignId]);

  const hasRunningMember = campaign
    ? [...(campaign.source_members || []), ...(campaign.target_members || [])]
        .some(member => member.status === "running")
    : false;
  usePolling(load, { enabled: campaign ? ACTIVE_STAGES.has(campaign.status) || hasRunningMember : true, intervalMs: 4000 });

  const runAction = useCallback(async (action, confirmMsg) => {
    if (confirmMsg && !confirm(confirmMsg)) return;
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }, [load]);

  const start = useCallback(() => runAction(() => api.startCampaign(applicationId, campaignId)), [runAction, applicationId, campaignId]);
  const stop = useCallback(() => runAction(() => api.stopCampaign(applicationId, campaignId), "Stop this campaign? All active child scans will be stopped."), [runAction, applicationId, campaignId]);
  const retry = useCallback(() => runAction(() => api.retryCampaign(applicationId, campaignId)), [runAction, applicationId, campaignId]);
  const resumeSource = useCallback((memberId) => runAction(() => api.resumeCampaignSource(applicationId, campaignId, memberId)), [runAction, applicationId, campaignId]);
  const resumeTarget = useCallback((memberId) => runAction(() => api.resumeCampaignTarget(applicationId, campaignId, memberId)), [runAction, applicationId, campaignId]);
  const continueToLive = useCallback(() => runAction(() => api.continueCampaign(applicationId, campaignId)), [runAction, applicationId, campaignId]);

  return { campaign, error, setError, busy, load, start, stop, retry, resumeSource, resumeTarget, continueToLive, isActive: campaign ? ACTIVE_STAGES.has(campaign.status) : false };
}
