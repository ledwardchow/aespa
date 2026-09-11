import * as applicationsApi from "../../shared/api/applications.js";
import { useState, useEffect, useCallback } from "react";
import { nav } from "../../shared/navigation/router.js";

import { EmptyState } from "../../shared/ui/EmptyState.jsx";
import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";
import { IconPlus } from "../../shared/ui/Icons.jsx";
import { fmtDate } from "../../shared/lib/dates.js";

// ── CampaignsTab ─────────────────────────────────────────────────────────────
// Every campaign run for this application, newest first.

export function CampaignsTab({ applicationId }) {
  const [campaigns, setCampaigns] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const list = await applicationsApi.listCampaigns(applicationId);
      setCampaigns([...list].sort((a, b) => b.id - a.id));
    } catch (e) {
      setError(e.message);
    }
  }, [applicationId]);

  useEffect(() => {
    load();
  }, [load]);

  const onDelete = async (c) => {
    if (!confirm(`Delete campaign "${c.name}"? This removes every child scan it created.`)) return;
    try {
      await applicationsApi.deleteCampaign(applicationId, c.id);
      await load();
    } catch (e) {
      setError(
        e.status === 409 ? "This campaign cannot be deleted right now — stop it first." : e.message,
      );
    }
  };

  return (
    <div>
      {error && (
        <div className="alert error" style={{ marginBottom: 16 }}>
          {error}
        </div>
      )}
      <div className="row spread" style={{ marginBottom: 14 }}>
        <div className="form-section-title" style={{ margin: 0, border: "none", padding: 0 }}>
          Campaigns
        </div>
        <button
          className="btn"
          onClick={() => nav(`#/applications/${applicationId}/campaigns/new`)}
        >
          <IconPlus /> New campaign
        </button>
      </div>
      {campaigns === null && <div className="subtle">Loading…</div>}
      {campaigns !== null && campaigns.length === 0 && (
        <EmptyState
          title="No campaigns yet"
          sub="Start a campaign to freeze one snapshot per component and a set of live targets, then coordinate SAST and DAST across all of them."
          action={
            <button
              className="btn"
              onClick={() => nav(`#/applications/${applicationId}/campaigns/new`)}
            >
              <IconPlus /> New campaign
            </button>
          }
        />
      )}
      {campaigns && campaigns.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Started</th>
                <th>Completed</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.id}>
                  <td>
                    <a
                      href={`#/applications/${applicationId}/campaigns/${c.id}`}
                      style={{ fontWeight: 600 }}
                    >
                      {c.name}
                    </a>
                  </td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="subtle">{fmtDate(c.started_at)}</td>
                  <td className="subtle">{fmtDate(c.completed_at)}</td>
                  <td>
                    <div className="row" style={{ justifyContent: "flex-end" }}>
                      <button
                        className="btn secondary sm"
                        onClick={() => nav(`#/applications/${applicationId}/campaigns/${c.id}`)}
                      >
                        Open
                      </button>
                      <button className="btn danger-outline sm" onClick={() => onDelete(c)}>
                        Delete
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
  );
}
