import * as systemsApi from "../../shared/api/systems.js";
import * as settingsApi from "../../shared/api/settings.js";
import { useState, useEffect, useCallback } from "react";

// Loads everything the guided campaign wizard needs: components (with every
// saved snapshot, not just the latest), attached targets, and LLM profiles.
export function useCampaignWizardData(systemId) {
  const [components, setComponents] = useState(null);
  const [snapshotsByComponent, setSnapshotsByComponent] = useState({});
  const [targets, setTargets] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [comps, tgts, profs] = await Promise.all([
        systemsApi.listSystemComponents(systemId),
        systemsApi.listSystemTargets(systemId),
        settingsApi.listLLMProfiles().catch(() => []),
      ]);
      setComponents(comps);
      setTargets(tgts);
      setProfiles(profs || []);
      const withSnapshots = comps.filter((c) => c.snapshot_count > 0);
      const histories = await Promise.all(
        withSnapshots.map((c) => systemsApi.listComponentSnapshots(systemId, c.id).catch(() => [])),
      );
      const map = {};
      withSnapshots.forEach((c, i) => {
        map[c.id] = histories[i];
      });
      setSnapshotsByComponent(map);
    } catch (e) {
      setError(e.message);
    }
  }, [systemId]);

  useEffect(() => {
    load();
  }, [load]);

  return { components, snapshotsByComponent, targets, profiles, error, setError };
}
