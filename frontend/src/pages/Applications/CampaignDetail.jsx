import { nav } from "../../lib/router";
import { PageHeader, Crumb, Sep } from "../../components/PageHeader";
import { useCampaign } from "./useCampaign";
import { StageBanner } from "./StageBanner";
import { CampaignComponentsTab } from "./CampaignComponentsTab";
import { CampaignConnectionsTab } from "./CampaignConnectionsTab";
import { CampaignReviewTab } from "./CampaignReviewTab";
import { CampaignRunsTab } from "./CampaignRunsTab";
import { CampaignFindingsTab } from "./CampaignFindingsTab";
import { CampaignActivityTab } from "./CampaignActivityTab";
import { campaignDisplayStatus } from "./_helpers";

const CAMPAIGN_TABS = [
  { key: "runs", label: "Runs" },
  { key: "components", label: "Components" },
  { key: "connections", label: "Connections" },
  { key: "review", label: "Review Leads" },
  { key: "findings", label: "Findings" },
  { key: "activity", label: "Activity" }
];

// ── CampaignDetail ───────────────────────────────────────────────────────────
// The campaign workspace: header + stage banner + start/stop/retry/continue
// controls, then the six tabs. Each tab owns its own data/state — this
// shell only owns the campaign record and the actions that mutate its
// lifecycle, so it never grows into a prop-bag monolith.
export function CampaignDetail({ applicationId, campaignId, initialTab, initialFindingRef }) {
  const { campaign, error, busy, load, start, stop, resume, resumeSource, resumeTarget, rebuildConnections, continueToLive, isActive } = useCampaign(applicationId, campaignId);
  const tab = CAMPAIGN_TABS.some(t => t.key === initialTab) ? initialTab : "runs";

  if (!campaign) {
    return <div className="content scroll-content">{error ? <div className="alert error">{error}</div> : <div className="subtle">Loading…</div>}</div>;
  }

  const canStart = campaign.status === "draft";
  const canStop = isActive;
  const hasCancelledSource = (campaign.source_members || []).some(member => member.run_status === "cancelled");
  const canResume = ["stopped", "interrupted"].includes(campaign.status)
    || (campaign.status === "awaiting_review" && hasCancelledSource);
  const canContinue = campaignDisplayStatus(campaign) === "awaiting_review" && !!campaign.review_submitted_at;

  return <>
    <PageHeader
      title={<><Crumb href={`#/applications/${applicationId}/campaigns`}>{"Campaigns"}</Crumb><Sep />{campaign.name}</>}
      actions={<>
        {canStart && <button className="btn" disabled={busy} onClick={start}>{busy ? "Starting…" : "Start campaign"}</button>}
        {canStop && <button className="btn danger-outline" disabled={busy} onClick={stop}>{busy ? "Stopping…" : "Stop"}</button>}
        {canResume && <button className="btn" disabled={busy} onClick={resume}>{busy ? "Resuming…" : "Resume campaign"}</button>}
        {canContinue && <button className="btn" disabled={busy} onClick={continueToLive}>{busy ? "Starting…" : "Continue to live testing"}</button>}
      </>}
    />
    <div className="campaign-stage-region">
      <StageBanner campaign={campaign} />
    </div>
    <div className="tab-bar">
      {CAMPAIGN_TABS.map(t => <button key={t.key} className={"tab-btn" + (tab === t.key ? " active" : "")} onClick={() => nav(`#/applications/${applicationId}/campaigns/${campaignId}/${t.key}`)}>{t.label}</button>)}
    </div>
    <div className="content scroll-content">
      {tab !== "runs" && error && <div className="alert error" style={{ marginBottom: 16 }}>{error}</div>}
      {tab === "components" && <CampaignComponentsTab applicationId={applicationId} campaign={campaign} />}
      {tab === "connections" && <CampaignConnectionsTab applicationId={applicationId} campaignId={campaignId} campaign={campaign} rebuildConnections={rebuildConnections} busy={busy} />}
      {tab === "review" && <CampaignReviewTab applicationId={applicationId} campaignId={campaignId} campaign={campaign} onSubmitted={load} canContinue={canContinue} continueToLive={continueToLive} continueBusy={busy} />}
      {tab === "runs" && <CampaignRunsTab applicationId={applicationId} campaign={campaign} error={error} resumeSource={resumeSource} resumeTarget={resumeTarget} busy={busy} />}
      {tab === "findings" && <CampaignFindingsTab applicationId={applicationId} campaignId={campaignId} initialFindingRef={initialFindingRef} />}
      {tab === "activity" && <CampaignActivityTab applicationId={applicationId} campaignId={campaignId} campaign={campaign} />}
    </div>
  </>;
}
