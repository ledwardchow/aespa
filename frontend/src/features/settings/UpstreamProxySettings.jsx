import * as settingsApi from "../../shared/api/settings.js";
import { useState, useEffect } from "react";

import { IconCheck } from "../../shared/ui/Icons.jsx";

export function UpstreamProxySettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const upd = (p) => {
    setSaved(false);
    setForm((f) => ({
      ...f,
      ...p,
    }));
  };
  useEffect(() => {
    (async () => {
      try {
        setForm(await settingsApi.getUpstreamProxy());
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);
  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    try {
      const saved = await settingsApi.upsertUpstreamProxy({
        proxy_url:
          form.proxy_scanner || form.proxy_llm ? (form.proxy_url || "").trim() || null : null,
        proxy_scanner: !!form.proxy_scanner,
        proxy_llm: !!form.proxy_llm,
      });
      setForm(saved);
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const anyProxy = form && (form.proxy_scanner || form.proxy_llm);
  return (
    <>
      {!form && !error && <div className="subtle">Loading…</div>}
      {error && <div className="alert error">{error}</div>}
      {form && (
        <form className="card" onSubmit={onSubmit}>
          <div className="form-section-title">Upstream Proxy</div>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={!!form.proxy_scanner}
              onChange={(e) =>
                upd({
                  proxy_scanner: e.target.checked,
                })
              }
            />
            <span>Send target requests through an upstream proxy</span>
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={!!form.proxy_llm}
              onChange={(e) =>
                upd({
                  proxy_llm: e.target.checked,
                })
              }
            />
            <span>Send LLM requests through the upstream proxy</span>
          </label>
          {anyProxy && (
            <div className="field">
              <label>Proxy URL</label>
              <input
                type="url"
                required
                value={form.proxy_url || ""}
                placeholder="http://127.0.0.1:8080"
                onChange={(e) =>
                  upd({
                    proxy_url: e.target.value,
                  })
                }
              />
            </div>
          )}
          <div className="divider" />
          <div className="row spread">
            <div>
              {saved && (
                <span className="save-confirm">
                  <IconCheck /> Saved
                </span>
              )}
            </div>
            <button type="submit" className="btn" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      )}
    </>
  );
}
