import { useState } from "react";

import { truncUrl } from "../../shared/lib/urls.js";
import { USER_PALETTE } from "../../shared/runs/presentation.jsx";

export function WebRunCrawlProgress({ run, crawlerTask, crawlerActive }) {
  const isRunning = crawlerActive;
  const progressBar = isRunning ? (
    <div className="crawl-progress-bar">
      <div className="crawl-progress-fill running" />
    </div>
  ) : null;
  const phaseLabel =
    {
      crawling: "Crawling and analysing pages",
      reconciling: "Checking direct access for each user",
      finalizing: "Finalising crawl results",
    }[run.phase] || (isRunning ? "Crawl in progress" : "Crawl is not running");
  const stageText = crawlerTask || phaseLabel;
  const stageStrip =
    isRunning || run.phase === "reconciling" || run.phase === "finalizing" ? (
      <div className="crawl-stage-strip">
        <span className="crawl-stage-label">Current stage</span>
        <span className="crawl-stage-text" title={stageText}>
          {stageText}
        </span>
      </div>
    ) : null;
  return (
    <>
      {progressBar}
      {stageStrip}
    </>
  );
}

export function WebRunUserCrawlProgress({ run, crawlerActive, activityLog = [] }) {
  const [userProgressOpen, setUserProgressOpen] = useState(true);
  const credentials = (run?.credentials || []).filter(
    (credential) => !run.crawl_credential_id || credential.id === run.crawl_credential_id,
  );
  const isRunning = crawlerActive;
  const progress = run.per_user_progress || {};
  const users =
    progress.unauthenticated || (isRunning && !run.crawl_credential_id)
      ? [{ username: "unauthenticated", label: "Unauthenticated" }, ...credentials]
      : credentials;
  if (!users.length) return null;
  const totalPages = users.reduce(
    (total, credential) => total + (progress[credential.username]?.pages_visited || 0),
    0,
  );
  const completedUsers = users.filter((credential) => progress[credential.username]?.done).length;
  return (
    <>
      <div className="crawl-user-progress-panel">
        <div className="crawl-user-progress-summary">
          <button
            className="btn ghost sm crawl-user-progress-toggle"
            type="button"
            aria-expanded={userProgressOpen}
            aria-controls="crawl-user-progress-details"
            onClick={() => setUserProgressOpen((open) => !open)}
          >
            <span aria-hidden="true">{userProgressOpen ? "▾" : "▸"}</span>
            User crawl progress
          </button>
          <span className="crawl-user-progress-count">
            {users.length} users · {totalPages} pages
            {completedUsers > 0 ? ` · ${completedUsers} done` : ""}
          </span>
        </div>
        <div
          id="crawl-user-progress-details"
          className="crawl-user-progress"
          hidden={!userProgressOpen}
        >
          {users.map((credential, index) => {
            const userProgress = progress[credential.username] || {};
            const active = isRunning && !userProgress.done;
            const loginEvent = [...activityLog]
              .reverse()
              .find(
                (entry) =>
                  entry.phase === "auth" &&
                  entry.message?.includes(credential.username) &&
                  ["start", "complete", "error"].includes(entry.status),
              );
            const loginStatus =
              userProgress.login_status ||
              { start: "pending", complete: "success", error: "failed" }[loginEvent?.status] ||
              "unknown";
            const loginLabel = {
              pending: "Logging in",
              success: "Login successful",
              failed: "Login failed",
              not_required: "No login needed",
              unknown: "Login status unknown",
            }[loginStatus];
            return (
              <div key={credential.username} className="crawl-user-row">
                <span
                  className={"crawl-user-dot" + (active ? " active" : "")}
                  style={{ background: USER_PALETTE[index % USER_PALETTE.length] }}
                />
                <span className="crawl-user-name" title={credential.username}>
                  {credential.label || credential.username}
                </span>
                {credential.username !== "unauthenticated" && (
                  <span className={`crawl-login-status ${loginStatus}`} title={loginLabel}>
                    {loginLabel}
                  </span>
                )}
                <span className="crawl-user-url mono" title={userProgress.current_url || ""}>
                  {userProgress.current_url
                    ? truncUrl(userProgress.current_url, 42)
                    : userProgress.done
                      ? "done"
                      : "waiting…"}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
