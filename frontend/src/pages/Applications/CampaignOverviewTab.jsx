import { useState, useEffect } from "react";
import { api } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { TokenUsageBar } from "../../components/TokenUsageBar";
import { safeParseJson } from "./_helpers";

// ── CampaignOverviewTab ──────────────────────────────────────────────────────
// Overall stage warnings, per-child-member progress, and an aggregated token
// usage bar (best-effort — summed across every child run this campaign
// created, since there is no single campaign-level usage endpoint).
export function CampaignOverviewTab({ applicationId, campaign }) {
  const [tokenUsage, setTokenUsage] = useState(null);
  const [tokenExpanded, setTokenExpanded] = useState(false);
  const [componentNames, setComponentNames] = useState({});
  const [targetNames, setTargetNames] = useState({});

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.listAppComponents(applicationId), api.listAppTargets(applicationId)]).then(([comps, tgts]) => {
      if (cancelled) return;
      const cMap = {}; comps.forEach(c => { cMap[c.id] = c.name; });
      const tMap = {}; tgts.forEach(t => { tMap[t.id] = t.name || `#${t.target_id}`; });
      setComponentNames(cMap);
      setTargetNames(tMap);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [applicationId]);

  useEffect(() => {
    let cancelled = false;
    async function loadUsage() {
      const requests = [];
      for (const m of campaign.source_members) {
        if (m.sast_run_id) requests.push(api.getSastTokenUsage(m.sast_run_id).catch(() => null));
      }
      for (const m of campaign.target_members) {
        if (m.test_run_id) requests.push(api.getTokenUsage(m.test_run_id).catch(() => null));
        if (m.api_test_run_id) requests.push(api.getApiTokenUsage(m.api_test_run_id).catch(() => null));
      }
      const results = await Promise.all(requests);
      if (cancelled) return;
      const totals = { total_input: 0, total_output: 0, total_cache_read: 0, total_cache_write: 0, total_ai_credits: 0, total_factory_credits: 0, total_premium_requests: 0, total_requests: 0, by_model: {} };
      for (const r of results) {
        if (!r) continue;
        for (const key of Object.keys(totals)) {
          if (key === "by_model") continue;
          totals[key] += r[key] || 0;
        }
        for (const [model, usage] of Object.entries(r.by_model || {})) {
          const aggregate = totals.by_model[model] ||= { provider: usage.provider };
          for (const key of ["input", "output", "cache_read", "cache_write", "ai_credits", "factory_credits", "premium_requests", "requests"]) {
            aggregate[key] = (aggregate[key] || 0) + (usage[key] || 0);
          }
        }
      }
      setTokenUsage(totals);
    }
    loadUsage();
    return () => { cancelled = true; };
  }, [campaign.source_members, campaign.target_members]);

  const warnings = safeParseJson(campaign.warnings_json, []);

  return <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
    {campaign.error_message && <div className="alert error">{campaign.error_message}</div>}
    {warnings.length > 0 && <div className="alert warning">
      <div style={{ fontWeight: 700, marginBottom: 4 }}>Partial-context warnings</div>
      <ul style={{ margin: 0, paddingLeft: 18 }}>{warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
    </div>}

    <div className="campaign-token-usage">
      <TokenUsageBar tokenUsage={tokenUsage} tokenExpanded={tokenExpanded} setTokenExpanded={setTokenExpanded} />
    </div>

    <div>
      <div className="form-section-title">Code scans</div>
      <div className="app-progress-list">
        {campaign.source_members.map(m => <div key={m.id} className="app-progress-row">
          <span style={{ flex: 1 }}>{componentNames[m.component_id] || `Component #${m.component_id}`}</span>
          <StatusBadge status={m.status} />
          {m.sast_run_id && <a href={`#/sast-runs/${m.sast_run_id}`} className="subtle">View SAST run →</a>}
        </div>)}
        {campaign.source_members.length === 0 && <div className="subtle">No source members.</div>}
      </div>
    </div>

    <div>
      <div className="form-section-title">Live target scans</div>
      <div className="app-progress-list">
        {campaign.target_members.map(m => <div key={m.id} className="app-progress-row">
          <span className="badge neutral">{m.target_type === "site" ? "Site" : "API collection"}</span>
          <span style={{ flex: 1 }}>{targetNames[m.target_id] || `#${m.target_id}`}</span>
          <StatusBadge status={m.status} />
          {m.test_run_id && <a href={`#/runs/${m.test_run_id}`} className="subtle">View web run →</a>}
          {m.api_test_run_id && <a href={`#/api-runs/${m.api_test_run_id}`} className="subtle">View API run →</a>}
        </div>)}
        {campaign.target_members.length === 0 && <div className="subtle">No target members.</div>}
      </div>
    </div>
  </div>;
}
