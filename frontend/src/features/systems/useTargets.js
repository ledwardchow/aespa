import * as apiCollectionsApi from "../../shared/api/apiCollections.js";
import * as systemsApi from "../../shared/api/systems.js";
import * as sitesApi from "../../shared/api/sites.js";
import { useState, useCallback, useEffect } from "react";

// Attached Sites/API Collections for an system, plus the catalog of
// existing Sites/API Collections available to attach. `onChanged` (optional)
// is invoked after attach/detach — see useComponents for why.
export function useTargets(systemId, onChanged) {
  const [targets, setTargets] = useState(null);
  const [allSites, setAllSites] = useState([]);
  const [allApiCollections, setAllApiCollections] = useState([]);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [t, sites, apis] = await Promise.all([
        systemsApi.listSystemTargets(systemId),
        sitesApi.listSites(),
        apiCollectionsApi.listApiCollections(),
      ]);
      setTargets(t);
      setAllSites(sites || []);
      setAllApiCollections(apis || []);
    } catch (e) {
      setError(e.message);
    }
  }, [systemId]);

  useEffect(() => {
    load();
  }, [load]);

  const attach = useCallback(
    async (targetType, targetId) => {
      await systemsApi.attachSystemTarget(systemId, {
        target_type: targetType,
        target_id: targetId,
      });
    },
    [systemId],
  );

  const attachMany = useCallback(
    async (items) => {
      for (const { targetType, targetId } of items) {
        await attach(targetType, targetId);
      }
      await load();
      onChanged?.();
    },
    [attach, load, onChanged],
  );

  const detach = useCallback(
    async (targetId) => {
      await systemsApi.detachSystemTarget(systemId, targetId);
      await load();
      onChanged?.();
    },
    [systemId, load, onChanged],
  );

  const setComponent = useCallback(
    async (targetId, componentId) => {
      await systemsApi.updateSystemTarget(systemId, targetId, {
        component_id: componentId || null,
      });
      await load();
      onChanged?.();
    },
    [systemId, load, onChanged],
  );

  return {
    targets,
    allSites,
    allApiCollections,
    error,
    setError,
    attachMany,
    detach,
    setComponent,
    reload: load,
  };
}
