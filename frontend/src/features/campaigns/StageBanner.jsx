import {
  CAMPAIGN_STAGES,
  campaignDisplayStatus,
  stageIndex,
  isTerminalPause,
} from "../../shared/runs/campaignPresentation.js";
import { StatusBadge } from "../../shared/ui/StatusBadge.jsx";

// The user-visible stage sequence from the plan:
// Draft -> Scanning code -> Matching context -> Waiting for review ->
// Testing live targets -> Complete. A stopped/failed/interrupted campaign
// keeps the position it paused at, badged separately, rather than a false
// "still progressing" look. Member status can advance independently when a
// user resumes an individual scan, so derive the displayed stage from the
// complete campaign record.
export function StageBanner({ campaign }) {
  const status = campaignDisplayStatus(campaign);
  const paused = isTerminalPause(status);
  const currentIdx = paused ? -1 : stageIndex(status);
  return (
    <div className="campaign-stage-banner">
      {CAMPAIGN_STAGES.map((s, i) => {
        const isCurrent = !paused && i === currentIdx;
        const isPast = !paused && currentIdx >= 0 && i < currentIdx;
        const cls = isCurrent ? "current" : isPast ? "done" : "upcoming";
        return (
          <div key={s.key} className={`campaign-stage-step ${cls}`}>
            <span className="campaign-stage-num">{i + 1}</span>
            <span>{s.label}</span>
          </div>
        );
      })}
      {paused && (
        <div className="campaign-stage-paused">
          <StatusBadge status={status} />
        </div>
      )}
    </div>
  );
}
