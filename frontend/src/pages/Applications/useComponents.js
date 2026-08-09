import { useState, useCallback, useEffect } from "react";
import { api } from "../../lib/api";

// Loads/mutates an application's code components. Snapshot history for a
// given component is fetched lazily (only when its card is expanded) so
// opening the tab with many components stays cheap. `onChanged` (optional) is
// invoked after any mutation that changes the application's composition —
// ApplicationDetail uses it to keep its application data fresh without the
// tab having to be revisited first.
export function useComponents(applicationId, onChanged) {
  const [components, setComponents] = useState(null);
  const [error, setError] = useState(null);
  const [snapshotsByComponent, setSnapshotsByComponent] = useState({});

  const load = useCallback(async () => {
    try {
      setComponents(await api.listAppComponents(applicationId));
    } catch (e) {
      setError(e.message);
    }
  }, [applicationId]);

  useEffect(() => { load(); }, [load]);

  const loadSnapshotHistory = useCallback(async componentId => {
    try {
      const snapshots = await api.listComponentSnapshots(applicationId, componentId);
      setSnapshotsByComponent(prev => ({ ...prev, [componentId]: snapshots }));
    } catch (e) {
      setError(e.message);
    }
  }, [applicationId]);

  const createComponent = useCallback(async body => {
    await api.createAppComponent(applicationId, body);
    await load();
    onChanged?.();
  }, [applicationId, load, onChanged]);

  const updateComponent = useCallback(async (componentId, body) => {
    await api.updateAppComponent(applicationId, componentId, body);
    await load();
    onChanged?.();
  }, [applicationId, load, onChanged]);

  const deleteComponent = useCallback(async componentId => {
    await api.deleteAppComponent(applicationId, componentId);
    await load();
    onChanged?.();
  }, [applicationId, load, onChanged]);

  const uploadSnapshot = useCallback(async (componentId, file) => {
    await api.uploadComponentSnapshot(applicationId, componentId, file);
    await load();
    await loadSnapshotHistory(componentId);
    onChanged?.();
  }, [applicationId, load, loadSnapshotHistory, onChanged]);

  const deleteSnapshot = useCallback(async (componentId, snapshotId) => {
    await api.deleteComponentSnapshot(applicationId, componentId, snapshotId);
    await load();
    await loadSnapshotHistory(componentId);
    onChanged?.();
  }, [applicationId, load, loadSnapshotHistory, onChanged]);

  return {
    components, error, setError,
    snapshotsByComponent, loadSnapshotHistory,
    createComponent, updateComponent, deleteComponent,
    uploadSnapshot, deleteSnapshot
  };
}
