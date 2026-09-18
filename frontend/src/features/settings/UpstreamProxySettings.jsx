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
        scanner_proxy_url: (form.scanner_proxy_url || "").trim() || null,
        llm_proxy_url: (form.llm_proxy_url || "").trim() || null,
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
          {form.proxy_scanner && (
            <div className="field">
              <label htmlFor="scanner-proxy-url">Testing traffic proxy URL</label>
              <input
                id="scanner-proxy-url"
                type="url"
                required
                value={form.scanner_proxy_url || ""}
                placeholder="http://127.0.0.1:8080"
                onChange={(e) =>
                  upd({
                    scanner_proxy_url: e.target.value,
                  })
                }
              />
            </div>
          )}
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
          {form.proxy_llm && (
            <div className="field">
              <label htmlFor="llm-proxy-url">LLM traffic proxy URL</label>
              <input
                id="llm-proxy-url"
                type="url"
                required
                value={form.llm_proxy_url || ""}
                placeholder="http://127.0.0.1:8080"
                onChange={(e) =>
                  upd({
                    llm_proxy_url: e.target.value,
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
