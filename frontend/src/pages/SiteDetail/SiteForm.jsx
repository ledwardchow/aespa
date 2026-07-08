import { useState, useEffect } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";
import { PageHeader, Crumb, Sep } from "../../components/PageHeader";
import { IconPlus } from "../../components/Icons";

export function SiteForm({
  siteId
}) {
  const isEdit = typeof siteId === "number";
  const [form, setForm] = useState({
    name: "",
    base_url: "",
    requires_auth: false,
    login_url: "",
    notes: "",
    scan_guidance: "",
    credentials: []
  });
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  useEffect(() => {
    if (!isEdit) return;
    (async () => {
      try {
        const d = await api.getSite(siteId);
        setForm({
          name: d.name,
          base_url: d.base_url,
          requires_auth: d.requires_auth,
          login_url: d.login_url || "",
          notes: d.notes || "",
          scan_guidance: d.scan_guidance || "",
          credentials: d.credentials.map(c => ({
            username: c.username,
            password: c.password,
            label: c.label || "",
            login_url: c.login_url || "",
            auth_mode: c.auth_mode || "auto",
            totp_seed: ""
          }))
        });
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [isEdit, siteId]);
  const upd = p => {
    setForm(f => ({
      ...f,
      ...p
    }));
  };
  const updC = (i, p) => setForm(f => ({
    ...f,
    credentials: f.credentials.map((c, j) => j === i ? {
      ...c,
      ...p
    } : c)
  }));
  const addC = () => upd({
    credentials: [...form.credentials, {
      username: "",
      password: "",
      label: "",
      login_url: "",
      auth_mode: "auto",
      totp_seed: ""
    }]
  });
  const rmC = i => upd({
    credentials: form.credentials.filter((_, j) => j !== i)
  });
  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    const payload = {
      name: form.name.trim(),
      base_url: form.base_url.trim(),
      requires_auth: form.requires_auth,
      login_url: form.requires_auth ? form.login_url.trim() || null : null,
      notes: form.notes.trim() || null,
      scan_guidance: form.scan_guidance.trim() || null,
      credentials: form.requires_auth ? form.credentials.map(c => {
        const base = {
          username: c.username,
          password: c.password,
          label: c.label || null,
          login_url: c.login_url?.trim() || null,
          auth_mode: c.auth_mode || "auto"
        };
        if (c.totp_seed?.trim()) base.totp_seed = c.totp_seed.trim();
        return base;
      }) : []
    };
    try {
      if (isEdit) {
        await api.updateSite(siteId, payload);
        nav(`#/sites/${siteId}`);
      } else {
        const s = await api.createSite(payload);
        nav(`#/sites/${s.id}`);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const bc = isEdit
    ? <><Crumb href={`#/sites/${siteId}`}>{form.name || "Site"}</Crumb><Sep />Edit</>
    : "New site";
  return <>
    <PageHeader title={bc} />
    <div className="content scroll-content">
      {loading && <div className="subtle">Loading…</div>}
      {!loading && <form className="card" onSubmit={onSubmit}>
          {error && <div className="alert error">{error}</div>}
          <div className="form-section-title">Site</div>
          <div className="field"><label>Name</label>
            <input type="text" required value={form.name} placeholder="e.g. Juice Shop" onChange={e => upd({
            name: e.target.value
          })} /></div>
          <div className="field"><label>Base URL</label>
            <input type="url" required value={form.base_url} placeholder="https://target.example.com" onChange={e => upd({
            base_url: e.target.value
          })} /></div>
          <div className="field"><label>Notes (optional)</label>
            <textarea value={form.notes} placeholder="Scope, contacts…" onChange={e => upd({
            notes: e.target.value
          })} /></div>
          <div className="field"><label>Test Lead guidance (optional)</label>
            <textarea rows="9" value={form.scan_guidance} placeholder="Instructions for the testing agents (passed directly to the prompt) — i.e. how to complete a particularly complex login sequence, things to focus on, things to avoid…" onChange={e => upd({
            scan_guidance: e.target.value
          })} /></div>
          <div className="divider" />
          <div className="form-section-title">Authentication</div>
          <label className="toggle-row">
            <input type="checkbox" checked={form.requires_auth} onChange={e => upd({
            requires_auth: e.target.checked
          })} />
            <span>This site requires authentication</span>
          </label>
          {form.requires_auth && <>
            <div className="field"><label>Default login page URL</label>
              <input type="url" value={form.login_url} placeholder="https://target.example.com/login" onChange={e => upd({
              login_url: e.target.value
            })} /></div>
            <fieldset><legend>Credentials</legend>
              {form.credentials.length === 0 && <div className="subtle">No credentials yet.</div>}
              {form.credentials.map((c, i) => {

              return <div className="cred-row" key={i}>
                  <div className="field"><label>Username</label><input type="text" required value={c.username} onChange={e => updC(i, {
                    username: e.target.value
                  })} /></div>
                  <div className="field"><label>Password</label><input type="text" required value={c.password} onChange={e => updC(i, {
                    password: e.target.value
                  })} /></div>
                  <div className="field credential-login-field"><label>Login URL <span className="field-optional">(optional override)</span></label><input type="url" value={c.login_url || ""} placeholder={form.login_url ? `Uses default: ${form.login_url}` : "Required if no default login URL"} onChange={e => updC(i, {
                    login_url: e.target.value
                  })} /></div>
                  <div className="field"><label>Label</label><input type="text" value={c.label} placeholder="admin" onChange={e => updC(i, {
                    label: e.target.value
                  })} /></div>
                  <div className="field"><label>Auth Mode</label>
                    <select value={c.auth_mode || "auto"} onChange={e => updC(i, {
                    auth_mode: e.target.value
                  })}>
                      <option value="auto">auto — single-page form fill</option>
                      <option value="totp">totp — form fill + TOTP 2FA</option>
                      <option value="guided">guided — interactive browser login</option>
                    </select></div>
                  {(c.auth_mode || "auto") === "totp" && <div className="field"><label>TOTP Seed <span className="field-optional">(base32 secret from authenticator app)</span></label>
                      <input type="text" value={c.totp_seed || ""} placeholder="JBSWY3DPEHPK3PXP…" onChange={e => updC(i, {
                    totp_seed: e.target.value
                  })} /></div>}
                  {(c.auth_mode || "auto") === "guided" && <div className="field"><div style={{
                    background: "var(--surface-2,#2a2a2a)",
                    border: "1px solid var(--border)",
                    borderRadius: 4,
                    padding: "8px 10px",
                    fontSize: 12,
                    color: "var(--text-2)"
                  }}>
                      🖥️ A browser window will open when a crawl or dynamic scan starts. Complete the login (including any SSO / MFA / push notifications), then click <strong>I'm Done</strong> in the run detail view. ALICE reuses the session captured by whichever phase runs first.
                    </div></div>}
                  <div className="credential-remove-cell"><button type="button" className="btn ghost sm" onClick={() => rmC(i)}>Remove</button></div>
                </div>;
            })}
              <button type="button" className="btn secondary sm" onClick={addC}><IconPlus /> Add credential</button>
            </fieldset></>}
          <div className="divider" />
          <div className="row spread">
            <button type="button" className="btn ghost" onClick={() => isEdit ? nav(`#/sites/${siteId}`) : nav("#/")}>Cancel</button>
            <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : isEdit ? "Save changes" : "Create site"}</button>
          </div>
        </form>}
    </div></>;
}
