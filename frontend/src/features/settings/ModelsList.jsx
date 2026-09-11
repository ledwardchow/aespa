import { useState, useMemo } from "react";

export function ModelsList({ visible, models, providers, busyId, onEdit, onDelete }) {
  const [modelSort, setModelSort] = useState({ field: "provider_name", dir: "asc" });
  const toggleSort = (setter, field) => {
    setter((s) => ({
      field,
      dir: s.field === field && s.dir === "asc" ? "desc" : "asc",
    }));
  };
  const sortArrow = (sortState, field) => {
    if (sortState.field !== field) return null;
    return (
      <span style={{ marginLeft: "4px", fontSize: "10px", opacity: 0.85 }}>
        {sortState.dir === "asc" ? "▲" : "▼"}
      </span>
    );
  };
  const sortedModels = useMemo(() => {
    if (!models) return [];
    const { field, dir } = modelSort;
    return [...models].sort((a, b) => {
      let valA = a[field];
      let valB = b[field];
      if (field === "provider_name") {
        valA = a.provider_name || `Provider #${a.provider_id}`;
        valB = b.provider_name || `Provider #${b.provider_id}`;
      } else if (field === "use_vision" || field === "is_active") {
        valA = a[field] ? 1 : 0;
        valB = b[field] ? 1 : 0;
      }
      if (valA == null) valA = "";
      if (valB == null) valB = "";
      let cmp =
        typeof valA === "number" && typeof valB === "number"
          ? valA - valB
          : String(valA).localeCompare(String(valB), undefined, {
              sensitivity: "base",
              numeric: true,
            });
      // Keep models in a predictable name order when providers compare equal.
      if (cmp === 0 && field === "provider_name") {
        return String(a.name || "").localeCompare(String(b.name || ""), undefined, {
          sensitivity: "base",
          numeric: true,
        });
      }
      return dir === "asc" ? cmp : -cmp;
    });
  }, [models, modelSort]);
  if (!visible) return null;
  return (
    <>
      {providers.length === 0 && (
        <div className="alert">Create a provider before adding models.</div>
      )}
      <div className="settings-list settings-list-profiles">
        <div className="settings-list-head">
          <div className="sortable" onClick={() => toggleSort(setModelSort, "name")}>
            Name {sortArrow(modelSort, "name")}
          </div>
          <div className="sortable" onClick={() => toggleSort(setModelSort, "provider_name")}>
            Provider {sortArrow(modelSort, "provider_name")}
          </div>
          <div className="sortable" onClick={() => toggleSort(setModelSort, "model")}>
            Model {sortArrow(modelSort, "model")}
          </div>
          <div className="sortable" onClick={() => toggleSort(setModelSort, "use_vision")}>
            Vision {sortArrow(modelSort, "use_vision")}
          </div>
          <div></div>
        </div>
        {sortedModels.map((p) => (
          <div className="settings-list-row" key={p.id}>
            <div>
              <strong>{p.name}</strong>
            </div>
            <div>{p.provider_name || `Provider #${p.provider_id}`}</div>
            <div className="mono">{p.model}</div>
            <div>{p.use_vision ? "On" : "Off"}</div>
            <div className="row settings-list-actions">
              <button className="btn sm" disabled={busyId === p.id} onClick={() => onEdit(p)}>
                Edit
              </button>
              <button
                className="btn danger-outline sm"
                disabled={busyId === p.id}
                onClick={() => onDelete(p)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
