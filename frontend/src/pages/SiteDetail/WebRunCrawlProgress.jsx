import { truncUrl } from "../../lib/utilities";
import { USER_PALETTE } from "./_helpers";

export function WebRunCrawlProgress({ run }) {
  const credentials = run.credentials || [];
  const multiUser = credentials.length > 1;
  const percent = run.status === "complete" ? 100 : Math.min(100, run.pages_discovered / run.max_pages * 100);
  const progressBar = run.status === "running" || run.pages_discovered > 0 ? <div className="crawl-progress-bar"><div className="crawl-progress-fill" style={{ width: percent + "%" }} /></div> : null;
  if (!multiUser) return progressBar;
  const progress = run.per_user_progress || {};
  return <>{progressBar}<div className="crawl-user-progress">
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
