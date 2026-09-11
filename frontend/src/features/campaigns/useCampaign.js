import * as applicationsApi from "../../shared/api/applications.js";
import { useState, useEffect, useCallback, useRef } from "react";

import { usePolling } from "../../shared/hooks/usePolling.js";
import { campaignDisplayStatus } from "../../shared/runs/campaignPresentation.js";

const ACTIVE_STAGES = new Set(["sast_running", "correlating", "dast_running"]);

// Loads the campaign, keeps it fresh while a stage is active, and exposes the
// start/stop/retry/continue actions the header and tabs need. Kept separate
// from any one tab's own state so every tab can share one source of truth
// without re-fetching independently.
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
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const load = useCallback(async () => {
    try {
      const c = await applicationsApi.getCampaign(applicationId, campaignId);
      if (mountedRef.current) {
        setCampaign(c);
        setError(null);
      }
    } catch (e) {
      if (mountedRef.current) setError(e.message);
    }
  }, [applicationId, campaignId]);

  const displayedStatus = campaignDisplayStatus(campaign);
  usePolling(load, {
    // A child scan can resume its parent campaign from another page. Keep
    // polling paused and terminal snapshots too, otherwise this screen can
    // remain stuck on "interrupted" after the backend advances to correlation.
    enabled: true,
    intervalMs: 4000,
  });

  const runAction = useCallback(
    async (action, confirmMsg) => {
      if (confirmMsg && !confirm(confirmMsg)) return;
      setBusy(true);
      setError(null);
      try {
        const updated = await action();
        if (
          mountedRef.current &&
          updated?.application_id != null &&
          Array.isArray(updated?.source_members)
        ) {
          setCampaign(updated);
        }
        await load();
      } catch (e) {
        setError(e.message);
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  const start = useCallback(
    () => runAction(() => applicationsApi.startCampaign(applicationId, campaignId)),
    [runAction, applicationId, campaignId],
  );
  const stop = useCallback(
    () =>
      runAction(
        () => applicationsApi.stopCampaign(applicationId, campaignId),
        "Stop this campaign? All active child scans will be stopped.",
      ),
    [runAction, applicationId, campaignId],
  );
  const resume = useCallback(
    () => runAction(() => applicationsApi.resumeCampaign(applicationId, campaignId)),
    [runAction, applicationId, campaignId],
  );
  const resumeSource = useCallback(
    (memberId) =>
      runAction(() => applicationsApi.resumeCampaignSource(applicationId, campaignId, memberId)),
    [runAction, applicationId, campaignId],
  );
  const resumeTarget = useCallback(
    (memberId) =>
      runAction(() => applicationsApi.resumeCampaignTarget(applicationId, campaignId, memberId)),
    [runAction, applicationId, campaignId],
  );
  const rebuildConnections = useCallback(
    () => runAction(() => applicationsApi.rebuildCampaignConnections(applicationId, campaignId)),
    [runAction, applicationId, campaignId],
  );
  const continueToLive = useCallback(
    () => runAction(() => applicationsApi.continueCampaign(applicationId, campaignId)),
    [runAction, applicationId, campaignId],
  );

  return {
    campaign,
    error,
    setError,
    busy,
    load,
    start,
    stop,
    resume,
    resumeSource,
    resumeTarget,
    rebuildConnections,
    continueToLive,
    isActive: campaign
      ? ACTIVE_STAGES.has(campaign.status) || ACTIVE_STAGES.has(displayedStatus)
      : false,
  };
}
