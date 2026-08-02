import { useState, useCallback, useEffect } from "react";
import { api } from "../../lib/api";

// Optional "component X talks to target Y" connection hints — improve
// correlation confidence but are never required. `onChanged` (optional) is
// invoked after create/delete — see useComponents for why.
export function useHints(applicationId, onChanged) {
  const [hints, setHints] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setHints(await api.listAppHints(applicationId));
    } catch (e) {
      setError(e.message);
    }
  }, [applicationId]);

  useEffect(() => { load(); }, [load]);

  const create = useCallback(async body => {
    await api.createAppHint(applicationId, body);
    await load();
    onChanged?.();
  }, [applicationId, load, onChanged]);

  const remove = useCallback(async hintId => {
    await api.deleteAppHint(applicationId, hintId);
    await load();
    onChanged?.();
  }, [applicationId, load, onChanged]);

  return { hints, error, setError, create, remove };
}
