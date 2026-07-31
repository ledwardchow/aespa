import { truncUrl } from "../../lib/utilities";
import { USER_PALETTE } from "./_helpers";

export function WebRunCrawlProgress({ run, crawlerTask }) {
  const credentials = run.credentials || [];
  const multiUser = credentials.length > 1;
  const percent = run.status === "complete" ? 100 : Math.min(100, run.pages_discovered / run.max_pages * 100);
  const progressBar = run.status === "running" || run.pages_discovered > 0 ? <div className="crawl-progress-bar"><div className="crawl-progress-fill" style={{ width: percent + "%" }} /></div> : null;
  const phaseLabel = {
    crawling: "Crawling and analyzing pages",
    reconciling: "Checking direct access for each user",
    finalizing: "Finalizing crawl results",
    crawled: "Crawl complete"
  }[run.phase] || (run.status === "running" ? "Crawl in progress" : "Crawl is not running");
  const stageText = crawlerTask || phaseLabel;
  const stageStrip = run.status === "running" || run.phase === "reconciling" || run.phase === "finalizing" ? <div className="crawl-stage-strip">
    <span className="crawl-stage-label">Current stage</span>
    <span className="crawl-stage-text" title={stageText}>{stageText}</span>
  </div> : null;
  if (!multiUser) return <>{progressBar}{stageStrip}</>;
  const progress = run.per_user_progress || {};
  return <>{progressBar}{stageStrip}<div className="crawl-user-progress">
    {credentials.map((credential, index) => {
      const userProgress = progress[credential.username] || {};
      const active = run.status === "running" && !userProgress.done;
      return <div key={credential.username} className="crawl-user-row">
        <span className={'crawl-user-dot' + (active ? ' active' : '')} style={{ background: USER_PALETTE[index % USER_PALETTE.length] }} />
        <span className="crawl-user-name" title={credential.username}>{credential.label || credential.username}</span>
        <span className="crawl-user-pages">{userProgress.pages_visited || 0} pg</span>
        <span className="crawl-user-url mono" title={userProgress.current_url || ''}>{userProgress.current_url ? truncUrl(userProgress.current_url, 42) : userProgress.done ? 'done' : 'waiting…'}</span>
      </div>;
    })}
  </div></>;
}
