import { useState } from "react";
import { getAuthenticationKey } from "../../shared/auth/session.ts";

export function AuthenticationSettings() {
  const [key, setKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function accessKey(copy: boolean) {
    setBusy(true);
    setError(null);
    setCopied(false);
    try {
      const value = await getAuthenticationKey();
      if (copy) {
        await navigator.clipboard.writeText(value);
        setCopied(true);
      } else setKey(value);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not retrieve the key.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" style={{ maxWidth: 680 }}>
      <h2 className="form-section-title">Authentication key</h2>
      <p className="field-hint">
        Use this key to sign in if AESPA did not sign you in automatically.
      </p>
      <p className="field-hint" style={{ marginBottom: 12 }}>
        Integrations use tokens from the API extension's settings instead.
      </p>
      <div className="field">
        <label htmlFor="settings-authentication-key">Authentication key</label>
        <input
          id="settings-authentication-key"
          readOnly
          type={key ? "text" : "password"}
          value={key ?? "••••••••••••••••"}
          autoComplete="off"
        />
      </div>
      <div className="row" style={{ gap: 8, marginTop: 12 }}>
        <button
          className="btn secondary"
          disabled={busy}
          onClick={() => (key ? setKey(null) : void accessKey(false))}
        >
          {key ? "Hide" : "Show"}
        </button>
        <button className="btn secondary" disabled={busy} onClick={() => void accessKey(true)}>
          Copy
        </button>
      </div>
      {copied ? <p role="status">Authentication key copied.</p> : null}
      {error ? (
        <p className="alert error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
