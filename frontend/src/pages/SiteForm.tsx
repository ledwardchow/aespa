import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, CredentialIn, SitePayload } from "../api";

function IconPlus() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  );
}

type FormState = {
  name: string;
  base_url: string;
  requires_auth: boolean;
  login_url: string;
  notes: string;
  credentials: { username: string; password: string; label: string }[];
};

const empty: FormState = {
  name: "", base_url: "", requires_auth: false, login_url: "", notes: "", credentials: [],
};

export default function SiteForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = id !== undefined;
  const siteId = isEdit ? parseInt(id, 10) : null;

  const [form, setForm]       = useState<FormState>(empty);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    if (siteId === null) return;
    (async () => {
      try {
        const data = await api.getSite(siteId);
        setForm({
          name: data.name, base_url: data.base_url, requires_auth: data.requires_auth,
          login_url: data.login_url || "", notes: data.notes || "",
          credentials: data.credentials.map((c) => ({
            username: c.username, password: c.password, label: c.label || "",
          })),
        });
      } catch (e) { setError((e as Error).message); }
      finally     { setLoading(false); }
    })();
  }, [siteId]);

  const update     = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }));
  const updateCred = (idx: number, patch: Partial<FormState["credentials"][number]>) =>
    setForm((f) => ({ ...f, credentials: f.credentials.map((c, i) => i === idx ? { ...c, ...patch } : c) }));
  const addCred    = () => update({ credentials: [...form.credentials, { username: "", password: "", label: "" }] });
  const removeCred = (idx: number) => update({ credentials: form.credentials.filter((_, i) => i !== idx) });

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null); setSaving(true);
    const credentials: CredentialIn[] = form.requires_auth
      ? form.credentials.map((c) => ({ username: c.username, password: c.password, label: c.label || null }))
      : [];
    const payload: SitePayload = {
      name: form.name.trim(), base_url: form.base_url.trim(),
      requires_auth: form.requires_auth,
      login_url: form.requires_auth ? form.login_url.trim() : null,
      notes: form.notes.trim() || null, credentials,
    };
    try {
      if (siteId !== null) await api.updateSite(siteId, payload);
      else                 await api.createSite(payload);
      navigate("/");
    } catch (e2) { setError((e2 as Error).message); }
    finally      { setSaving(false); }
  };

  const title = isEdit ? "Edit site" : "New site";

  return (
    <>
      <div className="topbar">
        <div className="topbar-title">
          <Link to="/" style={{ color: "var(--muted)", fontWeight: 400 }}>Sites</Link>
          <span className="breadcrumb-sep"> / </span>
          {title}
        </div>
      </div>

      <div className="content">
        {loading && <div className="subtle">Loading…</div>}
        {!loading && (
          <form className="card" onSubmit={onSubmit}>
            {error && <div className="alert error">{error}</div>}

            <div className="form-section-title">Site</div>

            <div className="field">
              <label>Name</label>
              <input type="text" required value={form.name} placeholder="e.g. Juice Shop"
                onChange={(e) => update({ name: e.target.value })} />
            </div>

            <div className="field">
              <label>Base URL</label>
              <input type="url" required value={form.base_url} placeholder="https://target.example.com"
                onChange={(e) => update({ base_url: e.target.value })} />
            </div>

            <div className="field">
              <label>Notes (optional)</label>
              <textarea value={form.notes} placeholder="Scope, contacts, notes…"
                onChange={(e) => update({ notes: e.target.value })} />
            </div>

            <div className="divider" />
            <div className="form-section-title">Authentication</div>

            <label className="toggle-row">
              <input type="checkbox" checked={form.requires_auth}
                onChange={(e) => update({ requires_auth: e.target.checked })} />
              <span>This site requires authentication</span>
            </label>

            {form.requires_auth && (
              <>
                <div className="field">
                  <label>Login page URL</label>
                  <input type="url" required value={form.login_url} placeholder="https://target.example.com/login"
                    onChange={(e) => update({ login_url: e.target.value })} />
                </div>

                <fieldset>
                  <legend>Credentials</legend>

                  {form.credentials.length === 0 && <div className="subtle">No credentials yet.</div>}

                  {form.credentials.map((c, idx) => (
                    <div className="cred-row" key={idx}>
                      <div className="field">
                        <label>Username</label>
                        <input type="text" required value={c.username}
                          onChange={(e) => updateCred(idx, { username: e.target.value })} />
                      </div>
                      <div className="field">
                        <label>Password</label>
                        <input type="text" required value={c.password}
                          onChange={(e) => updateCred(idx, { password: e.target.value })} />
                      </div>
                      <div className="field">
                        <label>Label (optional)</label>
                        <input type="text" value={c.label} placeholder="admin / low-priv"
                          onChange={(e) => updateCred(idx, { label: e.target.value })} />
                      </div>
                      <div style={{ paddingBottom: 1 }}>
                        <button type="button" className="btn ghost sm" onClick={() => removeCred(idx)}>Remove</button>
                      </div>
                    </div>
                  ))}

                  <div>
                    <button type="button" className="btn secondary sm" onClick={addCred}>
                      <IconPlus /> Add credential
                    </button>
                  </div>
                </fieldset>
              </>
            )}

            <div className="divider" />

            <div className="row spread">
              <button type="button" className="btn ghost" onClick={() => navigate("/")}>Cancel</button>
              <button type="submit" className="btn" disabled={saving}>
                {saving ? "Saving…" : isEdit ? "Save changes" : "Create site"}
              </button>
            </div>
          </form>
        )}
      </div>
    </>
  );
}
