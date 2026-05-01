import React, { useEffect, useState, useCallback } from "react";
import { createRoot } from "react-dom/client";
import htm from "htm";

const html = htm.bind(React.createElement);

// ---- API client ---------------------------------------------------------

const api = {
  listSites:        ()         => req("/api/sites"),
  getSite:          (id)       => req(`/api/sites/${id}`),
  createSite:       (payload)  => req("/api/sites",       { method: "POST",   body: payload }),
  updateSite:       (id, body) => req(`/api/sites/${id}`,  { method: "PUT",    body }),
  deleteSite:       (id)       => req(`/api/sites/${id}`,  { method: "DELETE" }),
  getLLMConfig:     ()         => req("/api/settings/llm"),
  upsertLLMConfig:  (body)     => req("/api/settings/llm", { method: "PUT",    body }),
  getDefaultModels: ()         => req("/api/settings/llm/models"),
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

function formatError(data) {
  if (!data) return null;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail))
    return data.detail.map((d) => `${(d.loc || []).join(".")}: ${d.msg}`).join("\n");
  return JSON.stringify(data);
}

// ---- Hash router --------------------------------------------------------

function useRoute() {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const cb = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", cb);
    return () => window.removeEventListener("hashchange", cb);
  }, []);
  if (hash === "#/" || hash === "" || hash === "#") return { name: "list" };
  const m = hash.match(/^#\/sites\/(new|\d+)$/);
  if (m) return m[1] === "new" ? { name: "new" } : { name: "edit", id: parseInt(m[1], 10) };
  if (hash === "#/settings") return { name: "settings" };
  return { name: "list" };
}

const navigate = (to) => { window.location.hash = to; };

// ---- Icons --------------------------------------------------------------

const IconSites = () => html`
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <rect x="1" y="1" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
    <rect x="9" y="1" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
    <rect x="1" y="9" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
    <rect x="9" y="9" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
  </svg>
`;

const IconSettings = () => html`
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <circle cx="8" cy="8" r="2.2" stroke="currentColor" stroke-width="1.4"/>
    <path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M2.93 2.93l1.06 1.06M12.01 12.01l1.06 1.06M2.93 13.07l1.06-1.06M12.01 3.99l1.06-1.06" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
  </svg>
`;

const IconPlus = () => html`
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M7 1v12M1 7h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
  </svg>
`;

const IconCheck = () => html`
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M2 7l4 4 6-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
`;

// ---- Layout shell -------------------------------------------------------

function App() {
  const route   = useRoute();
  const onSites = route.name === "list" || route.name === "new" || route.name === "edit";
  const onSettings = route.name === "settings";

  return html`
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="logo">
            <div className="logo-icon">A</div>
            <span className="logo-text">AESPA</span>
          </div>
          <div className="logo-sub">LLM Pentesting Agent</div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-label">Targets</div>
          <a href="#/" className=${"nav-item" + (onSites ? " active" : "")}>
            <span className="nav-icon"><${IconSites} /></span>
            Sites
          </a>

          <div className="nav-section-label" style=${{ marginTop: 8 }}>Configuration</div>
          <a href="#/settings" className=${"nav-item" + (onSettings ? " active" : "")}>
            <span className="nav-icon"><${IconSettings} /></span>
            LLM Settings
          </a>
        </nav>

        <div className="sidebar-footer">v0.1.0</div>
      </aside>

      <div className="main">
        ${route.name === "list"     && html`<${SitesList} />`}
        ${route.name === "new"      && html`<${SiteForm} key="new" />`}
        ${route.name === "edit"     && html`<${SiteForm} key=${route.id} siteId=${route.id} />`}
        ${route.name === "settings" && html`<${SettingsPage} />`}
      </div>
    </div>
  `;
}

// ---- Sites list ---------------------------------------------------------

function SitesList() {
  const [sites, setSites] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try { setSites(await api.listSites()); }
    catch (e) { setError(e.message); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onDelete = async (site) => {
    if (!confirm(`Delete "${site.name}"? This also removes its credentials.`)) return;
    try { await api.deleteSite(site.id); await load(); }
    catch (e) { setError(e.message); }
  };

  const authCount = sites ? sites.filter((s) => s.requires_auth).length : 0;
  const credCount = sites ? sites.reduce((n, s) => n + s.credential_count, 0) : 0;

  return html`
    <div className="topbar">
      <div className="topbar-title">Sites</div>
      <div className="topbar-actions">
        <button className="btn" onClick=${() => navigate("#/sites/new")}>
          <${IconPlus} /> New site
        </button>
      </div>
    </div>

    <div className="content">
      ${error && html`<div className="alert error" style=${{ marginBottom: 16 }}>${error}</div>`}

      ${sites && sites.length > 0 && html`
        <div className="stat-strip">
          <div className="stat">
            <span className="stat-value">${sites.length}</span>
            <span className="stat-label">Sites</span>
          </div>
          <div className="stat">
            <span className="stat-value">${authCount}</span>
            <span className="stat-label">Authenticated</span>
          </div>
          <div className="stat">
            <span className="stat-value">${credCount}</span>
            <span className="stat-label">Credentials</span>
          </div>
        </div>
      `}

      ${sites === null && html`<div className="subtle">Loading…</div>`}

      ${sites !== null && sites.length === 0 && html`
        <div className="empty-state">
          <div className="empty-icon">⬡</div>
          <div className="empty-msg">No sites configured</div>
          <div className="empty-sub">Add a target site to begin setting up your pentest scope.</div>
          <button className="btn" onClick=${() => navigate("#/sites/new")}>
            <${IconPlus} /> New site
          </button>
        </div>
      `}

      ${sites && sites.length > 0 && html`
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th><th>Base URL</th><th>Auth</th><th>Credentials</th><th></th>
              </tr>
            </thead>
            <tbody>
              ${sites.map((s) => html`
                <tr key=${s.id}>
                  <td><strong>${s.name}</strong></td>
                  <td className="url">${s.base_url}</td>
                  <td>
                    ${s.requires_auth
                      ? html`<span className="badge ok">required</span>`
                      : html`<span className="badge neutral">none</span>`}
                  </td>
                  <td>${s.credential_count > 0 ? s.credential_count : html`<span className="subtle">—</span>`}</td>
                  <td>
                    <div className="row" style=${{ justifyContent: "flex-end" }}>
                      <button className="btn secondary sm" onClick=${() => navigate(`#/sites/${s.id}`)}>Edit</button>
                      <button className="btn danger-outline sm" onClick=${() => onDelete(s)}>Delete</button>
                    </div>
                  </td>
                </tr>
              `)}
            </tbody>
          </table>
        </div>
      `}
    </div>
  `;
}

// ---- Site form ----------------------------------------------------------

function emptySite() {
  return { name: "", base_url: "", requires_auth: false, login_url: "", notes: "", credentials: [] };
}

function SiteForm({ siteId }) {
  const isEdit  = typeof siteId === "number";
  const [form, setForm]       = useState(emptySite());
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState(null);

  useEffect(() => {
    if (!isEdit) return;
    (async () => {
      try {
        const data = await api.getSite(siteId);
        setForm({
          name: data.name, base_url: data.base_url,
          requires_auth: data.requires_auth,
          login_url: data.login_url || "",
          notes: data.notes || "",
          credentials: data.credentials.map((c) => ({
            username: c.username, password: c.password, label: c.label || "",
          })),
        });
      } catch (e) { setError(e.message); }
      finally     { setLoading(false); }
    })();
  }, [isEdit, siteId]);

  const update     = (patch) => setForm((f) => ({ ...f, ...patch }));
  const updateCred = (idx, patch) => setForm((f) => ({
    ...f, credentials: f.credentials.map((c, i) => i === idx ? { ...c, ...patch } : c),
  }));
  const addCred    = () => setForm((f) => ({
    ...f, credentials: [...f.credentials, { username: "", password: "", label: "" }],
  }));
  const removeCred = (idx) => setForm((f) => ({
    ...f, credentials: f.credentials.filter((_, i) => i !== idx),
  }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null); setSaving(true);
    const payload = {
      name: form.name.trim(), base_url: form.base_url.trim(),
      requires_auth: form.requires_auth,
      login_url: form.requires_auth ? form.login_url.trim() : null,
      notes: form.notes.trim() || null,
      credentials: form.requires_auth
        ? form.credentials.map((c) => ({ username: c.username, password: c.password, label: c.label || null }))
        : [],
    };
    try {
      if (isEdit) await api.updateSite(siteId, payload);
      else        await api.createSite(payload);
      navigate("#/");
    } catch (e2) { setError(e2.message); }
    finally      { setSaving(false); }
  };

  return html`
    <div className="topbar">
      <div className="topbar-title">
        <a href="#/" style=${{ color: "var(--muted)", fontWeight: 400 }}>Sites</a>
        <span className="breadcrumb-sep"> / </span>
        ${isEdit ? "Edit site" : "New site"}
      </div>
    </div>

    <div className="content">
      ${loading && html`<div className="subtle">Loading…</div>`}
      ${!loading && html`
        <form className="card" onSubmit=${onSubmit}>
          ${error && html`<div className="alert error">${error}</div>`}

          <div className="form-section-title">Site</div>

          <div className="field">
            <label>Name</label>
            <input type="text" required value=${form.name} placeholder="e.g. Juice Shop"
              onChange=${(e) => update({ name: e.target.value })} />
          </div>
          <div className="field">
            <label>Base URL</label>
            <input type="url" required value=${form.base_url} placeholder="https://target.example.com"
              onChange=${(e) => update({ base_url: e.target.value })} />
          </div>
          <div className="field">
            <label>Notes (optional)</label>
            <textarea value=${form.notes} placeholder="Scope, contacts, notes…"
              onChange=${(e) => update({ notes: e.target.value })} />
          </div>

          <div className="divider" />
          <div className="form-section-title">Authentication</div>

          <label className="toggle-row">
            <input type="checkbox" checked=${form.requires_auth}
              onChange=${(e) => update({ requires_auth: e.target.checked })} />
            <span>This site requires authentication</span>
          </label>

          ${form.requires_auth && html`
            <div className="field">
              <label>Login page URL</label>
              <input type="url" required value=${form.login_url}
                placeholder="https://target.example.com/login"
                onChange=${(e) => update({ login_url: e.target.value })} />
            </div>

            <fieldset>
              <legend>Credentials</legend>
              ${form.credentials.length === 0 && html`<div className="subtle">No credentials yet.</div>`}
              ${form.credentials.map((c, idx) => html`
                <div className="cred-row" key=${idx}>
                  <div className="field">
                    <label>Username</label>
                    <input type="text" required value=${c.username}
                      onChange=${(e) => updateCred(idx, { username: e.target.value })} />
                  </div>
                  <div className="field">
                    <label>Password</label>
                    <input type="text" required value=${c.password}
                      onChange=${(e) => updateCred(idx, { password: e.target.value })} />
                  </div>
                  <div className="field">
                    <label>Label (optional)</label>
                    <input type="text" value=${c.label} placeholder="admin / low-priv"
                      onChange=${(e) => updateCred(idx, { label: e.target.value })} />
                  </div>
                  <div style=${{ paddingBottom: 1 }}>
                    <button type="button" className="btn ghost sm" onClick=${() => removeCred(idx)}>Remove</button>
                  </div>
                </div>
              `)}
              <div>
                <button type="button" className="btn secondary sm" onClick=${addCred}>
                  <${IconPlus} /> Add credential
                </button>
              </div>
            </fieldset>
          `}

          <div className="divider" />
          <div className="row spread">
            <button type="button" className="btn ghost" onClick=${() => navigate("#/")}>Cancel</button>
            <button type="submit" className="btn" disabled=${saving}>
              ${saving ? "Saving…" : isEdit ? "Save changes" : "Create site"}
            </button>
          </div>
        </form>
      `}
    </div>
  `;
}

// ---- Settings page ------------------------------------------------------

const PROVIDER_LABELS = {
  anthropic:        "Anthropic",
  openai:           "OpenAI",
  openai_compatible:"OpenAI-compatible (LM Studio, Ollama, etc.)",
};

const PROVIDER_HINTS = {
  anthropic:         "claude-opus-4-5",
  openai:            "gpt-4o",
  openai_compatible: "e.g. llama-3.1-8b-instruct or the model name shown in LM Studio",
};

function SettingsPage() {
  const [form, setForm]         = useState(null);
  const [defaultModels, setDMs] = useState({});
  const [saving, setSaving]     = useState(false);
  const [saved, setSaved]       = useState(false);
  const [error, setError]       = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [cfg, dms] = await Promise.all([api.getLLMConfig(), api.getDefaultModels()]);
        setDMs(dms);
        setForm(cfg ? {
          provider:    cfg.provider,
          api_key:     cfg.api_key    ?? "",
          base_url:    cfg.base_url   ?? "",
          model:       cfg.model,
          max_tokens:  cfg.max_tokens,
          temperature: cfg.temperature,
        } : {
          provider: "anthropic", api_key: "", base_url: "",
          model: "claude-opus-4-5", max_tokens: 4096, temperature: 0,
        });
      } catch (e) { setError(e.message); }
    })();
  }, []);

  const update = (patch) => {
    setSaved(false);
    setForm((f) => ({ ...f, ...patch }));
  };

  // When provider changes, reset model to first known default
  const changeProvider = (p) => {
    const models = defaultModels[p] || [];
    update({ provider: p, model: models[0] || "", api_key: "", base_url: "" });
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null); setSaving(true); setSaved(false);
    const payload = {
      provider:    form.provider,
      api_key:     form.provider !== "openai_compatible" ? (form.api_key.trim() || null) : (form.api_key.trim() || null),
      base_url:    form.provider === "openai_compatible" ? form.base_url.trim() : null,
      model:       form.model.trim(),
      max_tokens:  Number(form.max_tokens),
      temperature: Number(form.temperature),
    };
    try {
      await api.upsertLLMConfig(payload);
      setSaved(true);
    } catch (e2) { setError(e2.message); }
    finally      { setSaving(false); }
  };

  const models = form ? (defaultModels[form.provider] || []) : [];
  const isCustomModel = form && models.length > 0 && !models.includes(form.model) && form.model !== "";

  return html`
    <div className="topbar">
      <div className="topbar-title">LLM Settings</div>
    </div>

    <div className="content">
      ${!form && !error && html`<div className="subtle">Loading…</div>`}
      ${error  && html`<div className="alert error">${error}</div>`}

      ${form && html`
        <form className="card" onSubmit=${onSubmit}>

          <div className="form-section-title">Provider</div>

          <div className="provider-grid">
            ${Object.entries(PROVIDER_LABELS).map(([key, label]) => html`
              <label key=${key} className=${"provider-card" + (form.provider === key ? " selected" : "")}>
                <input type="radio" name="provider" value=${key}
                  checked=${form.provider === key}
                  onChange=${() => changeProvider(key)} />
                <span className="provider-name">${label}</span>
              </label>
            `)}
          </div>

          <div className="divider" />
          <div className="form-section-title">
            ${PROVIDER_LABELS[form.provider]} Configuration
          </div>

          ${(form.provider === "anthropic" || form.provider === "openai") && html`
            <div className="field">
              <label>API Key</label>
              <input type="password" required
                value=${form.api_key}
                placeholder=${form.provider === "anthropic" ? "sk-ant-…" : "sk-…"}
                onChange=${(e) => update({ api_key: e.target.value })} />
            </div>
          `}

          ${form.provider === "openai_compatible" && html`
            <div className="field">
              <label>Base URL</label>
              <input type="url" required
                value=${form.base_url}
                placeholder="http://localhost:1234/v1"
                onChange=${(e) => update({ base_url: e.target.value })} />
              <div className="field-hint">LM Studio default: http://localhost:1234/v1 · Ollama: http://localhost:11434/v1</div>
            </div>
            <div className="field">
              <label>API Key <span className="field-optional">(optional)</span></label>
              <input type="password"
                value=${form.api_key}
                placeholder="Leave blank if not required"
                onChange=${(e) => update({ api_key: e.target.value })} />
            </div>
          `}

          <div className="field">
            <label>Model</label>
            ${models.length > 0 && html`
              <div className="model-select-group">
                <select className="select"
                  value=${isCustomModel ? "__custom__" : form.model}
                  onChange=${(e) => {
                    if (e.target.value !== "__custom__") update({ model: e.target.value });
                    else update({ model: "" });
                  }}>
                  ${models.map((m) => html`<option key=${m} value=${m}>${m}</option>`)}
                  <option value="__custom__">Custom…</option>
                </select>
                ${isCustomModel && html`
                  <input type="text" required value=${form.model}
                    placeholder="Enter model name"
                    onChange=${(e) => update({ model: e.target.value })} />
                `}
              </div>
            `}
            ${models.length === 0 && html`
              <input type="text" required value=${form.model}
                placeholder=${PROVIDER_HINTS[form.provider]}
                onChange=${(e) => update({ model: e.target.value })} />
            `}
          </div>

          <div className="divider" />
          <div className="form-section-title">Sampling</div>

          <div className="two-col">
            <div className="field">
              <label>Max tokens</label>
              <input type="number" required min="1" max="32768"
                value=${form.max_tokens}
                onChange=${(e) => update({ max_tokens: e.target.value })} />
            </div>
            <div className="field">
              <label>Temperature <span className="field-hint-inline">(0 – 2)</span></label>
              <input type="number" required min="0" max="2" step="0.05"
                value=${form.temperature}
                onChange=${(e) => update({ temperature: e.target.value })} />
            </div>
          </div>

          <div className="divider" />
          <div className="row spread">
            <div>
              ${saved && html`
                <span className="save-confirm"><${IconCheck} /> Saved</span>
              `}
            </div>
            <button type="submit" className="btn" disabled=${saving}>
              ${saving ? "Saving…" : "Save settings"}
            </button>
          </div>
        </form>
      `}
    </div>
  `;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);
