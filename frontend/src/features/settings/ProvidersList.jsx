import { useState, useMemo } from "react";
import { PROVIDER_DEFAULT_BASE_URLS, API_FORMAT_LABELS } from "./providerMetadata.js";

export function ProvidersList({ visible, providers, busyId, onEdit, onDeleteProvider }) {
  const [providerSort, setProviderSort] = useState({ field: "name", dir: "asc" });
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
  const sortedProviders = useMemo(() => {
    if (!providers) return [];
    const { field, dir } = providerSort;
    return [...providers].sort((a, b) => {
      let valA = a[field];
      let valB = b[field];
      if (field === "api_label") {
        valA = API_FORMAT_LABELS[a.api_format] || a.api_format || "";
        valB = API_FORMAT_LABELS[b.api_format] || b.api_format || "";
      } else if (field === "base_url_display") {
        valA = a.base_url || PROVIDER_DEFAULT_BASE_URLS[a.api_format] || "";
        valB = b.base_url || PROVIDER_DEFAULT_BASE_URLS[b.api_format] || "";
      } else if (field === "models_display") {
        valA = (a.models || []).join(", ");
        valB = (b.models || []).join(", ");
      } else if (field === "limits") {
        valA = (a.max_tpm || 0) * 1000000 + (a.max_rpm || 0);
        valB = (b.max_tpm || 0) * 1000000 + (b.max_rpm || 0);
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
  }, [providers, providerSort]);
  if (!visible) return null;
  return (
    <div className="settings-list settings-list-providers">
      <div className="settings-list-head">
        <div className="sortable" onClick={() => toggleSort(setProviderSort, "name")}>
          Name {sortArrow(providerSort, "name")}
        </div>
        <div className="sortable" onClick={() => toggleSort(setProviderSort, "api_label")}>
          API {sortArrow(providerSort, "api_label")}
        </div>
        <div className="sortable" onClick={() => toggleSort(setProviderSort, "base_url_display")}>
          Base URL {sortArrow(providerSort, "base_url_display")}
        </div>
        <div className="sortable" onClick={() => toggleSort(setProviderSort, "models_display")}>
          Models {sortArrow(providerSort, "models_display")}
        </div>
        <div className="sortable" onClick={() => toggleSort(setProviderSort, "limits")}>
          Limits {sortArrow(providerSort, "limits")}
        </div>
        <div></div>
      </div>
      {sortedProviders.map((p) => (
        <div className="settings-list-row" key={p.id}>
          <div>
            <strong>{p.name}</strong>
          </div>
          <div>{API_FORMAT_LABELS[p.api_format] || p.api_format}</div>
          <div className="mono">
            {p.base_url || PROVIDER_DEFAULT_BASE_URLS[p.api_format] || "(must be set)"}
          </div>
          <div className="mono">{(p.models || []).join(", ")}</div>
          <div>
            {p.max_tpm || p.max_rpm ? (
              <>
                {p.max_tpm ? <div>{Number(p.max_tpm).toLocaleString()} TPM</div> : ""}
                {p.max_rpm ? (
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--muted)",
                      marginTop: 1,
                    }}
                  >
                    {Number(p.max_rpm).toLocaleString()} RPM
                  </div>
                ) : (
                  ""
                )}
              </>
            ) : (
              <span className="subtle">Unlimited</span>
            )}
          </div>
          <div className="row settings-list-actions">
            <button className="btn sm" disabled={busyId === p.id} onClick={() => onEdit(p)}>
              Edit
            </button>
            <button
              className="btn danger-outline sm"
              disabled={busyId === p.id}
              onClick={() => onDeleteProvider(p)}
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
