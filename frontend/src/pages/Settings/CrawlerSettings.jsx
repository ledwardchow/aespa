import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { IconCheck } from "../../components/Icons";

export function CrawlerSettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setForm(await api.getCrawlerConfig());
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);

  const onSubmit = async e => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.upsertCrawlerConfig({
        js_endpoint_discovery_enabled: !!form.js_endpoint_discovery_enabled,
        skip_dangerous_actions: !!form.skip_dangerous_actions,
        suppress_form_submit_actions: !!form.suppress_form_submit_actions,
        block_non_idempotent_interactive_replay: !!form.block_non_idempotent_interactive_replay,
        enable_access_reconciliation: !!form.enable_access_reconciliation,
        llm_max_concurrency: form.llm_max_concurrency && form.llm_max_concurrency > 0 ? form.llm_max_concurrency : null
      });
      setForm(updated);
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return <>
    {!form && !error && <div className="subtle">Loading…</div>}
    {error && <div className="alert error">{error}</div>}
    {form && <form className="card" onSubmit={onSubmit}>
        <div className="form-section-title">Crawler</div>
        <label className="toggle-row">
          <input type="checkbox" checked={!!form.js_endpoint_discovery_enabled} onChange={e => {
          setSaved(false);
          setForm(f => ({
            ...f,
            js_endpoint_discovery_enabled: e.target.checked
          }));
        }} />
          <span>Proactively add JavaScript-discovered endpoints to scope</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={!!form.skip_dangerous_actions} onChange={e => {
          setSaved(false);
          setForm(f => ({
            ...f,
            skip_dangerous_actions: e.target.checked
          }));
        }} />
          <span>Skip dangerous action labels (pay, checkout, purchase, transfer, etc.)</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={!!form.suppress_form_submit_actions} onChange={e => {
          setSaved(false);
          setForm(f => ({
            ...f,
            suppress_form_submit_actions: e.target.checked
          }));
        }} />
          <span>Suppress form submit buttons during interactive control discovery</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={!!form.block_non_idempotent_interactive_replay} onChange={e => {
          setSaved(false);
          setForm(f => ({
            ...f,
            block_non_idempotent_interactive_replay: e.target.checked
          }));
        }} />
          <span>Block non-idempotent requests (POST/PUT/PATCH/DELETE) during interactive replay</span>
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={!!form.enable_access_reconciliation} onChange={e => {
          setSaved(false);
          setForm(f => ({
            ...f,
            enable_access_reconciliation: e.target.checked
          }));
        }} />
          <span>Enable access reconciliation (recheck known pages with each credential)</span>
        </label>

        <div style={{ marginTop: 16, marginBottom: 8 }}>
          <label style={{ display: "block", fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
            LLM Concurrency Limit
          </label>
          <div className="subtle" style={{ fontSize: 11, marginBottom: 6 }}>
            Maximum concurrent requests sent to the LLM during page analysis. Default is unlimited (0 or blank). Excess requests will queue automatically.
          </div>
          <input
            type="number"
            min="0"
            max="100"
            className="input"
            placeholder="Unlimited (default)"
            value={form.llm_max_concurrency ?? ""}
            onChange={e => {
              setSaved(false);
              const val = e.target.value === "" ? null : parseInt(e.target.value, 10);
              setForm(f => ({
                ...f,
                llm_max_concurrency: val && val > 0 ? val : null
              }));
            }}
            style={{ width: 200 }}
          />
        </div>

        <div className="divider" />
        <div className="row spread">
          <div>{saved && <span className="save-confirm"><IconCheck /> Saved</span>}</div>
          <button type="submit" className="btn" disabled={saving}>{saving ? "Saving…" : "Save Crawler Settings"}</button>
        </div>
      </form>}
  </>;
}
