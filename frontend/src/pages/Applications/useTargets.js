import { useState, useCallback, useEffect } from "react";
import { api } from "../../lib/api";

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
        api.listAppTargets(applicationId),
        api.listSites(),
        api.listApiCollections()
      ]);
      setTargets(t);
      setAllSites(sites || []);
      setAllApiCollections(apis || []);
    } catch (e) {
      setError(e.message);
    }
  }, [applicationId]);

  useEffect(() => { load(); }, [load]);

  const attach = useCallback(async (targetType, targetId) => {
    await api.attachAppTarget(applicationId, { target_type: targetType, target_id: targetId });
  }, [applicationId]);

  const attachMany = useCallback(async items => {
    for (const { targetType, targetId } of items) {
      await attach(targetType, targetId);
    }
    await load();
    onChanged?.();
  }, [attach, load, onChanged]);

  const detach = useCallback(async targetId => {
    await api.detachAppTarget(applicationId, targetId);
    await load();
    onChanged?.();
  }, [applicationId, load, onChanged]);

  return { targets, allSites, allApiCollections, error, setError, attachMany, detach, reload: load };
}
