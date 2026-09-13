import * as systemsApi from "../../shared/api/systems.js";
import { useState, useEffect, useCallback } from "react";
import { nav } from "../../shared/navigation/router.js";

import { IconPlus, IconSystems } from "../../shared/ui/Icons.jsx";
import { EmptyState } from "../../shared/ui/EmptyState.jsx";
import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";

// ── Systems list ───────────────────────────────────────────────────────
// Same card/table visual language as SitesList — a sortable table with an
// empty state, plus Open / New campaign actions per row.

export function SystemsList() {
  const [apps, setApps] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setApps(await systemsApi.listSystems());
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <div className="topbar">
        <div className="topbar-title">
          <IconSystems /> Systems
        </div>
        <div className="topbar-actions">
          <button className="btn" onClick={() => nav("#/systems/new")}>
            <IconPlus /> New system
          </button>
        </div>
      </div>
      <div className="content scroll-content">
        {error && (
          <div className="alert error" style={{ marginBottom: 16 }}>
            {error}
          </div>
        )}
        {apps === null && <div className="subtle">Loading…</div>}
        {apps !== null && apps.length === 0 && (
          <EmptyState
            icon="⬒"
            title="No systems yet"
            sub="Group several code repositories, Sites, and API Collections into one system so a single campaign can coordinate their SAST and DAST scans."
            action={
              <button className="btn" onClick={() => nav("#/systems/new")}>
                <IconPlus /> New system
              </button>
            }
          />
        )}
        {apps && apps.length > 0 && (
          <div className="table-wrap">
            <table>
              <colgroup>
                <col style={{ width: "26%" }} />
                <col style={{ width: "34%" }} />
                <col style={{ width: "16%" }} />
                <col style={{ width: "24%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Composition</th>
                  <th>Last campaign</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {apps.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <a href={`#/systems/${a.id}`} style={{ fontWeight: 600 }}>
                        {a.name}
                      </a>
                      {a.description && (
                        <div className="subtle" style={{ fontSize: 12, marginTop: 2 }}>
                          {a.description}
                        </div>
                      )}
                    </td>
                    <td className="subtle">
                      {a.component_count} component{a.component_count !== 1 ? "s" : ""} ·{" "}
                      {a.site_count} site{a.site_count !== 1 ? "s" : ""} · {a.api_collection_count}{" "}
                      API collection{a.api_collection_count !== 1 ? "s" : ""}
                    </td>
                    <td>
                      {a.last_campaign_status ? (
                        <StatusBadge status={a.last_campaign_status} />
                      ) : (
                        <span className="subtle">—</span>
                      )}
                    </td>
                    <td>
                      <div className="row" style={{ justifyContent: "flex-end" }}>
                        <button
                          className="btn secondary sm"
                          onClick={() => nav(`#/systems/${a.id}`)}
                        >
                          Open
                        </button>
                        <button
                          className="btn secondary sm"
                          onClick={() => nav(`#/systems/${a.id}/campaigns/new`)}
                        >
                          New campaign
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
