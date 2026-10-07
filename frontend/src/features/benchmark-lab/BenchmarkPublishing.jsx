import { useEffect, useState } from "react";
import { req } from "../../shared/api/request.ts";

const BASE = "/extension/aespa.benchmarking";
const DEFAULT_SITE = "https://aespa-benchmarks.maranthis.chatgpt.site";

export function BenchmarkPublishing({ mode = "publish" }) {
  const [url, setUrl] = useState(DEFAULT_SITE);
  const [token, setToken] = useState("");
  const [uploadToken, setUploadToken] = useState("");
  const [serviceSaved, setServiceSaved] = useState(false);
  const [uploadSaved, setUploadSaved] = useState(false);
  const [revealedUploadToken, setRevealedUploadToken] = useState("");
  const [configured, setConfigured] = useState(false);
  const [revealedToken, setRevealedToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    req(`${BASE}/publishing`)
      .then((data) => {
        setUrl(data.site_url || DEFAULT_SITE);
        setServiceSaved(data.token_saved);
        setUploadSaved(data.upload_token_saved);
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
          ...(token ? { service_token: token } : {}),
          ...(uploadToken ? { upload_token: uploadToken } : {}),
        },
      });
      setToken("");
      setUploadToken("");
      setServiceSaved(true);
      setUploadSaved(true);
      setRevealedUploadToken("");
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
      const report = await req(`${BASE}/publish`, { method: "POST" });
      setMessage(`${report.received} results sent. ${report.skipped_stale} older updates skipped.`);
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
      setRevealedToken(saved.service_token);
      setRevealedUploadToken(saved.upload_token || "");
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
            Private Sites service token
            <input
              className="input"
              type="password"
              autoComplete="new-password"
              value={token}
              disabled={busy}
              placeholder={serviceSaved ? "Saved. Leave blank to keep it." : "Enter service token"}
              onChange={(event) => setToken(event.target.value)}
            />
          </label>
          <label className="field">
            Upload token
            <input
              className="input"
              type="password"
              autoComplete="new-password"
              value={uploadToken}
              disabled={busy}
              placeholder={
                uploadSaved
                  ? "Saved. Leave blank to keep it."
                  : "Create a token on the results site"
              }
              onChange={(event) => setUploadToken(event.target.value)}
            />
          </label>
          <p className="subtle">
            Open the results site’s API &amp; connection tab to create or revoke upload tokens. Both
            tokens are required to publish.
          </p>
          {serviceSaved && (
            <div className="field">
              <div className="form-actions">
                <button
                  className="btn secondary"
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    if (revealedToken) {
                      setRevealedToken("");
                      setRevealedUploadToken("");
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
                  Saved service token
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
          {revealedUploadToken && (
            <label className="field">
              Saved upload token
              <input
                className="input"
                readOnly
                value={revealedUploadToken}
                onFocus={(event) => event.target.select()}
              />
            </label>
          )}
          <p className="subtle">
            Both tokens are stored in this installation’s benchmark extension database and are never
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
        <div className="form-actions">
          <button
            className="btn primary"
            type="button"
            disabled={busy || !configured}
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
