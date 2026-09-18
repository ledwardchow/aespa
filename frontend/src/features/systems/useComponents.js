import * as systemsApi from "../../shared/api/systems.js";
import { useState, useCallback, useEffect } from "react";

// Loads/mutates an system's code components. Snapshot history for a
// given component is fetched lazily (only when its card is expanded) so
// opening the tab with many components stays cheap. `onChanged` (optional) is
// invoked after any mutation that changes the system's composition —
// SystemDetail uses it to keep its system data fresh without the
// tab having to be revisited first.
export function useComponents(systemId, onChanged) {
  const [components, setComponents] = useState(null);
  const [error, setError] = useState(null);
  const [snapshotsByComponent, setSnapshotsByComponent] = useState({});

  const load = useCallback(async () => {
    try {
      setComponents(await systemsApi.listSystemComponents(systemId));
    } catch (e) {
      setError(e.message);
    }
  }, [systemId]);

  useEffect(() => {
    load();
  }, [load]);

  const loadSnapshotHistory = useCallback(
    async (componentId) => {
      try {
        const snapshots = await systemsApi.listComponentSnapshots(systemId, componentId);
        setSnapshotsByComponent((prev) => ({ ...prev, [componentId]: snapshots }));
      } catch (e) {
        setError(e.message);
      }
    },
    [systemId],
  );

  const createComponent = useCallback(
    async (body) => {
      await systemsApi.createSystemComponent(systemId, body);
      await load();
      onChanged?.();
    },
    [systemId, load, onChanged],
  );

  const updateComponent = useCallback(
    async (componentId, body) => {
      await systemsApi.updateSystemComponent(systemId, componentId, body);
      await load();
      onChanged?.();
    },
    [systemId, load, onChanged],
  );

  const deleteComponent = useCallback(
    async (componentId) => {
      await systemsApi.deleteSystemComponent(systemId, componentId);
      await load();
      onChanged?.();
    },
    [systemId, load, onChanged],
  );

  const uploadSnapshot = useCallback(
    async (componentId, file) => {
      await systemsApi.uploadComponentSnapshot(systemId, componentId, file);
      await load();
      await loadSnapshotHistory(componentId);
      onChanged?.();
    },
    [systemId, load, loadSnapshotHistory, onChanged],
  );

  const deleteSnapshot = useCallback(
    async (componentId, snapshotId) => {
      await systemsApi.deleteComponentSnapshot(systemId, componentId, snapshotId);
      await load();
      await loadSnapshotHistory(componentId);
      onChanged?.();
    },
    [systemId, load, loadSnapshotHistory, onChanged],
  );

  return {
    components,
    error,
    setError,
    snapshotsByComponent,
    loadSnapshotHistory,
    createComponent,
    updateComponent,
    deleteComponent,
    uploadSnapshot,
    deleteSnapshot,
  };
}
