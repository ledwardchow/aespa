import * as systemsApi from "../../shared/api/systems.js";
import { useState, useCallback, useEffect } from "react";

// Optional code-to-target routing associations — improve correlation
// confidence but are never required. `onChanged` (optional) is
// invoked after create/delete — see useComponents for why.
export function useHints(systemId, onChanged) {
  const [hints, setHints] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setHints(await systemsApi.listSystemHints(systemId));
    } catch (e) {
      setError(e.message);
    }
  }, [systemId]);

  useEffect(() => {
    load();
  }, [load]);

  const create = useCallback(
    async (body) => {
      await systemsApi.createSystemHint(systemId, body);
      await load();
      onChanged?.();
    },
    [systemId, load, onChanged],
  );

  const remove = useCallback(
    async (hintId) => {
      await systemsApi.deleteSystemHint(systemId, hintId);
      await load();
      onChanged?.();
    },
    [systemId, load, onChanged],
  );

  return { hints, error, setError, create, remove };
}
