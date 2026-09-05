import { useState, useMemo } from "react";

export function ProfilesList({ visible, profiles, models, busyId, onActivate, onEdit, onDelete }) {
  const [profileSort, setProfileSort] = useState({ field: "name", dir: "asc" });
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
  const sortedProfiles = useMemo(() => {
    if (!profiles) return [];
    const { field, dir } = profileSort;
    return [...profiles].sort((a, b) => {
      let valA = a[field];
      let valB = b[field];
      if (field === "default_model_name") {
        valA = a.default_model_name || (a.default_model_id ? `#${a.default_model_id}` : "");
        valB = b.default_model_name || (b.default_model_id ? `#${b.default_model_id}` : "");
      } else if (field === "overrides_count") {
        valA = Object.keys(a.role_models || {}).length;
        valB = Object.keys(b.role_models || {}).length;
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
      return dir === "asc" ? cmp : -cmp;
    });
  }, [profiles, profileSort]);
  if (!visible) return null;
  return (
    <>
      {models.length === 0 && (
        <div className="alert">Create a model before adding scan profiles.</div>
      )}
      <div className="settings-list settings-list-scanprofiles">
        <div className="settings-list-head">
          <div className="sortable" onClick={() => toggleSort(setProfileSort, "name")}>
            Name {sortArrow(profileSort, "name")}
          </div>
          <div
            className="sortable"
            onClick={() => toggleSort(setProfileSort, "default_model_name")}
          >
            Default model {sortArrow(profileSort, "default_model_name")}
          </div>
          <div className="sortable" onClick={() => toggleSort(setProfileSort, "overrides_count")}>
            Overrides {sortArrow(profileSort, "overrides_count")}
          </div>
          <div className="sortable" onClick={() => toggleSort(setProfileSort, "is_active")}>
            Status {sortArrow(profileSort, "is_active")}
          </div>
          <div></div>
        </div>
        {sortedProfiles.map((p) => (
          <div className="settings-list-row" key={p.id}>
            <div>
              <strong>{p.name}</strong>
            </div>
            <div className="mono">
              {p.default_model_name || (p.default_model_id ? `#${p.default_model_id}` : "—")}
            </div>
            <div>
              {Object.keys(p.role_models || {}).length || <span className="subtle">none</span>}
            </div>
            <div>
              {p.is_active ? (
                <span className="badge ok">Active</span>
              ) : (
                <span className="subtle">Inactive</span>
              )}
            </div>
            <div className="row settings-list-actions">
              {!p.is_active && (
                <button
                  className="btn sm secondary"
                  disabled={busyId === p.id}
                  onClick={() => onActivate(p)}
                >
                  Use
                </button>
              )}
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
