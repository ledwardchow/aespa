import { nav } from "../../lib/router";
import { PageHeader, Crumb, Sep } from "../../components/PageHeader";
import { useCampaign } from "./useCampaign";
import { StageBanner } from "./StageBanner";
import { CampaignOverviewTab } from "./CampaignOverviewTab";
import { CampaignComponentsTab } from "./CampaignComponentsTab";
import { CampaignConnectionsTab } from "./CampaignConnectionsTab";
import { CampaignReviewTab } from "./CampaignReviewTab";
import { CampaignRunsTab } from "./CampaignRunsTab";
import { CampaignFindingsTab } from "./CampaignFindingsTab";
import { CampaignActivityTab } from "./CampaignActivityTab";

const CAMPAIGN_TABS = [
  { key: "overview", label: "Overview" },
  { key: "components", label: "Components" },
  { key: "connections", label: "Connections" },
  { key: "review", label: "Review Leads" },
  { key: "runs", label: "Runs" },
  { key: "findings", label: "Findings" },
  { key: "activity", label: "Activity" }
];

// ── CampaignDetail ───────────────────────────────────────────────────────────
// The campaign workspace: header + stage banner + start/stop/retry/continue
// controls, then the seven tabs. Each tab owns its own data/state — this
// shell only owns the campaign record and the actions that mutate its
// lifecycle, so it never grows into a prop-bag monolith.
export function CampaignDetail({ applicationId, campaignId, initialTab }) {
  const { campaign, error, busy, load, start, stop, retry, continueToLive, isActive } = useCampaign(applicationId, campaignId);
  const tab = initialTab || "overview";

  if (!campaign) {
    return <div className="content scroll-content">{error ? <div className="alert error">{error}</div> : <div className="subtle">Loading…</div>}</div>;
  }

  const canStart = campaign.status === "draft";
  const canStop = isActive;
  const canRetry = campaign.status === "interrupted";
  const canContinue = campaign.status === "awaiting_review" && !!campaign.review_submitted_at;

  return <>
    <PageHeader
      title={<><Crumb href={`#/applications/${applicationId}/campaigns`}>{"Campaigns"}</Crumb><Sep />{campaign.name}</>}
      actions={<>
        {canStart && <button className="btn" disabled={busy} onClick={start}>{busy ? "Starting…" : "Start campaign"}</button>}
        {canStop && <button className="btn danger-outline" disabled={busy} onClick={stop}>{busy ? "Stopping…" : "Stop"}</button>}
        {canRetry && <button className="btn" disabled={busy} onClick={retry}>{busy ? "Resuming…" : "Retry"}</button>}
        {canContinue && <button className="btn" disabled={busy} onClick={continueToLive}>{busy ? "Starting…" : "Continue to live testing"}</button>}
      </>}
    />
    <div className="campaign-stage-region">
      <StageBanner status={campaign.status} />
    </div>
    <div className="tab-bar">
      {CAMPAIGN_TABS.map(t => <button key={t.key} className={"tab-btn" + (tab === t.key ? " active" : "")} onClick={() => nav(`#/applications/${applicationId}/campaigns/${campaignId}/${t.key}`)}>{t.label}</button>)}
    </div>
    <div className="content scroll-content">
      {error && <div className="alert error" style={{ marginBottom: 16 }}>{error}</div>}
      {tab === "overview" && <CampaignOverviewTab applicationId={applicationId} campaignId={campaignId} campaign={campaign} />}
      {tab === "components" && <CampaignComponentsTab applicationId={applicationId} campaign={campaign} />}
      {tab === "connections" && <CampaignConnectionsTab applicationId={applicationId} campaignId={campaignId} campaign={campaign} />}
      {tab === "review" && <CampaignReviewTab applicationId={applicationId} campaignId={campaignId} campaign={campaign} onSubmitted={load} canContinue={canContinue} continueToLive={continueToLive} continueBusy={busy} />}
      {tab === "runs" && <CampaignRunsTab applicationId={applicationId} campaign={campaign} />}
      {tab === "findings" && <CampaignFindingsTab applicationId={applicationId} campaignId={campaignId} />}
      {tab === "activity" && <CampaignActivityTab applicationId={applicationId} campaignId={campaignId} campaign={campaign} />}
    </div>
  </>;
}
