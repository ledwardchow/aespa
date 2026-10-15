import { useEffect, useMemo, useState } from "react";
import { req } from "../../shared/api/request.ts";

const BASE = "/extension/aespa.benchmarking";
const DEFAULT_SITE = "https://benchmarks.aespa.app";

export function BenchmarkPublishing({ mode = "publish", datasets = [], results = [] }) {
  const [url, setUrl] = useState(DEFAULT_SITE);
  const [token, setToken] = useState("");
  const [serviceSaved, setServiceSaved] = useState(false);
  const [configured, setConfigured] = useState(false);
  const [revealedToken, setRevealedToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [selected, setSelected] = useState(() => new Set());
  const apps = useMemo(() => {
    const counts = new Map();
    for (const result of results) {
      counts.set(result.dataset_id, (counts.get(result.dataset_id) || 0) + 1);
    }
    return datasets
      .filter((dataset) => counts.has(dataset.id))
      .map((dataset) => ({
        id: dataset.id,
        name: dataset.label || dataset.name,
        count: counts.get(dataset.id),
      }));
  }, [datasets, results]);
  const chosen = apps.filter((app) => selected.has(app.id)).map((app) => app.id);
  function toggle(id) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  useEffect(() => {
    req(`${BASE}/publishing`)
      .then((data) => {
        setUrl(data.site_url || DEFAULT_SITE);
        setServiceSaved(data.token_saved);
        setConfigured(data.token_saved && data.upload_token_saved);
      })
      .catch((err) => setError(err.message));
  }, []);
  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await req(`${BASE}/publishing`, {
        method: "PUT",
        body: {
          site_url: url,
          ...(token ? { token } : {}),
        },
      });
      setToken("");
      setServiceSaved(true);
      setRevealedToken("");
      setConfigured(true);
      setMessage("Site connection saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  async function publish() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const report = await req(`${BASE}/publish`, {
        method: "POST",
        body: { dataset_ids: chosen },
      });
      setMessage(
        `${report.received} results sent. ${report.skipped_stale} older updates skipped.${report.skipped_site_edits ? ` ${report.skipped_site_edits} site-edited results protected.` : ""}`,
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  async function reveal() {
    setBusy(true);
    setError("");
    try {
      const saved = await req(`${BASE}/publishing/token`, { method: "POST" });
      setRevealedToken(saved.token);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="card">
      <h2>AESPA Benchmarks Online</h2>
      <p className="subtle">
        Benchmark Lab results can be uploaded to a central repository which stores only the
        information required to produce the performance graphs (detailed scan results are not
        uploaded).
      </p>
      {mode === "settings" ? (
        <form onSubmit={save}>
          <label className="field">
            Site URL
            <input
              className="input"
              type="url"
              required
              value={url}
              disabled={busy}
              onChange={(event) => {
                setUrl(event.target.value);
                setConfigured(false);
              }}
            />
          </label>
          <label className="field">
            Upload token
            <input
              className="input"
              type="password"
              autoComplete="new-password"
              value={token}
              disabled={busy}
              placeholder={
                configured
                  ? "Saved. Leave blank to keep it."
                  : "Paste a token generated on the results site"
              }
              onChange={(event) => setToken(event.target.value)}
            />
          </label>
          <p className="subtle">
            Open the results site’s API &amp; connection tab to create or revoke upload tokens. Copy
            the generated token here. No separate service token is needed.
          </p>
          {configured && (
            <div className="field">
              <div className="form-actions">
                <button
                  className="btn secondary"
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    if (revealedToken) {
                      setRevealedToken("");
                    } else {
                      reveal();
                    }
                  }}
                >
                  {revealedToken ? "Hide saved token" : "Show saved token"}
                </button>
              </div>
              {revealedToken && (
                <label>
                  Saved upload token
                  <input
                    className="input"
                    readOnly
                    value={revealedToken}
                    onFocus={(event) => event.target.select()}
                  />
                </label>
              )}
            </div>
          )}
          <p className="subtle">
            The token is stored in this installation’s benchmark extension database and is never
            included in benchmark exports.
          </p>
          <div className="form-actions">
            <button className="btn secondary" disabled={busy}>
              Save connection
            </button>
            {serviceSaved && (
              <a className="btn secondary" href={url} target="_blank" rel="noreferrer">
                Open results site
              </a>
            )}
          </div>
        </form>
      ) : (
        <>
          <fieldset className="field" disabled={busy}>
            <legend>Applications to publish</legend>
            {apps.length === 0 ? (
              <p className="subtle">No saved results yet.</p>
            ) : (
              <>
                {apps.map((app) => (
                  <label key={app.id} className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={selected.has(app.id)}
                      onChange={() => toggle(app.id)}
                    />
                    {app.name} ({app.count} {app.count === 1 ? "result" : "results"})
                  </label>
                ))}
                <div className="form-actions">
                  <button
                    className="btn ghost sm"
                    type="button"
                    onClick={() => setSelected(new Set(apps.map((app) => app.id)))}
                  >
                    Select all
                  </button>
                  <button
                    className="btn ghost sm"
                    type="button"
                    onClick={() => setSelected(new Set())}
                  >
                    Clear
                  </button>
                </div>
              </>
            )}
          </fieldset>
          <div className="form-actions">
            <button
              className="btn primary"
              type="button"
              disabled={busy || !configured || chosen.length === 0}
              onClick={publish}
            >
              {busy ? "Publishing..." : "Publish results"}
            </button>
            <a className="btn secondary" href="#/extensions/aespa.benchmarking/settings">
              Connection settings
            </a>
            {configured && (
              <a className="btn secondary" href={url} target="_blank" rel="noreferrer">
                Open results site
              </a>
            )}
          </div>
        </>
      )}
      {message && <p role="status">{message}</p>}
      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
