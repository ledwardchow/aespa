import * as apiCollectionsApi from "../../shared/api/apiCollections.js";
import * as applicationsApi from "../../shared/api/applications.js";
import * as sitesApi from "../../shared/api/sites.js";
import { useState, useCallback, useEffect } from "react";

// Attached Sites/API Collections for an application, plus the catalog of
// existing Sites/API Collections available to attach. `onChanged` (optional)
// is invoked after attach/detach — see useComponents for why.
export function useTargets(applicationId, onChanged) {
  const [targets, setTargets] = useState(null);
  const [allSites, setAllSites] = useState([]);
  const [allApiCollections, setAllApiCollections] = useState([]);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [t, sites, apis] = await Promise.all([
        applicationsApi.listAppTargets(applicationId),
        sitesApi.listSites(),
        apiCollectionsApi.listApiCollections(),
      ]);
      setTargets(t);
      setAllSites(sites || []);
      setAllApiCollections(apis || []);
    } catch (e) {
      setError(e.message);
    }
  }, [applicationId]);

  useEffect(() => {
    load();
  }, [load]);

  const attach = useCallback(
    async (targetType, targetId) => {
      await applicationsApi.attachAppTarget(applicationId, {
        target_type: targetType,
        target_id: targetId,
      });
    },
    [applicationId],
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
      await applicationsApi.detachAppTarget(applicationId, targetId);
      await load();
      onChanged?.();
    },
    [applicationId, load, onChanged],
  );

  const setComponent = useCallback(
    async (targetId, componentId) => {
      await applicationsApi.updateAppTarget(applicationId, targetId, {
        component_id: componentId || null,
      });
      await load();
      onChanged?.();
    },
    [applicationId, load, onChanged],
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
