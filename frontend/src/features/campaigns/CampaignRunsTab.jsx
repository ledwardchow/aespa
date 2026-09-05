import * as apiRunsApi from "../../shared/api/apiRuns.js";
import * as applicationsApi from "../../shared/api/applications.js";
import * as sastRunsApi from "../../shared/api/sastRuns.js";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { useState, useEffect } from "react";

import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";
import { TokenUsageBar } from "../../shared/ui/TokenUsageBar.jsx";
import {
  campaignDisplayStatus,
  campaignMemberDisplayStatus,
  safeParseJson,
} from "../../shared/runs/campaignPresentation.js";

// ── CampaignRunsTab ──────────────────────────────────────────────────────────
// Every child SAST/web/API run this campaign created, with a deep link to its
// existing detail route, plus the campaign's aggregated token usage. No run
// state lifecycle is duplicated here — the campaign record (already loaded by
// the shell) is the only source of truth; this only additionally resolves
// component/target names for readability.
export function CampaignRunsTab({
  applicationId,
  campaign,
  error,
  resumeSource,
  resumeTarget,
  busy,
}) {
  const [tokenUsage, setTokenUsage] = useState(null);
  const [tokenExpanded, setTokenExpanded] = useState(false);
  const [componentNames, setComponentNames] = useState({});
  const [targetNames, setTargetNames] = useState({});

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      applicationsApi.listAppComponents(applicationId),
      applicationsApi.listAppTargets(applicationId),
    ])
      .then(([comps, tgts]) => {
        if (cancelled) return;
        const cMap = {};
        comps.forEach((c) => {
          cMap[c.id] = c.name;
        });
        const tMap = {};
        tgts.forEach((t) => {
          tMap[t.id] = t.name || `#${t.target_id}`;
        });
        setComponentNames(cMap);
        setTargetNames(tMap);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [applicationId]);

  useEffect(() => {
    let cancelled = false;
    async function loadUsage() {
      const requests = [];
      for (const m of campaign.source_members) {
        if (m.sast_run_id)
          requests.push(sastRunsApi.getSastTokenUsage(m.sast_run_id).catch(() => null));
      }
      for (const m of campaign.target_members) {
        if (m.test_run_id) requests.push(webRunsApi.getTokenUsage(m.test_run_id).catch(() => null));
        if (m.api_test_run_id)
          requests.push(apiRunsApi.getApiTokenUsage(m.api_test_run_id).catch(() => null));
      }
      const results = await Promise.all(requests);
      if (cancelled) return;
      const totals = {
        total_input: 0,
        total_output: 0,
        total_cache_read: 0,
        total_cache_write: 0,
        total_ai_credits: 0,
        total_factory_credits: 0,
        total_premium_requests: 0,
        total_requests: 0,
        estimated_token_cost_usd: 0,
        estimated_credit_cost_usd: 0,
        estimated_total_cost_usd: 0,
        estimated_cost_available: false,
        by_model: {},
      };
      for (const r of results) {
        if (!r) continue;
        for (const key of Object.keys(totals)) {
          if (key === "by_model") continue;
          if (key === "estimated_cost_available") totals[key] = totals[key] || r[key];
          else totals[key] += r[key] || 0;
        }
        for (const [model, usage] of Object.entries(r.by_model || {})) {
          const aggregate = (totals.by_model[model] ||= { provider: usage.provider });
          for (const key of [
            "input",
            "output",
            "cache_read",
            "cache_write",
            "ai_credits",
            "factory_credits",
            "premium_requests",
            "requests",
            "estimated_token_cost_usd",
            "estimated_credit_cost_usd",
            "estimated_total_cost_usd",
          ]) {
            aggregate[key] = (aggregate[key] || 0) + (usage[key] || 0);
          }
          aggregate.estimated_cost_available =
            aggregate.estimated_cost_available || usage.estimated_cost_available;
        }
      }
      setTokenUsage(totals);
    }
    loadUsage();
    return () => {
      cancelled = true;
    };
  }, [campaign.source_members, campaign.target_members]);

  const sourceRuns = campaign.source_members;
  const targetRuns = campaign.target_members;
  const canResumeMember = !["sast_running", "correlating", "dast_running"].includes(
    campaignDisplayStatus(campaign),
  );
  const resumable = (status) => ["pending", "failed", "skipped", "incomplete"].includes(status);
  const warnings = safeParseJson(campaign.warnings_json, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="campaign-token-usage">
        <TokenUsageBar
          tokenUsage={tokenUsage}
          tokenExpanded={tokenExpanded}
          setTokenExpanded={setTokenExpanded}
        />
      </div>

      {error && <div className="alert error">{error}</div>}
      {campaign.error_message && <div className="alert error">{campaign.error_message}</div>}
      {warnings.length > 0 && (
        <div className="alert warning">
          <div style={{ fontWeight: 700, marginBottom: 4 }}>Partial-context warnings</div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <div className="form-section-title">Code scans (SAST)</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Component</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sourceRuns.map((m) => (
                <tr key={m.id}>
                  <td>{componentNames[m.component_id] || `Component #${m.component_id}`}</td>
                  <td>
                    <StatusBadge status={campaignMemberDisplayStatus(m)} />
                  </td>
                  <td>
                    {m.sast_run_id && (
                      <a
                        className="btn secondary sm"
                        href={`#/sast-runs/${m.sast_run_id}/progress`}
                      >
                        Open →
                      </a>
                    )}
                    {canResumeMember && resumable(campaignMemberDisplayStatus(m)) && (
                      <button
                        className="btn secondary sm"
                        title="Resume only this SAST action"
                        disabled={busy}
                        onClick={() => resumeSource(m.id)}
                      >
                        Resume SAST
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {sourceRuns.length === 0 && (
                <tr>
                  <td colSpan={3} className="subtle">
                    No SAST runs created yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      <div>
        <div className="form-section-title">Live target scans</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Target</th>
                <th>Type</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {targetRuns.map((m) => (
                <tr key={m.id}>
                  <td>{targetNames[m.target_id] || `#${m.target_id}`}</td>
                  <td>{m.target_type === "site" ? "Web" : "API"}</td>
                  <td>
                    <StatusBadge status={campaignMemberDisplayStatus(m)} />
                  </td>
                  <td>
                    {m.test_run_id && (
                      <a className="btn secondary sm" href={`#/runs/${m.test_run_id}/status`}>
                        Open web run →
                      </a>
                    )}
                    {m.api_test_run_id && (
                      <a
                        className="btn secondary sm"
                        href={`#/api-runs/${m.api_test_run_id}/status`}
                      >
                        Open API run →
                      </a>
                    )}
                    {canResumeMember && resumable(campaignMemberDisplayStatus(m)) && (
                      <button
                        className="btn secondary sm"
                        title={`Resume only this ${m.target_type === "site" ? "web" : "API"} action`}
                        disabled={busy}
                        onClick={() => resumeTarget(m.id)}
                      >
                        Resume {m.target_type === "site" ? "web" : "API"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {targetRuns.length === 0 && (
                <tr>
                  <td colSpan={4} className="subtle">
                    No live target runs created yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
