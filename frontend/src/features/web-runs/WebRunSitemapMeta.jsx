import * as webRunsApi from "../../shared/api/webRuns.js";
import { useState } from "react";

import { truncUrl } from "../../shared/lib/urls.js";

/** Displays crawl metadata and owns editing the run's crawl limits. */
export function WebRunSitemapMeta({
  run,
  graph,
  crawlUsername,
  profiles,
  onRunUpdate,
  onError,
  crawlCredentialId,
  onCrawlCredentialChange,
}) {
  const [editing, setEditing] = useState(false);
  const [depth, setDepth] = useState("");
  const [pages, setPages] = useState("");
  const [llmConcurrency, setLlmConcurrency] = useState("");
  const [profileId, setProfileId] = useState(null);
  const [crawlerMode, setCrawlerMode] = useState("url");
  const [showFlyout, setShowFlyout] = useState(false);
  const profile = profiles.find((item) => item.id === run.llm_profile_id);
  const multiUser = run.credentials?.length > 1;
  const credentials = run.credentials || [];

  const pendingNodes = (graph?.nodes || [])
    .filter(
      (n) =>
        n.status !== "failed" &&
        n.status !== "redirect" &&
        n.analysis_status !== "complete" &&
        n.analysis_status !== "skipped" &&
        (!n.context || n.context.length === 0),
    )
    .sort((a, b) => {
      const getRank = (status) => (status === "analyzing" ? 0 : status === "queued" ? 1 : 2);
      return getRank(a.analysis_status) - getRank(b.analysis_status);
    });

  const completedNodes = (graph?.nodes || []).filter(
    (n) => n.analysis_status === "complete" || (n.context && n.context.length > 0),
  );

  const skippedNodes = (graph?.nodes || []).filter((n) => n.analysis_status === "skipped");

  const activeCount = pendingNodes.filter((n) => n.analysis_status === "analyzing").length;
  const queuedCount = pendingNodes.filter(
    (n) => n.analysis_status === "queued" || n.analysis_status === "pending" || !n.analysis_status,
  ).length;

  const edit = () => {
    setDepth(String(run.max_depth));
    setPages(String(run.max_pages));
    setLlmConcurrency(run.llm_max_concurrency ? String(run.llm_max_concurrency) : "");
    setProfileId(run.llm_profile_id || null);
    setCrawlerMode(run.crawler_mode || "url");
    setEditing(true);
  };
  const save = async () => {
    const maxDepth = parseInt(depth, 10);
    const maxPages = parseInt(pages, 10);
    const parsedConcurrency = llmConcurrency ? parseInt(llmConcurrency, 10) : null;
    const maxConcurrency = parsedConcurrency && parsedConcurrency > 0 ? parsedConcurrency : null;
    if (!maxDepth || !maxPages || maxDepth < 1 || maxDepth > 10 || maxPages < 5 || maxPages > 500)
      return;
    try {
      onRunUpdate(
        await webRunsApi.updateRun(run.id, {
          max_depth: maxDepth,
          max_pages: maxPages,
          llm_max_concurrency: maxConcurrency,
          crawler_mode: crawlerMode,
          llm_profile_id: profileId || null,
        }),
      );
      setEditing(false);
    } catch (error) {
      onError(error.message);
    }
  };

  return (
    <div className="run-meta">
      <div className="run-stat">
        <span className="run-stat-val">{run.pages_discovered}</span>
        <span className="run-stat-lbl">Pages found</span>
      </div>
      {editing ? (
        <div className="run-stat-edit">
          <div className="run-stat-edit-field">
            <label>Max depth</label>
            <input
              type="number"
              min="1"
              max="10"
              value={depth}
              onInput={(event) => setDepth(event.target.value)}
              style={{ width: 54 }}
            />
          </div>
          <div className="run-stat-edit-field">
            <label>Crawler</label>
            <select
              className="select"
              value={crawlerMode}
              onChange={(event) => setCrawlerMode(event.target.value)}
            >
              <option value="url">URL</option>
              <option value="interactive">Interactive SPA</option>
            </select>
          </div>
          <div className="run-stat-edit-field">
            <label>Max pages</label>
            <input
              type="number"
              min="5"
              max="500"
              value={pages}
              onInput={(event) => setPages(event.target.value)}
              style={{ width: 64 }}
            />
          </div>
          <div className="run-stat-edit-field">
            <label>LLM Concurrency</label>
            <input
              type="number"
              min="0"
              max="100"
              placeholder="Unlimited"
              value={llmConcurrency}
              onInput={(event) => setLlmConcurrency(event.target.value)}
              style={{ width: 80 }}
              title="Max concurrent LLM page analysis requests (0 or empty = unlimited)"
            />
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <button className="btn sm" onClick={save}>
              Save
            </button>
            <button className="btn ghost sm" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="run-stat">
            <span className="run-stat-val">{run.max_depth}</span>
            <span className="run-stat-lbl">Max depth</span>
          </div>
          <div className="run-stat">
            <span className="run-stat-val">{run.max_pages}</span>
            <span className="run-stat-lbl">Max pages</span>
          </div>
          <div className="run-stat">
            <span className="run-stat-val" style={{ fontSize: 12 }}>
              {run.crawler_mode === "interactive" ? "Interactive SPA" : "URL"}
            </span>
            <span className="run-stat-lbl">Crawler</span>
          </div>
          <div className="run-stat">
            <span className="run-stat-val" style={{ fontSize: 12 }}>
              {run.llm_max_concurrency ? `${run.llm_max_concurrency} max` : "Unlimited"}
            </span>
            <span className="run-stat-lbl">LLM Concurrency</span>
          </div>
          {run.llm_profile_id && profiles.length > 0 && (
            <div className="run-stat">
              <span className="run-stat-val" style={{ fontSize: 12 }}>
                {profile?.name || "#" + run.llm_profile_id}
              </span>
              <span className="run-stat-lbl">LLM profile</span>
            </div>
          )}
          {run.status !== "running" && (
            <button
              className="btn ghost sm"
              style={{ alignSelf: "center", marginLeft: 4 }}
              title="Edit depth / pages / LLM concurrency"
              onClick={edit}
            >
              ✎
            </button>
          )}
        </>
      )}
      {!multiUser && (
        <>
          {crawlUsername && (
            <div className="run-stat">
              <span className="run-stat-lbl">Crawling as</span>
              <span className="run-stat-val" style={{ fontSize: 14 }}>
                {crawlUsername}
              </span>
            </div>
          )}
          {run.current_url && (
            <div className="run-stat run-stat-url">
              <span className="run-stat-lbl">Current URL</span>
              <span className="mono run-stat-url-val">{truncUrl(run.current_url, 50)}</span>
            </div>
          )}
        </>
      )}
      {credentials.length > 0 && run.status !== "running" && (
        <div className="run-stat" style={{ flexDirection: "column", gap: 2 }}>
          <span className="run-stat-lbl">Next crawl as</span>
          <select
            className="select"
            style={{ fontSize: 12 }}
            value={crawlCredentialId || ""}
            onChange={(e) =>
              onCrawlCredentialChange &&
              onCrawlCredentialChange(e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">All users</option>
            {credentials.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label ? `${c.label} (${c.username})` : c.username}
              </option>
            ))}
          </select>
        </div>
      )}
      {run.error_message && (
        <div style={{ color: "var(--danger)", fontSize: 12, flex: 1 }}>{run.error_message}</div>
      )}
      {(run.status === "running" ||
        (run.llm_pending || 0) > 0 ||
        (run.llm_completed || 0) > 0 ||
        pendingNodes.length > 0) && (
        <div
          className="run-stat"
          style={{ minWidth: 90, marginLeft: "auto", cursor: "pointer", position: "relative" }}
          onClick={() => setShowFlyout((prev) => !prev)}
          title="Click to view LLM analysis queue details"
        >
          <span
            className="run-stat-val"
            style={{
              fontSize: 13,
              fontWeight: 600,
              color:
                activeCount > 0
                  ? "var(--warning, #f59e0b)"
                  : queuedCount > 0
                    ? "var(--text, #e5e7eb)"
                    : (run.llm_completed || 0) > 0 || completedNodes.length > 0
                      ? "var(--success, #10b981)"
                      : "var(--muted)",
            }}
          >
            {activeCount > 0 && queuedCount > 0
              ? `${activeCount} active · ${queuedCount} queued`
              : activeCount > 0
                ? `${activeCount} active`
                : queuedCount > 0
                  ? `${queuedCount} queued`
                  : (run.llm_completed || 0) > 0 || completedNodes.length > 0
                    ? `${run.llm_completed || completedNodes.length} complete`
                    : "Clear"}
          </span>
          <span className="run-stat-lbl">LLM Queue ▾</span>

          {showFlyout && (
            <div className="llm-queue-popover" onClick={(e) => e.stopPropagation()}>
              <div className="llm-queue-popover-header">
                <span>LLM Page Analysis Queue</span>
                <button
                  className="btn ghost sm"
                  style={{ padding: "0 4px", height: 20, minWidth: 20, fontSize: 12 }}
                  onClick={() => setShowFlyout(false)}
                >
                  ✕
                </button>
              </div>
              <div className="llm-queue-popover-body">
                {pendingNodes.length > 0 && (
                  <>
                    <div className="llm-queue-section-title">
                      Pending Analysis ({pendingNodes.length})
                    </div>
                    {pendingNodes.map((node) => (
                      <div key={node.id} className="llm-queue-item">
                        <span className="llm-queue-item-url" title={node.url}>
                          {truncUrl(node.url, 38)}
                        </span>
                        <span
                          className={`pill ${node.analysis_status === "analyzing" ? "warning" : "neutral"} sm`}
                        >
                          {node.analysis_status === "analyzing"
                            ? "Analysing…"
                            : node.analysis_status === "queued"
                              ? "Queued"
                              : "Pending"}
                        </span>
                      </div>
                    ))}
                  </>
                )}
                {skippedNodes.length > 0 && (
                  <>
                    <div className="llm-queue-section-title">
                      Skipped Pages ({skippedNodes.length})
                    </div>
                    {skippedNodes
                      .slice(-10)
                      .reverse()
                      .map((node) => (
                        <div key={node.id} className="llm-queue-item">
                          <span className="llm-queue-item-url" title={node.url}>
                            {truncUrl(node.url, 38)}
                          </span>
                          <span className="pill neutral sm">Skipped</span>
                        </div>
                      ))}
                  </>
                )}
                {completedNodes.length > 0 && (
                  <>
                    <div className="llm-queue-section-title">
                      Analysed Pages ({completedNodes.length})
                    </div>
                    {completedNodes
                      .slice(-10)
                      .reverse()
                      .map((node) => (
                        <div key={node.id} className="llm-queue-item">
                          <span className="llm-queue-item-url" title={node.url}>
                            {node.state_label || truncUrl(node.url, 38)}
                          </span>
                          <span className="pill success sm">Complete</span>
                        </div>
                      ))}
                  </>
                )}
                {pendingNodes.length === 0 &&
                  completedNodes.length === 0 &&
                  skippedNodes.length === 0 && (
                    <div
                      className="subtle"
                      style={{ padding: "12px 0", textAlign: "center", fontSize: 11 }}
                    >
                      No pages currently queued for LLM analysis.
                    </div>
                  )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
