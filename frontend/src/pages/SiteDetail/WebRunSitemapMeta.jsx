import { useState } from "react";
import { api } from "../../lib/api";
import { truncUrl } from "../../lib/utilities";

/** Displays crawl metadata and owns editing the run's crawl limits. */
export function WebRunSitemapMeta({ run, crawlUsername, profiles, onRunUpdate, onError }) {
  const [editing, setEditing] = useState(false);
  const [depth, setDepth] = useState("");
  const [pages, setPages] = useState("");
  const [profileId, setProfileId] = useState(null);
  const [crawlerMode, setCrawlerMode] = useState("url");
  const profile = profiles.find(item => item.id === run.llm_profile_id);
  const multiUser = run.credentials?.length > 1;

  const edit = () => {
    setDepth(String(run.max_depth));
    setPages(String(run.max_pages));
    setProfileId(run.llm_profile_id || null);
    setCrawlerMode(run.crawler_mode || "url");
    setEditing(true);
  };
  const save = async () => {
    const maxDepth = parseInt(depth, 10);
    const maxPages = parseInt(pages, 10);
    if (!maxDepth || !maxPages || maxDepth < 1 || maxDepth > 10 || maxPages < 5 || maxPages > 500) return;
    try {
      onRunUpdate(await api.updateRun(run.id, {
        max_depth: maxDepth,
        max_pages: maxPages,
        crawler_mode: crawlerMode,
        llm_profile_id: profileId || null
      }));
      setEditing(false);
    } catch (error) {
      onError(error.message);
    }
  };

  return <div className="run-meta">
    <div className="run-stat"><span className="run-stat-val">{run.pages_discovered}</span><span className="run-stat-lbl">Pages found</span></div>
    {editing ? <div className="run-stat-edit">
      <div className="run-stat-edit-field">
        <label>Max depth</label>
        <input type="number" min="1" max="10" value={depth} onInput={event => setDepth(event.target.value)} style={{ width: 54 }} />
      </div>
      <div className="run-stat-edit-field">
        <label>Crawler</label>
        <select className="select" value={crawlerMode} onChange={event => setCrawlerMode(event.target.value)}>
          <option value="url">URL</option>
          <option value="interactive">Interactive SPA</option>
        </select>
      </div>
      <div className="run-stat-edit-field">
        <label>Max pages</label>
        <input type="number" min="5" max="500" value={pages} onInput={event => setPages(event.target.value)} style={{ width: 64 }} />
      </div>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <button className="btn sm" onClick={save}>Save</button>
        <button className="btn ghost sm" onClick={() => setEditing(false)}>Cancel</button>
      </div>
    </div> : <>
      <div className="run-stat"><span className="run-stat-val">{run.max_depth}</span><span className="run-stat-lbl">Max depth</span></div>
      <div className="run-stat"><span className="run-stat-val">{run.max_pages}</span><span className="run-stat-lbl">Max pages</span></div>
      <div className="run-stat"><span className="run-stat-val" style={{ fontSize: 12 }}>{run.crawler_mode === "interactive" ? "Interactive SPA" : "URL"}</span><span className="run-stat-lbl">Crawler</span></div>
      {run.llm_profile_id && profiles.length > 0 && <div className="run-stat">
        <span className="run-stat-val" style={{ fontSize: 12 }}>{profile?.name || "#" + run.llm_profile_id}</span>
        <span className="run-stat-lbl">LLM profile</span>
      </div>}
      {run.status !== "running" && <button className="btn ghost sm" style={{ alignSelf: "center", marginLeft: 4 }} title="Edit depth / pages" onClick={edit}>✎</button>}
    </>}
    {!multiUser && <>
      {crawlUsername && <div className="run-stat"><span className="run-stat-lbl">Crawling as</span><span className="run-stat-val" style={{ fontSize: 14 }}>{crawlUsername}</span></div>}
      {run.current_url && <div className="run-stat run-stat-url"><span className="run-stat-lbl">Current URL</span><span className="mono run-stat-url-val">{truncUrl(run.current_url, 50)}</span></div>}
    </>}
    {run.error_message && <div style={{ color: "var(--danger)", fontSize: 12, flex: 1 }}>{run.error_message}</div>}
  </div>;
}
