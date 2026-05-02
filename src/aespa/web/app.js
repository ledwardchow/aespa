import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import htm from "htm";
import * as d3 from "d3";

const html = htm.bind(React.createElement);

// ── API client ────────────────────────────────────────────────────────────────

const api = {
  listSites:        ()            => req("/api/sites"),
  getSite:          (id)          => req(`/api/sites/${id}`),
  createSite:       (b)           => req("/api/sites",         { method:"POST",   body:b }),
  updateSite:       (id,b)        => req(`/api/sites/${id}`,   { method:"PUT",    body:b }),
  deleteSite:       (id)          => req(`/api/sites/${id}`,   { method:"DELETE" }),
  getLLMConfig:     ()            => req("/api/settings/llm"),
  upsertLLMConfig:  (b)           => req("/api/settings/llm",  { method:"PUT",    body:b }),
  getDefaultModels: ()            => req("/api/settings/llm/models"),
  listRuns:         (siteId)      => req(`/api/sites/${siteId}/test-runs`),
  createRun:        (siteId,b)    => req(`/api/sites/${siteId}/test-runs`, { method:"POST", body:b }),
  getRun:           (id)          => req(`/api/test-runs/${id}`),
  deleteRun:        (id)          => req(`/api/test-runs/${id}`,  { method:"DELETE" }),
  startRun:         (id)          => req(`/api/test-runs/${id}/start`,   { method:"POST" }),
  stopRun:          (id)          => req(`/api/test-runs/${id}/stop`,    { method:"POST" }),
  restartRun:       (id)          => req(`/api/test-runs/${id}/restart`, { method:"POST" }),
  getGraph:         (id)          => req(`/api/test-runs/${id}/graph`),
  listPages:        (id)          => req(`/api/test-runs/${id}/pages`),
  getPage:          (runId,pgId)  => req(`/api/test-runs/${runId}/pages/${pgId}`),
  setPageScope:     (runId,pgId,b)=> req(`/api/test-runs/${runId}/pages/${pgId}/scope`, { method:"PATCH", body:b }),
  deletePage:       (runId,pgId,cascade) => req(`/api/test-runs/${runId}/pages/${pgId}?cascade=${cascade}`, { method:"DELETE" }),
  updateRun:        (id,b)        => req(`/api/test-runs/${id}`,                         { method:"PATCH", body:b }),
  startScan:        (id)          => req(`/api/test-runs/${id}/scan/start`,               { method:"POST" }),
  stopScan:         (id)          => req(`/api/test-runs/${id}/scan/stop`,                { method:"POST" }),
  getScanStatus:    (id)          => req(`/api/test-runs/${id}/scan/status`),
  getFindings:      (id)          => req(`/api/test-runs/${id}/findings`),
  deleteFinding:    (id,fid)      => req(`/api/test-runs/${id}/findings/${fid}`, { method:"DELETE" }),
  scanPage:         (id,pgId)     => req(`/api/test-runs/${id}/pages/${pgId}/scan`,       { method:"POST" }),
  getTraffic:       (id,since)    => req(`/api/test-runs/${id}/traffic?since_id=${since||0}`),
};

async function req(url, opts = {}) {
  const init = { method: opts.method || "GET", headers: { "Content-Type": "application/json" } };
  if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
  const res  = await fetch(url, init);
  if (res.status === 204) return null;
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const msg = formatError(data) || `${res.status} ${res.statusText}`;
    const err = new Error(msg); err.status = res.status; throw err;
  }
  return data;
}

function formatError(d) {
  if (!d) return null;
  if (typeof d.detail === "string") return d.detail;
  if (Array.isArray(d.detail)) return d.detail.map(x => `${(x.loc||[]).join(".")}: ${x.msg}`).join("\n");
  return JSON.stringify(d);
}

// ── Hash router ───────────────────────────────────────────────────────────────

function useRoute() {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const cb = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", cb);
    return () => window.removeEventListener("hashchange", cb);
  }, []);

  if (!hash || hash === "#/" || hash === "#") return { name: "list" };

  let m;
  if ((m = hash.match(/^#\/sites\/new$/)))               return { name: "site-new" };
  if ((m = hash.match(/^#\/sites\/(\d+)\/edit$/)))       return { name: "site-edit",   id: +m[1] };
  if ((m = hash.match(/^#\/sites\/(\d+)\/runs\/new$/)))  return { name: "run-new",     siteId: +m[1] };
  if ((m = hash.match(/^#\/sites\/(\d+)$/)))             return { name: "site-detail", id: +m[1] };
  if ((m = hash.match(/^#\/runs\/(\d+)$/)))              return { name: "run-detail",  id: +m[1] };
  if (hash === "#/settings")                             return { name: "settings" };

  return { name: "list" };
}

const nav = (to) => { window.location.hash = to; };

// ── Icons ─────────────────────────────────────────────────────────────────────

const IconSites = () => html`<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
  <rect x="1" y="1" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
  <rect x="9" y="1" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
  <rect x="1" y="9" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
  <rect x="9" y="9" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
</svg>`;

const IconSettings = () => html`<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
  <circle cx="8" cy="8" r="2.2" stroke="currentColor" stroke-width="1.4"/>
  <path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M2.93 2.93l1.06 1.06M12.01 12.01l1.06 1.06M2.93 13.07l1.06-1.06M12.01 3.99l1.06-1.06"
    stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
</svg>`;

const IconPlus = () => html`<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
  <path d="M7 1v12M1 7h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
</svg>`;

const IconCheck = () => html`<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
  <path d="M2 7l4 4 6-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;

const IconPlay = () => html`<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
  <path d="M3 2l9 5-9 5V2z" fill="currentColor"/>
</svg>`;

const IconStop = () => html`<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
  <rect x="2" y="2" width="10" height="10" rx="1.5" fill="currentColor"/>
</svg>`;

// ── Shell ──────────────────────────────────────────────────────────────────────

function App() {
  const route = useRoute();
  const onSites    = ["list","site-new","site-edit","site-detail","run-new","run-detail"].includes(route.name);
  const onSettings = route.name === "settings";

  return html`
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="logo"><div className="logo-icon">A</div><span className="logo-text">ESPA</span></div>
          <div className="logo-sub">AI-Enabled Security Pentesting Agent</div>
        </div>
        <nav className="sidebar-nav">
          <div className="nav-section-label">Targets</div>
          <a href="#/" className=${"nav-item"+(onSites?" active":"")}>
            <span className="nav-icon"><${IconSites}/></span> Sites
          </a>
          <div className="nav-section-label" style=${{marginTop:8}}>Configuration</div>
          <a href="#/settings" className=${"nav-item"+(onSettings?" active":"")}>
            <span className="nav-icon"><${IconSettings}/></span> LLM Settings
          </a>
        </nav>
        <div className="sidebar-footer">v0.1.0</div>
      </aside>

      <div className="main">
        ${route.name==="list"        && html`<${SitesList}/>`}
        ${route.name==="site-new"    && html`<${SiteForm} key="new"/>`}
        ${route.name==="site-edit"   && html`<${SiteForm} key=${route.id} siteId=${route.id}/>`}
        ${route.name==="site-detail" && html`<${SiteDetail} key=${route.id} siteId=${route.id}/>`}
        ${route.name==="run-new"     && html`<${TestRunForm} key=${route.siteId} siteId=${route.siteId}/>`}
        ${route.name==="run-detail"  && html`<${TestRunDetail} key=${route.id} runId=${route.id}/>`}
        ${route.name==="settings"    && html`<${SettingsPage}/>`}
      </div>
    </div>
  `;
}

// ── Sites list ────────────────────────────────────────────────────────────────

function SitesList() {
  const [sites, setSites] = useState(null);
  const [error, setError] = useState(null);
  const load = useCallback(async () => {
    try { setSites(await api.listSites()); } catch(e) { setError(e.message); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const onDelete = async (s) => {
    if (!confirm(`Delete "${s.name}"? This also removes all test runs and credentials.`)) return;
    try { await api.deleteSite(s.id); await load(); } catch(e) { setError(e.message); }
  };
  const authCount = sites ? sites.filter(s=>s.requires_auth).length : 0;
  const credCount = sites ? sites.reduce((n,s)=>n+s.credential_count,0) : 0;

  return html`
    <div className="topbar">
      <div className="topbar-title">Sites</div>
      <div className="topbar-actions">
        <button className="btn" onClick=${()=>nav("#/sites/new")}><${IconPlus}/> New site</button>
      </div>
    </div>
    <div className="content">
      ${error && html`<div className="alert error" style=${{marginBottom:16}}>${error}</div>`}
      ${sites&&sites.length>0 && html`
        <div className="stat-strip">
          <div className="stat"><span className="stat-value">${sites.length}</span><span className="stat-label">Sites</span></div>
          <div className="stat"><span className="stat-value">${authCount}</span><span className="stat-label">Authenticated</span></div>
          <div className="stat"><span className="stat-value">${credCount}</span><span className="stat-label">Credentials</span></div>
        </div>`}
      ${sites===null && html`<div className="subtle">Loading…</div>`}
      ${sites!==null&&sites.length===0 && html`
        <div className="empty-state">
          <div className="empty-icon">⬡</div>
          <div className="empty-msg">No sites configured</div>
          <div className="empty-sub">Add a target site to begin setting up your pentest scope.</div>
          <button className="btn" onClick=${()=>nav("#/sites/new")}><${IconPlus}/> New site</button>
        </div>`}
      ${sites&&sites.length>0 && html`
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Base URL</th><th>Auth</th><th>Credentials</th><th></th></tr></thead>
            <tbody>${sites.map(s=>html`
              <tr key=${s.id}>
                <td><a href=${`#/sites/${s.id}`} style=${{fontWeight:600}}>${s.name}</a></td>
                <td className="url">${s.base_url}</td>
                <td>${s.requires_auth?html`<span className="badge ok">required</span>`:html`<span className="badge neutral">none</span>`}</td>
                <td>${s.credential_count>0?s.credential_count:html`<span className="subtle">—</span>`}</td>
                <td>
                  <div className="row" style=${{justifyContent:"flex-end"}}>
                    <button className="btn secondary sm" onClick=${()=>nav(`#/sites/${s.id}`)}>Open</button>
                    <button className="btn danger-outline sm" onClick=${()=>onDelete(s)}>Delete</button>
                  </div>
                </td>
              </tr>`)}
            </tbody>
          </table>
        </div>`}
    </div>
  `;
}

// ── Site detail ───────────────────────────────────────────────────────────────

function SiteDetail({ siteId }) {
  const [site, setSite]   = useState(null);
  const [runs, setRuns]   = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([api.getSite(siteId), api.listRuns(siteId)]);
      setSite(s); setRuns(r);
    } catch(e) { setError(e.message); }
  }, [siteId]);
  useEffect(() => { load(); }, [load]);

  const deleteRun = async (run) => {
    if (!confirm(`Delete run "${run.name}"?`)) return;
    try { await api.deleteRun(run.id); setRuns(r=>r.filter(x=>x.id!==run.id)); }
    catch(e) { setError(e.message); }
  };

  const STATUS_BADGE = {
    pending:  html`<span className="badge">pending</span>`,
    running:  html`<span className="badge running">running</span>`,
    complete: html`<span className="badge ok">complete</span>`,
    failed:   html`<span className="badge danger">failed</span>`,
    stopped:  html`<span className="badge">stopped</span>`,
  };

  return html`
    <div className="topbar">
      <div className="topbar-title">
        <a href="#/" style=${{color:"var(--muted)",fontWeight:400}}>Sites</a>
        <span className="breadcrumb-sep"> / </span>
        ${site ? site.name : "…"}
      </div>
      <div className="topbar-actions">
        ${site && html`<button className="btn secondary" onClick=${()=>nav(`#/sites/${siteId}/edit`)}>Edit site</button>`}
        <button className="btn" onClick=${()=>nav(`#/sites/${siteId}/runs/new`)}><${IconPlus}/> New run</button>
      </div>
    </div>
    <div className="content stack">
      ${error && html`<div className="alert error">${error}</div>`}

      ${site && html`
        <div className="card" style=${{padding:"16px 20px"}}>
          <div className="row spread">
            <div className="stack" style=${{gap:4}}>
              <div style=${{fontSize:13,color:"var(--muted)"}}>Base URL</div>
              <div className="mono" style=${{fontSize:13}}>${site.base_url}</div>
            </div>
            <div className="row" style=${{gap:16}}>
              ${site.requires_auth
                ? html`<span className="badge ok">auth required</span>`
                : html`<span className="badge neutral">no auth</span>`}
              <span className="subtle">${site.credentials.length} credential${site.credentials.length!==1?"s":""}</span>
            </div>
          </div>
          ${site.notes && html`<div style=${{marginTop:10,fontSize:13,color:"var(--muted)"}}>${site.notes}</div>`}
        </div>`}

      <div>
        <div className="row spread" style=${{marginBottom:12}}>
          <div style=${{fontSize:13,fontWeight:700,color:"var(--muted)",textTransform:"uppercase",letterSpacing:"0.6px"}}>Test Runs</div>
        </div>
        ${runs===null && html`<div className="subtle">Loading…</div>`}
        ${runs!==null&&runs.length===0 && html`
          <div className="empty-state" style=${{padding:"32px"}}>
            <div className="empty-msg">No test runs yet</div>
            <div className="empty-sub">Create a new run to start crawling this site.</div>
            <button className="btn" onClick=${()=>nav(`#/sites/${siteId}/runs/new`)}><${IconPlus}/> New run</button>
          </div>`}
        ${runs&&runs.length>0 && html`
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Status</th><th>Pages</th><th>Created</th><th></th></tr></thead>
              <tbody>${runs.map(r=>html`
                <tr key=${r.id}>
                  <td><strong>${r.name}</strong></td>
                  <td>${STATUS_BADGE[r.status]||r.status}</td>
                  <td>${r.pages_discovered}</td>
                  <td className="subtle">${fmtDate(r.created_at)}</td>
                  <td>
                    <div className="row" style=${{justifyContent:"flex-end"}}>
                      <button className="btn secondary sm" onClick=${()=>nav(`#/runs/${r.id}`)}>Open</button>
                      <button className="btn danger-outline sm" onClick=${()=>deleteRun(r)}>Delete</button>
                    </div>
                  </td>
                </tr>`)}
              </tbody>
            </table>
          </div>`}
      </div>
    </div>
  `;
}

// ── Site form (create/edit) ───────────────────────────────────────────────────

function SiteForm({ siteId }) {
  const isEdit = typeof siteId === "number";
  const [form, setForm]       = useState({ name:"", base_url:"", requires_auth:false, login_url:"", notes:"", credentials:[] });
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState(null);

  useEffect(() => {
    if (!isEdit) return;
    (async () => {
      try {
        const d = await api.getSite(siteId);
        setForm({ name:d.name, base_url:d.base_url, requires_auth:d.requires_auth,
          login_url:d.login_url||"", notes:d.notes||"",
          credentials:d.credentials.map(c=>({username:c.username,password:c.password,label:c.label||""})) });
      } catch(e) { setError(e.message); } finally { setLoading(false); }
    })();
  }, [isEdit, siteId]);

  const upd = p => { setForm(f=>({...f,...p})); };
  const updC = (i,p) => setForm(f=>({...f,credentials:f.credentials.map((c,j)=>j===i?{...c,...p}:c)}));
  const addC = () => upd({ credentials:[...form.credentials,{username:"",password:"",label:""}] });
  const rmC  = i  => upd({ credentials:form.credentials.filter((_,j)=>j!==i) });

  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true);
    const payload = { name:form.name.trim(), base_url:form.base_url.trim(), requires_auth:form.requires_auth,
      login_url:form.requires_auth?form.login_url.trim():null, notes:form.notes.trim()||null,
      credentials:form.requires_auth?form.credentials.map(c=>({username:c.username,password:c.password,label:c.label||null})):[] };
    try {
      if (isEdit) { await api.updateSite(siteId,payload); nav(`#/sites/${siteId}`); }
      else        { const s = await api.createSite(payload); nav(`#/sites/${s.id}`); }
    } catch(e) { setError(e.message); } finally { setSaving(false); }
  };

  const bc = isEdit
    ? html`<a href=${`#/sites/${siteId}`} style=${{color:"var(--muted)",fontWeight:400}}>${form.name||"Site"}</a><span className="breadcrumb-sep"> / </span>Edit`
    : "New site";

  return html`
    <div className="topbar"><div className="topbar-title">${bc}</div></div>
    <div className="content">
      ${loading && html`<div className="subtle">Loading…</div>`}
      ${!loading && html`
        <form className="card" onSubmit=${onSubmit}>
          ${error && html`<div className="alert error">${error}</div>`}
          <div className="form-section-title">Site</div>
          <div className="field"><label>Name</label>
            <input type="text" required value=${form.name} placeholder="e.g. Juice Shop" onChange=${e=>upd({name:e.target.value})}/></div>
          <div className="field"><label>Base URL</label>
            <input type="url" required value=${form.base_url} placeholder="https://target.example.com" onChange=${e=>upd({base_url:e.target.value})}/></div>
          <div className="field"><label>Notes (optional)</label>
            <textarea value=${form.notes} placeholder="Scope, contacts…" onChange=${e=>upd({notes:e.target.value})}/></div>
          <div className="divider"/>
          <div className="form-section-title">Authentication</div>
          <label className="toggle-row">
            <input type="checkbox" checked=${form.requires_auth} onChange=${e=>upd({requires_auth:e.target.checked})}/>
            <span>This site requires authentication</span>
          </label>
          ${form.requires_auth && html`
            <div className="field"><label>Login page URL</label>
              <input type="url" required value=${form.login_url} placeholder="https://target.example.com/login" onChange=${e=>upd({login_url:e.target.value})}/></div>
            <fieldset><legend>Credentials</legend>
              ${form.credentials.length===0&&html`<div className="subtle">No credentials yet.</div>`}
              ${form.credentials.map((c,i)=>html`
                <div className="cred-row" key=${i}>
                  <div className="field"><label>Username</label><input type="text" required value=${c.username} onChange=${e=>updC(i,{username:e.target.value})}/></div>
                  <div className="field"><label>Password</label><input type="text" required value=${c.password} onChange=${e=>updC(i,{password:e.target.value})}/></div>
                  <div className="field"><label>Label</label><input type="text" value=${c.label} placeholder="admin" onChange=${e=>updC(i,{label:e.target.value})}/></div>
                  <div style=${{paddingBottom:1}}><button type="button" className="btn ghost sm" onClick=${()=>rmC(i)}>Remove</button></div>
                </div>`)}
              <button type="button" className="btn secondary sm" onClick=${addC}><${IconPlus}/> Add credential</button>
            </fieldset>`}
          <div className="divider"/>
          <div className="row spread">
            <button type="button" className="btn ghost" onClick=${()=>isEdit?nav(`#/sites/${siteId}`):nav("#/")}>Cancel</button>
            <button type="submit" className="btn" disabled=${saving}>${saving?"Saving…":isEdit?"Save changes":"Create site"}</button>
          </div>
        </form>`}
    </div>`;
}

// ── Test run form ─────────────────────────────────────────────────────────────

function TestRunForm({ siteId }) {
  const [form, setForm] = useState({ name:"", max_depth:3, max_pages:50 });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const upd = p => setForm(f=>({...f,...p}));

  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true);
    try {
      const run = await api.createRun(siteId, {
        name: form.name.trim()||null,
        max_depth: Number(form.max_depth),
        max_pages: Number(form.max_pages),
      });
      nav(`#/runs/${run.id}`);
    } catch(e) { setError(e.message); setSaving(false); }
  };

  return html`
    <div className="topbar">
      <div className="topbar-title">
        <a href=${`#/sites/${siteId}`} style=${{color:"var(--muted)",fontWeight:400}}>Site</a>
        <span className="breadcrumb-sep"> / </span>New test run
      </div>
    </div>
    <div className="content">
      <form className="card" onSubmit=${onSubmit}>
        ${error && html`<div className="alert error">${error}</div>`}
        <div className="form-section-title">Run Configuration</div>
        <div className="field">
          <label>Name <span className="field-optional">(optional — auto-generated if blank)</span></label>
          <input type="text" value=${form.name} placeholder="e.g. Initial crawl" onChange=${e=>upd({name:e.target.value})}/>
        </div>
        <div className="two-col">
          <div className="field">
            <label>Max depth <span className="field-hint-inline">(1–10)</span></label>
            <input type="number" required min="1" max="10" value=${form.max_depth} onChange=${e=>upd({max_depth:e.target.value})}/>
          </div>
          <div className="field">
            <label>Max pages <span className="field-hint-inline">(5–500)</span></label>
            <input type="number" required min="5" max="500" value=${form.max_pages} onChange=${e=>upd({max_pages:e.target.value})}/>
          </div>
        </div>
        <div className="divider"/>
        <div className="row spread">
          <button type="button" className="btn ghost" onClick=${()=>nav(`#/sites/${siteId}`)}>Cancel</button>
          <button type="submit" className="btn" disabled=${saving}>${saving?"Creating…":"Create run"}</button>
        </div>
      </form>
    </div>`;
}

// ── Test run detail + D3 graph ────────────────────────────────────────────────

const SCOPE_IN_COLOR  = "#3b82f6";
const SCOPE_OUT_COLOR = "#ef4444";
const scopeColor = (d) => d.in_scope === false ? SCOPE_OUT_COLOR : SCOPE_IN_COLOR;

const SCAN_COLORS = { pending: "#ef4444", running: "#eab308", complete: "#3b82f6" };
const scanColor = (d) => SCAN_COLORS[d.scan_status] || SCAN_COLORS.pending;

function TestRunDetail({ runId }) {
  const [run, setRun]           = useState(null);
  const [graph, setGraph]       = useState(null);
  const [selectedNode, setSelNode] = useState(null);
  const [pageDetail, setPageDetail] = useState(null);
  const [cascade, setCascade]     = useState(false);
  const [scopeBusy, setScopeBusy] = useState(false);
  const [activeTab, setActiveTab] = useState("sitemap");
  const [editingSettings, setEditingSettings] = useState(false);
  const [editDepth, setEditDepth] = useState("");
  const [editPages, setEditPages] = useState("");
  const [scanStatus, setScanStatus]         = useState(null);
  const [findings, setFindings]             = useState([]);
  const [expandedFinding, setExpandedFinding] = useState(null);
  const [traffic, setTraffic]               = useState([]);
  const [selectedTraffic, setSelectedTraffic] = useState(null);
  const [trafficFilter, setTrafficFilter]   = useState("");
  const [autoScroll, setAutoScroll]         = useState(true);
  const [trafficSort, setTrafficSort]       = useState({ field: "_seq", dir: "asc" });
  const lastTrafficIdRef                    = useRef(0);
  const trafficTableRef                     = useRef(null);
  const [error, setError]       = useState(null);
  const svgRef                  = useRef(null);
  const simRef                  = useRef(null);
  const prevGraphKeyRef                     = useRef("");

  // Initial load
  const loadAll = useCallback(async () => {
    try {
      const [r, g] = await Promise.all([api.getRun(runId), api.getGraph(runId)]);
      setRun(r); setGraph(g);
    } catch(e) { setError(e.message); }
  }, [runId]);
  useEffect(() => { loadAll(); }, [loadAll]);

  // SSE: receive incremental graph + status updates — no graph polling needed
  useEffect(() => {
    const es = new EventSource(`/api/test-runs/${runId}/events`);
    es.onmessage = (msg) => {
      let evt;
      try { evt = JSON.parse(msg.data); } catch { return; }

      if (evt.type === "page_added") {
        setGraph(prev => {
          if (!prev) return prev;
          const exists = prev.nodes.some(n => n.id === evt.node.id);
          if (exists) return prev;
          const newLinks = evt.link ? [...prev.links, evt.link] : prev.links;
          return { nodes: [...prev.nodes, evt.node], links: newLinks };
        });
      } else if (evt.type === "run_update") {
        setRun(prev => prev ? { ...prev, ...evt } : prev);
      } else if (evt.type === "node_scan_status") {
        setGraph(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            nodes: prev.nodes.map(n =>
              n.id === evt.page_id ? { ...n, scan_status: evt.scan_status } : n
            ),
          };
        });
      } else if (evt.type === "scan_update") {
        setScanStatus(evt);
      }
    };
    es.onerror = () => { /* auto-reconnects */ };
    return () => es.close();
  }, [runId]);

  // Lightweight fallback poll: run metadata only (no graph fetch)
  useEffect(() => {
    if (run?.status !== "running") return;
    const iv = setInterval(() => {
      api.getRun(runId).then(r => setRun(r)).catch(() => {});
    }, 5000);
    return () => clearInterval(iv);
  }, [run?.status, runId]);

  // Poll findings while scan is running or on findings tab
  useEffect(() => {
    const needsFindings = scanStatus?.status === "running" || activeTab === "findings";
    if (!needsFindings) return;
    const poll = () => {
      api.getFindings(runId).then(setFindings).catch(() => {});
      if (!scanStatus) api.getScanStatus(runId).then(setScanStatus).catch(() => {});
    };
    poll();
    const iv = setInterval(poll, 4000);
    return () => clearInterval(iv);
  }, [runId, scanStatus?.status, activeTab]);

  // Fetch findings when switching to findings tab
  useEffect(() => {
    if (activeTab !== "findings") return;
    api.getFindings(runId).then(setFindings).catch(()=>{});
    api.getScanStatus(runId).then(setScanStatus).catch(()=>{});
  }, [activeTab, runId]);

  // Traffic log polling — always active while crawling or scanning; also when on the tab
  useEffect(() => {
    const poll = async () => {
      try {
        const entries = await api.getTraffic(runId, lastTrafficIdRef.current);
        if (entries.length > 0) {
          lastTrafficIdRef.current = entries[entries.length - 1].id;
          setTraffic(prev => {
            const base = prev.length;
            const stamped = entries.map((e, i) => ({ ...e, _seq: base + i + 1 }));
            const next = [...prev, ...stamped];
            return next.length > 2000 ? next.slice(-2000) : next;
          });
        }
      } catch(_) {}
    };
    const isActive = (
      activeTab === "traffic" ||
      run?.status === "running" ||
      scanStatus?.status === "running"
    );
    if (!isActive) return;
    poll();
    const iv = setInterval(poll, 2000);
    return () => clearInterval(iv);
  }, [activeTab, run?.status, scanStatus?.status, runId]);

  // Auto-scroll traffic table to bottom when new entries arrive
  useEffect(() => {
    if (!autoScroll || activeTab !== "traffic" || !trafficTableRef.current) return;
    trafficTableRef.current.scrollTop = trafficTableRef.current.scrollHeight;
  }, [traffic.length, activeTab, autoScroll]);

  // Fetch page detail when node selected
  useEffect(() => {
    if (!selectedNode) { setPageDetail(null); return; }
    api.getPage(runId, selectedNode.id).then(setPageDetail).catch(()=>{});
  }, [selectedNode, runId]);

  // D3 force graph
  useEffect(() => {
    if (!graph || !svgRef.current) return;

    const isScan = activeTab === "scan";
    const visibleNodes = isScan ? graph.nodes.filter(n => n.in_scope !== false) : graph.nodes;
    const structureKey = `${activeTab}:${visibleNodes.length}:${graph.links.length}`;

    // Status-only change (same nodes/links, just colour updates) — update in-place.
    if (structureKey === prevGraphKeyRef.current && simRef.current) {
      const simNodes = simRef.current.nodes();
      graph.nodes.forEach(updated => {
        const sn = simNodes.find(n => n.id === updated.id);
        if (sn) Object.assign(sn, updated);
      });
      d3.select(svgRef.current).selectAll("circle")
        .filter(d => d && d.id != null)
        .attr("fill", d => isScan ? scanColor(d) : scopeColor(d));
      return;
    }

    prevGraphKeyRef.current = structureKey;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const W = svgRef.current.clientWidth || 800;
    const H = svgRef.current.clientHeight || 500;

    const inScopeIds = isScan
      ? new Set(graph.nodes.filter(n => n.in_scope !== false).map(n => n.id))
      : null;

    const nodes = (isScan ? graph.nodes.filter(n => n.in_scope !== false) : graph.nodes)
      .map(n => ({...n}));
    const links = (isScan
      ? graph.links.filter(l => inScopeIds.has(l.source) && inScopeIds.has(l.target))
      : graph.links
    ).map(l => ({...l}));

    const zoom = d3.zoom().scaleExtent([0.2, 4]).on("zoom", e => g.attr("transform", e.transform));
    svg.call(zoom);

    const g = svg.append("g");

    // Arrow marker
    svg.append("defs").append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -4 8 8")
      .attr("refX", 18).attr("refY", 0)
      .attr("markerWidth", 6).attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path").attr("d", "M0,-4L8,0L0,4").attr("fill", "var(--border-2)");

    const link = g.append("g").selectAll("line")
      .data(links).join("line")
      .attr("stroke", "var(--border-2)")
      .attr("stroke-width", 1.5)
      .attr("marker-end", "url(#arrow)");

    const node = g.append("g").selectAll("g")
      .data(nodes).join("g")
      .attr("cursor", "pointer")
      .call(d3.drag()
        .on("start", (e,d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
        .on("drag",  (e,d) => { d.fx=e.x; d.fy=e.y; })
        .on("end",   (e,d) => { if (!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }))
      .on("click", (e, d) => { e.stopPropagation(); setSelNode(d); });

    node.append("circle")
      .attr("r", 10)
      .attr("fill", d => isScan ? scanColor(d) : scopeColor(d))
      .attr("stroke", d => d.status === "failed" ? "#fbbf24" : "var(--bg)")
      .attr("stroke-width", 2);

    const rootNode = nodes.find(n => n.depth === 0);
    let baseHost = null;
    try { if (rootNode) baseHost = new URL(rootNode.url).host; } catch {}

    node.append("text")
      .attr("dy", 22).attr("text-anchor", "middle")
      .attr("fill", "var(--muted)")
      .attr("font-size", "10px")
      .attr("pointer-events", "none")
      .text(d => {
        try {
          const u = new URL(d.url);
          const label = u.host === baseHost
            ? (u.pathname + u.search + u.hash || "/")
            : d.url;
          return label.length > 36 ? label.slice(0, 35) + "…" : label;
        } catch { return truncUrl(d.url, 36); }
      });

    // Tooltip on hover
    node.append("title").text(d => d.url);

    svg.on("click", () => setSelNode(null));

    const sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d=>d.id).distance(110).strength(0.8))
      .force("charge", d3.forceManyBody().strength(-350))
      .force("center", d3.forceCenter(W/2, H/2))
      .force("collision", d3.forceCollide(22))
      .on("tick", () => {
        link
          .attr("x1", d=>d.source.x).attr("y1", d=>d.source.y)
          .attr("x2", d=>d.target.x).attr("y2", d=>d.target.y);
        node.attr("transform", d=>`translate(${d.x},${d.y})`);
      });

    simRef.current = sim;
    return () => sim.stop();
  }, [graph, activeTab]);

  // Highlight the node whose URL is currently being crawled.
  // Runs after the D3 graph effect so the SVG is already populated.
  useEffect(() => {
    if (!svgRef.current || !graph) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll(".node-crawl-pulse").remove();
    if (!run?.current_url) return;
    const cur = run.current_url.replace(/\/$/, "");
    svg.select("g").selectAll("g")
      .filter(d => d && d.url && d.url.replace(/\/$/, "") === cur)
      .insert("circle", ":first-child")
        .attr("class", "node-crawl-pulse")
        .attr("r", 10);
  }, [run?.current_url, graph]);

  // ── Traffic helpers ────────────────────────────────────────────────────────
  const fmtRequest = (e) => {
    if (!e) return "";
    const u = new URL(e.url);
    const path = u.pathname + u.search;
    const hdrs = Object.entries(e.request_headers||{})
      .map(([k,v])=>`${k}: ${v}`).join("\n");
    return `${e.method} ${path} HTTP/1.1\nHost: ${u.host}\n${hdrs}${e.request_body?"\n\n"+e.request_body:""}`;
  };
  const fmtResponse = (e) => {
    if (!e) return "";
    const hdrs = Object.entries(e.response_headers||{})
      .map(([k,v])=>`${k}: ${v}`).join("\n");
    return `HTTP/1.1 ${e.status??""}\n${hdrs}${e.response_body?"\n\n"+e.response_body:""}`;
  };
  const statusClass = (s) => !s ? "" : s<300 ? "tr-2xx" : s<400 ? "tr-3xx" : s<500 ? "tr-4xx" : "tr-5xx";
  const filteredTraffic = (() => {
    let list = trafficFilter
      ? traffic.filter(e =>
          e.url.toLowerCase().includes(trafficFilter.toLowerCase()) ||
          (e.method||"").toLowerCase().includes(trafficFilter.toLowerCase()) ||
          String(e.status||"").includes(trafficFilter) ||
          (e.source||"").toLowerCase().includes(trafficFilter.toLowerCase()))
      : traffic;
    const { field, dir } = trafficSort;
    const mul = dir === "asc" ? 1 : -1;
    const numeric = new Set(["_seq", "status", "duration_ms", "id"]);
    list = [...list].sort((a, b) => {
      let av = a[field], bv = b[field];
      if (numeric.has(field)) {
        av = av ?? -1; bv = bv ?? -1;
        return (av - bv) * mul;
      }
      return String(av ?? "").localeCompare(String(bv ?? "")) * mul;
    });
    return list;
  })();
  const onTrafficSort = (field) => setTrafficSort(prev =>
    prev.field === field ? { field, dir: prev.dir === "asc" ? "desc" : "asc" } : { field, dir: "asc" }
  );
  const sortArrow = (field) => trafficSort.field === field
    ? html`<span className="sort-arrow">${trafficSort.dir === "asc" ? "▲" : "▼"}</span>` : "";
  const fmtTs = (iso) => { try { const d = new Date(iso); return d.toTimeString().slice(0,8)+"."+String(d.getMilliseconds()).padStart(3,"0"); } catch { return iso||""; } };

  const onStartScan = async () => {
    try {
      const s = await api.startScan(runId);
      setScanStatus(s);
    } catch(e) { setError(e.message); }
  };

  const onScanPage = async () => {
    if (!selectedNode || scopeBusy) return;
    setScopeBusy(true);
    try {
      const s = await api.scanPage(runId, selectedNode.id);
      setScanStatus(s);
    } catch(e) { setError(e.message); } finally { setScopeBusy(false); }
  };
  const onDeleteFinding = async (e, findingId) => {
    e.stopPropagation();
    try {
      await api.deleteFinding(runId, findingId);
      setFindings(prev => prev.filter(f => f.id !== findingId));
      if (expandedFinding === findingId) setExpandedFinding(null);
    } catch(err) { setError(err.message); }
  };

  const onStopScan = async () => {
    try {
      const s = await api.stopScan(runId);
      setScanStatus(s);
    } catch(e) { setError(e.message); }
  };

  const onEditSettings = () => {
    setEditDepth(String(run.max_depth));
    setEditPages(String(run.max_pages));
    setEditingSettings(true);
  };
  const onSaveSettings = async () => {
    const d = parseInt(editDepth, 10);
    const p = parseInt(editPages, 10);
    if (!d || !p || d < 1 || d > 10 || p < 5 || p > 500) return;
    try {
      const r = await api.updateRun(runId, { max_depth: d, max_pages: p });
      setRun(r);
      setEditingSettings(false);
    } catch(e) { setError(e.message); }
  };

  const onToggleScope = async () => {
    if (!selectedNode || scopeBusy) return;
    setScopeBusy(true);
    const newScope = selectedNode.in_scope === false ? true : false;
    try {
      await api.setPageScope(runId, selectedNode.id, { in_scope: newScope, cascade });
      const g = await api.getGraph(runId);
      setGraph(g);
      const updated = g.nodes.find(n => n.id === selectedNode.id);
      if (updated) setSelNode(updated);
    } catch(e) { setError(e.message); } finally { setScopeBusy(false); }
  };

  const onDeleteNode = async () => {
    if (!selectedNode || scopeBusy) return;
    setScopeBusy(true);
    try {
      await api.deletePage(runId, selectedNode.id, cascade);
      const g = await api.getGraph(runId);
      setGraph(g);
      setSelNode(null);
    } catch(e) { setError(e.message); } finally { setScopeBusy(false); }
  };

  const onStart = async () => {
    try {
      const r = await api.startRun(runId);
      // Optimistically mark as running so the poll interval starts immediately.
      setRun({...r, status: "running"});
    } catch(e) { setError(e.message); }
  };
  const onStop = async () => {
    try { const r = await api.stopRun(runId); setRun(r); } catch(e) { setError(e.message); }
  };
  const onRestart = async () => {
    if (!confirm("Delete all crawled pages for this run and start fresh?")) return;
    try {
      setGraph({nodes:[], links:[]});
      const r = await api.restartRun(runId);
      // Optimistically mark as running so the poll interval starts immediately
      // and the empty-graph "Start crawl" button disappears.
      setRun({...r, status: "running"});
    } catch(e) { setError(e.message); }
  };

  const STATUS_COLOR = { pending:"var(--muted)", running:"var(--warn)", complete:"var(--ok)", failed:"var(--danger)", stopped:"var(--muted)" };
  const canStart   = run && ["pending","stopped","failed","complete"].includes(run.status);
  const canRestart = run && ["stopped","failed","complete"].includes(run.status);
  const canStop    = run?.status === "running";

  return html`
    <div className="topbar">
      <div className="topbar-title">
        <a href=${run?`#/sites/${run.site_id}`:"#/"} style=${{color:"var(--muted)",fontWeight:400}}>Site</a>
        <span className="breadcrumb-sep"> / </span>
        ${run ? run.name : "…"}
        ${run && html`<span className=${"run-status-badge"+(run.status==="running"?" running":"")} style=${{color:STATUS_COLOR[run.status]||"var(--muted)"}}>● ${run.status}</span>`}
      </div>
      <div className="topbar-actions">
        ${canStop && html`<button className="btn danger-outline" onClick=${onStop}><${IconStop}/> Stop</button>`}
      </div>
    </div>

    <div className="content" style=${{paddingBottom:0,display:"flex",flexDirection:"column",flex:1,minHeight:0}}>
      ${error && html`<div className="alert error" style=${{marginBottom:12}}>${error}</div>`}

      <div className="tab-bar">
        <button className=${"tab-btn"+(activeTab==="sitemap"?" active":"")}
          onClick=${()=>{ setActiveTab("sitemap"); setSelNode(null); }}>Site Map</button>
        <button className=${"tab-btn"+(activeTab==="scan"?" active":"")}
          onClick=${()=>{ setActiveTab("scan"); setSelNode(null); }}>Scan Status</button>
        <button className=${"tab-btn"+(activeTab==="findings"?" active":"")}
          onClick=${()=>{ setActiveTab("findings"); setSelNode(null); }}>
          Findings${findings.length>0?html` <span className="findings-badge">${findings.length}</span>`:""}
        </button>
        <button className=${"tab-btn"+(activeTab==="traffic"?" active":"")}
          onClick=${()=>{ setActiveTab("traffic"); setSelNode(null); }}>
          Traffic Log${traffic.length>0?html` <span className="traffic-count">${traffic.length}</span>`:""}
        </button>
        <div style=${{flex:1}}></div>
        ${activeTab==="sitemap" && canStart   && html`<button className="btn sm" style=${{margin:"auto 4px auto 0"}} onClick=${onStart}><${IconPlay}/> Start crawl</button>`}
        ${activeTab==="sitemap" && canRestart && html`<button className="btn danger-outline sm" style=${{margin:"auto 8px auto 0"}} onClick=${onRestart}>↺ Clear & restart</button>`}
        ${activeTab==="scan" && scanStatus?.status==="running" && html`
          <button className="btn danger-outline sm" style=${{margin:"auto 4px auto 0"}} onClick=${onStopScan}>◼ Stop scan</button>`}
        ${activeTab==="scan" && (scanStatus?.status==="idle"||scanStatus?.status==="complete"||scanStatus?.status==="stopped"||scanStatus?.status==null) && run?.status!=="running" && html`
          <button className="btn sm" style=${{margin:"auto 4px auto 0"}} onClick=${onStartScan}><${IconPlay}/> Start scan</button>`}
      </div>

      ${(activeTab==="sitemap"||activeTab==="scan") && run && html`
        <div className="run-meta">
          <div className="run-stat"><span className="run-stat-val">${run.pages_discovered}</span><span className="run-stat-lbl">Pages found</span></div>
          ${editingSettings ? html`
            <div className="run-stat-edit">
              <div className="run-stat-edit-field">
                <label>Max depth</label>
                <input type="number" min="1" max="10" value=${editDepth}
                  onInput=${e=>setEditDepth(e.target.value)} style=${{width:54}}/>
              </div>
              <div className="run-stat-edit-field">
                <label>Max pages</label>
                <input type="number" min="5" max="500" value=${editPages}
                  onInput=${e=>setEditPages(e.target.value)} style=${{width:64}}/>
              </div>
              <div style=${{display:"flex",gap:6,alignItems:"center"}}>
                <button className="btn sm" onClick=${onSaveSettings}>Save</button>
                <button className="btn ghost sm" onClick=${()=>setEditingSettings(false)}>Cancel</button>
              </div>
            </div>
          ` : html`
            <div className="run-stat">
              <span className="run-stat-val">${run.max_depth}</span>
              <span className="run-stat-lbl">Max depth</span>
            </div>
            <div className="run-stat">
              <span className="run-stat-val">${run.max_pages}</span>
              <span className="run-stat-lbl">Max pages</span>
            </div>
            ${run.status !== "running" && html`
              <button className="btn ghost sm" style=${{alignSelf:"center",marginLeft:4}}
                title="Edit depth / pages" onClick=${onEditSettings}>✎</button>`}
          `}
          ${run.current_url&&html`<div className="run-stat run-stat-url"><span className="run-stat-lbl">Crawling</span><span className="mono run-stat-url-val">${truncUrl(run.current_url,50)}</span></div>`}
          ${run.error_message&&html`<div style=${{color:"var(--danger)",fontSize:12,flex:1}}>${run.error_message}</div>`}
        </div>
        ${run.status==="running" && html`
          <div className="crawl-progress-bar">
            <div className="crawl-progress-fill" style=${{width: Math.min(100, run.pages_discovered / run.max_pages * 100) + "%"}}></div>
          </div>`}`}

      <div className="graph-layout" style=${{display: (activeTab==="findings"||activeTab==="traffic") ? "none" : "flex"}}>
        <div className="graph-canvas-wrap">
          ${graph&&graph.nodes.length===0 && html`
            <div className="graph-empty">
              ${activeTab==="sitemap" && run?.status==="pending"
                ? html`<div style=${{display:"flex",flexDirection:"column",alignItems:"center",gap:12}}>
                    <span>Ready to crawl.</span>
                    <button className="btn" onClick=${onStart}><${IconPlay}/> Start crawl</button>
                  </div>`
                : html`<span>No pages discovered yet.</span>`}
            </div>`}
          <svg ref=${svgRef} className="graph-svg" width="100%" height="100%"></svg>
          ${graph&&graph.nodes.length>0 && html`
            <div className="graph-legend">
              ${activeTab === "sitemap" ? html`
                <div className="legend-item"><span className="legend-dot" style=${{background:SCOPE_IN_COLOR}}></span>In Scope</div>
                <div className="legend-item"><span className="legend-dot" style=${{background:SCOPE_OUT_COLOR}}></span>Out of Scope</div>
                <div className="legend-item"><span className="legend-dot" style=${{background:"var(--bg)",border:"2px solid #fbbf24"}}></span>Failed</div>
              ` : html`
                <div className="legend-item"><span className="legend-dot" style=${{background:SCAN_COLORS.pending}}></span>Not scanned</div>
                <div className="legend-item"><span className="legend-dot" style=${{background:SCAN_COLORS.running}}></span>Scanning…</div>
                <div className="legend-item"><span className="legend-dot" style=${{background:SCAN_COLORS.complete}}></span>Complete</div>
              `}
            </div>`}
        </div>

        ${selectedNode && html`
          <div className="graph-panel">
            <div className="graph-panel-header">
              <div className="graph-panel-url">${selectedNode.url}</div>
              <button className="btn ghost sm" onClick=${()=>setSelNode(null)}>✕</button>
            </div>
            ${pageDetail ? html`
              <div className="graph-panel-body">
                ${pageDetail.title && html`<div className="graph-panel-title">${pageDetail.title}</div>`}

                <div className="graph-panel-section-label">Scope</div>
                <div className="scope-row">
                  <span className=${"scope-badge " + (selectedNode.in_scope === false ? "out" : "in")}>
                    ${selectedNode.in_scope === false ? "Out of Scope" : "In Scope"}
                  </span>
                  <button className="btn sm" onClick=${onToggleScope} disabled=${scopeBusy}>
                    ${scopeBusy ? "…" : (selectedNode.in_scope === false ? "Mark in scope" : "Mark out of scope")}
                  </button>
                  <button className="btn danger-outline sm" onClick=${onDeleteNode} disabled=${scopeBusy}
                    title="Delete this node (and children if checkbox is ticked)">🗑</button>
                </div>
                ${activeTab==="scan" && selectedNode.in_scope !== false && html`
                  <div style=${{marginTop:10}}>
                    <button className="btn sm" onClick=${onScanPage} disabled=${scopeBusy||scanStatus?.status==="running"}>
                      ${scopeBusy ? "Starting…" : scanStatus?.status==="running" ? "Scan running…" : "▶ Scan this page"}
                    </button>
                    ${selectedNode.scan_status && html`
                      <span className=${"scan-node-status scan-node-"+selectedNode.scan_status}>
                        ${selectedNode.scan_status}
                      </span>`}
                  </div>`}
                <label className="scope-cascade-label">
                  <input type="checkbox" checked=${cascade} onChange=${e=>setCascade(e.target.checked)}/>
                  Also apply to all children
                </label>

                <div className="graph-panel-section-label" style=${{marginTop:14}}>Page Categories</div>
                <div className="page-cats">
                  ${[
                    ["req_auth",          "Auth Required"],
                    ["takes_input",       "Takes Input"],
                    ["has_object_ref",    "Object Reference"],
                    ["has_business_logic","Business Logic"],
                  ].map(([key, label]) => {
                    const val = pageDetail[key];
                    const cls = val === true ? "cat-yes" : val === false ? "cat-no" : "cat-unknown";
                    const badge = val === true ? "Yes" : val === false ? "No" : "?";
                    return html`<div key=${key} className="cat-row">
                      <span className="cat-label">${label}</span>
                      <span className=${"cat-badge " + cls}>${badge}</span>
                    </div>`;
                  })}
                </div>

                <div className="graph-panel-section-label" style=${{marginTop:14}}>LLM Context</div>
                <div className="graph-panel-context">${pageDetail.llm_context || "No context available."}</div>
                ${pageDetail.screenshot_b64 && html`
                  <div className="graph-panel-section-label" style=${{marginTop:12}}>Screenshot</div>
                  <img src=${`data:image/png;base64,${pageDetail.screenshot_b64}`}
                    style=${{width:"100%",borderRadius:6,border:"1px solid var(--border)"}} alt="screenshot"/>`}
              </div>` : html`<div className="subtle" style=${{padding:12}}>Loading…</div>`}
          </div>`}
      </div>

      ${activeTab==="findings" && html`
        <div className="findings-panel">
          ${scanStatus && html`
            <div className="findings-status-bar">
              <span className=${"scan-status-badge scan-status-"+scanStatus.status}>
                ${scanStatus.status==="running" ? "Scanning…" :
                  scanStatus.status==="complete" ? "Scan complete" :
                  scanStatus.status==="stopped"  ? "Scan stopped" :
                  scanStatus.status==="failed"   ? "Scan failed"  : "Not scanned"}
              </span>
              ${scanStatus.status==="running" && html`
                <span className="subtle" style=${{fontSize:12}}>
                  ${scanStatus.pages_done} / ${scanStatus.total_pages} pages
                </span>`}
            </div>`}
          ${findings.length === 0
            ? html`<div className="subtle" style=${{padding:24,textAlign:"center"}}>
                ${scanStatus?.status==="running" ? "Scanning… findings will appear here." : "No findings yet. Start a scan from the Scan Status tab."}
              </div>`
            : html`
              <div className="findings-table-wrap">
                <table className="findings-table">
                  <thead>
                    <tr>
                      <th>Severity</th>
                      <th>OWASP</th>
                      <th>Title</th>
                      <th>URL</th>
                      <th style=${{width:36}}></th>
                    </tr>
                  </thead>
                  <tbody>
                    ${findings.map(f => html`
                      <tr key=${f.id} className="finding-row"
                        onClick=${()=>setExpandedFinding(expandedFinding===f.id?null:f.id)}>
                        <td><span className=${"sev-badge sev-"+f.severity}>${f.severity}</span></td>
                        <td><span className="owasp-badge">${f.owasp_category}</span></td>
                        <td className="finding-title">${f.title}</td>
                        <td className="finding-url mono" title=${f.affected_url}>${truncUrl(f.affected_url||"",48)}</td>
                        <td><button className="btn ghost sm finding-del-btn" title="Delete finding"
                          onClick=${e=>onDeleteFinding(e,f.id)}>🗑</button></td>
                      </tr>
                      ${expandedFinding===f.id && html`
                        <tr key=${"ev-"+f.id} className="finding-evidence-row">
                          <td colSpan="4">
                            <div className="finding-description">${f.description}</div>
                            ${f.affected_url && html`
                              <div className="finding-affected-url">
                                <span className="finding-affected-label">Affected URL</span>
                                <span className="mono">${f.affected_url}</span>
                              </div>`}
                            ${f.evidence && html`<pre className="finding-evidence">${f.evidence}</pre>`}
                            ${f.screenshot_b64 && html`
                              <div className="finding-screenshot-wrap">
                                <div className="finding-affected-label">Screenshot</div>
                                <img src=${"data:image/png;base64,"+f.screenshot_b64}
                                  className="finding-screenshot" alt="proof screenshot"/>
                              </div>`}
                          </td>
                        </tr>`}
                    `)}
                  </tbody>
                </table>
              </div>`}
        </div>`}
      ${activeTab==="traffic" && html`
        <div className="traffic-panel">
          <div className="traffic-toolbar">
            <input className="traffic-filter" type="text" placeholder="Filter by URL, method or status…"
              value=${trafficFilter} onInput=${e=>setTrafficFilter(e.target.value)}/>
            <span className="traffic-count-label">${filteredTraffic.length} request${filteredTraffic.length!==1?"s":""}</span>
            <label className="traffic-autoscroll">
              <input type="checkbox" checked=${autoScroll} onChange=${e=>setAutoScroll(e.target.checked)}/>
              Auto-scroll
            </label>
            <button className="btn ghost sm" onClick=${()=>{ setTraffic([]); lastTrafficIdRef.current=0; setSelectedTraffic(null); }}>Clear</button>
          </div>

          <div className="traffic-table-wrap" ref=${trafficTableRef}>
            <table className="traffic-table">
              <thead>
                <tr>
                  <th className="sortable tr-num" onClick=${()=>onTrafficSort("_seq")}>#${sortArrow("_seq")}</th>
                  <th className="sortable tr-ts"  onClick=${()=>onTrafficSort("created_at")}>Time${sortArrow("created_at")}</th>
                  <th className="sortable" style=${{width:80}} onClick=${()=>onTrafficSort("source")}>Source${sortArrow("source")}</th>
                  <th className="sortable" style=${{width:60}} onClick=${()=>onTrafficSort("method")}>Method${sortArrow("method")}</th>
                  <th className="sortable" style=${{width:54}} onClick=${()=>onTrafficSort("status")}>Status${sortArrow("status")}</th>
                  <th className="sortable" onClick=${()=>onTrafficSort("url")}>URL${sortArrow("url")}</th>
                  <th className="sortable tr-dur" onClick=${()=>onTrafficSort("duration_ms")}>Duration${sortArrow("duration_ms")}</th>
                </tr>
              </thead>
              <tbody>
                ${filteredTraffic.map((e,i) => html`
                  <tr key=${e.id}
                    className=${"traffic-row"+(selectedTraffic?.id===e.id?" selected":"")}
                    onClick=${()=>setSelectedTraffic(selectedTraffic?.id===e.id?null:e)}>
                    <td className="tr-num">${e._seq??i+1}</td>
                    <td className="tr-ts">${fmtTs(e.created_at)}</td>
                    <td><span className=${"src-badge src-"+e.source}>${e.source}</span></td>
                    <td className="tr-method">${e.method}</td>
                    <td><span className=${"status-pill "+statusClass(e.status)}>${e.status??"-"}</span></td>
                    <td className="tr-url" title=${e.url}>${e.url}</td>
                    <td className="tr-dur">${e.duration_ms!=null?e.duration_ms+"ms":"-"}</td>
                  </tr>`)}
              </tbody>
            </table>
            ${filteredTraffic.length===0 && html`
              <div className="subtle" style=${{padding:"24px",textAlign:"center"}}>
                ${run?.status==="running"||scanStatus?.status==="running"
                  ? "Capturing traffic…" : "No traffic recorded yet. Start a crawl or scan."}
              </div>`}
          </div>

          ${selectedTraffic && html`
            <div className="traffic-detail">
              <div className="traffic-pane">
                <div className="traffic-pane-label">REQUEST — ${selectedTraffic.method} ${selectedTraffic.url}</div>
                <pre className="traffic-raw">${fmtRequest(selectedTraffic)}</pre>
              </div>
              <div className="traffic-pane">
                <div className="traffic-pane-label">RESPONSE — ${selectedTraffic.status??"-"} ${selectedTraffic.duration_ms!=null?"("+selectedTraffic.duration_ms+"ms)":""}</div>
                <pre className="traffic-raw">${fmtResponse(selectedTraffic)}</pre>
              </div>
            </div>`}
        </div>`}
    </div>`;
}

// ── Settings ──────────────────────────────────────────────────────────────────

const PROVIDER_LABELS = { anthropic:"Anthropic", openai:"OpenAI", openai_compatible:"OpenAI-compatible (LM Studio, Ollama, etc.)", google:"Google Gemini" };
const PROVIDER_PLACEHOLDERS = { anthropic:"claude-opus-4-5", openai:"gpt-4o", openai_compatible:"e.g. llama-3.1-8b-instruct", google:"gemini-2.5-flash-preview-04-17" };

function SettingsPage() {
  const [form, setForm]     = useState(null);
  const [dms, setDMs]       = useState({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved]   = useState(false);
  const [error, setError]   = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [cfg,dm] = await Promise.all([api.getLLMConfig(), api.getDefaultModels()]);
        setDMs(dm);
        setForm(cfg ? {
          provider:cfg.provider, api_key:cfg.api_key??"", base_url:cfg.base_url??"",
          model:cfg.model, max_tokens:cfg.max_tokens, temperature:cfg.temperature,
          use_vision:cfg.use_vision??false,
        } : { provider:"anthropic", api_key:"", base_url:"", model:"claude-opus-4-5", max_tokens:4096, temperature:0, use_vision:false });
      } catch(e) { setError(e.message); }
    })();
  }, []);

  const upd = p => { setSaved(false); setForm(f=>({...f,...p})); };
  const changeProv = p => { const ms=dms[p]||[]; upd({provider:p,model:ms[0]||"",api_key:"",base_url:""}); };

  const onSubmit = async (e) => {
    e.preventDefault(); setError(null); setSaving(true); setSaved(false);
    const payload = {
      provider:form.provider, api_key:form.api_key.trim()||null,
      base_url:form.provider==="openai_compatible"?form.base_url.trim():null,
      model:form.model.trim(), max_tokens:Number(form.max_tokens),
      temperature:Number(form.temperature), use_vision:form.use_vision,
    };
    try { await api.upsertLLMConfig(payload); setSaved(true); }
    catch(e) { setError(e.message); } finally { setSaving(false); }
  };

  const models = form?(dms[form.provider]||[]):[];
  const isCustom = form&&models.length>0&&!models.includes(form.model)&&form.model!=="";

  return html`
    <div className="topbar"><div className="topbar-title">LLM Settings</div></div>
    <div className="content">
      ${!form&&!error&&html`<div className="subtle">Loading…</div>`}
      ${error&&html`<div className="alert error">${error}</div>`}
      ${form&&html`
        <form className="card" onSubmit=${onSubmit}>
          <div className="form-section-title">Provider</div>
          <div className="provider-grid">
            ${Object.entries(PROVIDER_LABELS).map(([k,lbl])=>html`
              <label key=${k} className=${"provider-card"+(form.provider===k?" selected":"")}>
                <input type="radio" name="provider" value=${k} checked=${form.provider===k} onChange=${()=>changeProv(k)}/>
                <span className="provider-name">${lbl}</span>
              </label>`)}
          </div>
          <div className="divider"/>
          <div className="form-section-title">${PROVIDER_LABELS[form.provider]} Configuration</div>
          ${(form.provider==="anthropic"||form.provider==="openai")&&html`
            <div className="field"><label>API Key</label>
              <input type="password" required value=${form.api_key} placeholder=${form.provider==="anthropic"?"sk-ant-…":"sk-…"}
                onChange=${e=>upd({api_key:e.target.value})}/></div>`}
          ${form.provider==="openai_compatible"&&html`
            <div className="field"><label>Base URL</label>
              <input type="url" required value=${form.base_url} placeholder="http://localhost:1234/v1" onChange=${e=>upd({base_url:e.target.value})}/>
              <div className="field-hint">LM Studio: http://localhost:1234/v1 · Ollama: http://localhost:11434/v1</div></div>
            <div className="field"><label>API Key <span className="field-optional">(optional)</span></label>
              <input type="password" value=${form.api_key} placeholder="Leave blank if not required" onChange=${e=>upd({api_key:e.target.value})}/></div>`}
          <div className="field"><label>Model</label>
            ${models.length>0?html`
              <div className="model-select-group">
                <select className="select" value=${isCustom?"__custom__":form.model}
                  onChange=${e=>e.target.value!=="__custom__"?upd({model:e.target.value}):upd({model:""})}>
                  ${models.map(m=>html`<option key=${m} value=${m}>${m}</option>`)}
                  <option value="__custom__">Custom…</option>
                </select>
                ${isCustom&&html`<input type="text" required value=${form.model} placeholder="Model name" onChange=${e=>upd({model:e.target.value})}/>`}
              </div>`:html`
              <input type="text" required value=${form.model} placeholder=${PROVIDER_PLACEHOLDERS[form.provider]}
                onChange=${e=>upd({model:e.target.value})}/>`}
          </div>
          <div className="divider"/>
          <div className="form-section-title">Sampling</div>
          <div className="two-col">
            <div className="field"><label>Max tokens</label>
              <input type="number" required min="1" max="32768" value=${form.max_tokens} onChange=${e=>upd({max_tokens:e.target.value})}/></div>
            <div className="field"><label>Temperature <span className="field-hint-inline">(0–2)</span></label>
              <input type="number" required min="0" max="2" step="0.05" value=${form.temperature} onChange=${e=>upd({temperature:e.target.value})}/></div>
          </div>
          <div className="divider"/>
          <div className="form-section-title">Vision</div>
          <label className="toggle-row">
            <input type="checkbox" checked=${form.use_vision} onChange=${e=>upd({use_vision:e.target.checked})}/>
            <span>Include page screenshots in LLM prompts (requires vision-capable model)</span>
          </label>
          <div className="divider"/>
          <div className="row spread">
            <div>${saved&&html`<span className="save-confirm"><${IconCheck}/> Saved</span>`}</div>
            <button type="submit" className="btn" disabled=${saving}>${saving?"Saving…":"Save settings"}</button>
          </div>
        </form>`}
    </div>`;
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function fmtDate(iso) {
  return iso ? new Date(iso).toLocaleString(undefined, {dateStyle:"short",timeStyle:"short"}) : "—";
}

function truncUrl(url, maxLen=40) {
  try {
    const u = new URL(url);
    const s = u.hostname + u.pathname;
    return s.length > maxLen ? s.slice(0, maxLen-1) + "…" : s;
  } catch { return url.slice(0, maxLen); }
}

createRoot(document.getElementById("root")).render(html`<${App}/>`);
