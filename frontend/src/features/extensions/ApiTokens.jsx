import { useCallback, useEffect, useState } from "react";

import * as integrationApi from "../../shared/api/integrationApi.js";
import { API_PERMISSIONS, permissionLabels } from "./apiPermissions.js";

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Never";
}

function OneTimeValue({ label, value }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className="field" style={{ marginTop: 8 }}>
      <label>{label}</label>
      <div className="row" style={{ gap: 8 }}>
        <input readOnly value={value} aria-label={label} className="api-def-secret" />
        <button className="btn secondary" type="button" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}

function CreateTokenForm({ onCreated }) {
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState(["sast"]);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const toggle = (value) =>
    setScopes((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const created = await integrationApi.createApiToken({
        name,
        scopes,
        webhook_url: webhookUrl || null,
      });
      setName("");
      setWebhookUrl("");
      onCreated(created);
    } catch (createError) {
      setError(createError.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="api-token-form">
      <div className="extension-subsection-title">Create a token</div>
      {error ? <div className="alert error">{error}</div> : null}
      <div className="field">
        <label htmlFor="api-token-name">Name</label>
        <input
          id="api-token-name"
          required
          maxLength={100}
          placeholder="For example, GitHub Actions"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <fieldset className="api-token-scopes">
        <legend>Permissions</legend>
        {API_PERMISSIONS.map((scope) => (
          <label key={scope.value} className="checkbox-row">
            <input
              type="checkbox"
              checked={scopes.includes(scope.value)}
              onChange={() => toggle(scope.value)}
            />
            <span>{scope.label}</span>
          </label>
        ))}
      </fieldset>
      <div className="field">
        <label htmlFor="api-token-webhook">Default callback URL (optional)</label>
        <input
          id="api-token-webhook"
          type="url"
          placeholder="https://ci.example.com/aespa-events"
          value={webhookUrl}
          onChange={(event) => setWebhookUrl(event.target.value)}
        />
        <div className="subtle" style={{ fontSize: 12 }}>
          Used for scans that do not set their own callback URL.
        </div>
      </div>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn" type="submit" disabled={saving || !name || !scopes.length}>
          {saving ? "Creating…" : "Create token"}
        </button>
      </div>
    </form>
  );
}

function TokenRow({ token, onChanged, onSecret }) {
  const [editing, setEditing] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState(token.webhook_url || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const revoked = Boolean(token.revoked_at);

  const run = async (action) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (actionError) {
      setError(actionError.message);
    } finally {
      setBusy(false);
    }
  };

  const saveWebhook = () =>
    run(async () => {
      const updated = await integrationApi.updateApiToken(token.id, { webhook_url: webhookUrl });
      if (updated.webhook_secret) onSecret(token.name, updated.webhook_secret);
      setEditing(false);
      onChanged();
    });

  return (
    <tr>
      <td>
        <div style={{ fontWeight: 600 }}>{token.name}</div>
        <code className="subtle" style={{ fontSize: 12 }}>
          {token.prefix}…
        </code>
      </td>
      <td className="subtle">{permissionLabels(token.scopes)}</td>
      <td className="subtle">{formatDate(token.last_used_at)}</td>
      <td className="subtle api-token-webhook">
        {editing ? (
          <div className="row" style={{ gap: 6 }}>
            <input
              type="url"
              aria-label={`Callback URL for ${token.name}`}
              value={webhookUrl}
              onChange={(event) => setWebhookUrl(event.target.value)}
            />
            <button className="btn sm" type="button" disabled={busy} onClick={saveWebhook}>
              Save
            </button>
          </div>
        ) : (
          token.webhook_url || "None"
        )}
        {error ? (
          <div className="alert error" style={{ marginTop: 6 }}>
            {error}
          </div>
        ) : null}
      </td>
      <td>
        <span className={`badge ${revoked ? "danger" : "success"}`}>
          {revoked ? "Revoked" : "Active"}
        </span>
      </td>
      <td>
        {revoked ? null : (
          <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
            <button
              className="btn secondary sm"
              type="button"
              disabled={busy}
              onClick={() => setEditing((value) => !value)}
            >
              {editing ? "Cancel" : "Change callback"}
            </button>
            {token.has_webhook_secret ? (
              <button
                className="btn secondary sm"
                type="button"
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    const rotated = await integrationApi.rotateWebhookSecret(token.id);
                    onSecret(token.name, rotated.webhook_secret);
                  })
                }
              >
                New callback secret
              </button>
            ) : null}
            <button
              className="btn secondary sm"
              type="button"
              disabled={busy}
              onClick={() => {
                if (window.confirm(`Revoke ${token.name}? Apps using it will stop working.`)) {
                  run(async () => {
                    await integrationApi.revokeApiToken(token.id);
                    onChanged();
                  });
                }
              }}
            >
              Revoke
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}

export function ApiTokens() {
  const [tokens, setTokens] = useState(null);
  const [failures, setFailures] = useState([]);
  const [error, setError] = useState(null);
  const [shown, setShown] = useState(null);

  const load = useCallback(() => {
    Promise.all([integrationApi.listApiTokens(), integrationApi.listFailedDeliveries()])
      .then(([loadedTokens, loadedFailures]) => {
        setTokens(loadedTokens);
        setFailures(loadedFailures);
      })
      .catch((loadError) => setError(loadError.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <section className="card api-tokens" aria-label="API tokens">
      <div className="form-section-title">API tokens</div>
      <div className="subtle" style={{ marginTop: 4 }}>
        Apps send a token in the Authorization header. Each token sees only the scans it created.
        Tokens can only be managed here, on this computer.
      </div>
      {error ? (
        <div className="alert error" style={{ marginTop: 12 }}>
          {error}
        </div>
      ) : null}
      {shown ? (
        <div className="alert success" style={{ marginTop: 16 }}>
          <div>Copy {shown.title} now. It will not be shown again.</div>
          {shown.values.map((item) => (
            <OneTimeValue key={item.label} label={item.label} value={item.value} />
          ))}
          <div className="row" style={{ justifyContent: "flex-end", marginTop: 8 }}>
            <button className="btn secondary sm" type="button" onClick={() => setShown(null)}>
              Done
            </button>
          </div>
        </div>
      ) : null}
      {tokens === null && !error ? <div className="subtle">Loading…</div> : null}
      {tokens?.length ? (
        <div className="table-wrap" style={{ marginTop: 16 }}>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Permissions</th>
                <th>Last used</th>
                <th>Callback URL</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tokens.map((token) => (
                <TokenRow
                  key={token.id}
                  token={token}
                  onChanged={load}
                  onSecret={(name, secret) =>
                    setShown({
                      title: `the callback secret for ${name}`,
                      values: [{ label: "Callback secret", value: secret }],
                    })
                  }
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {tokens?.length === 0 ? (
        <div className="subtle" style={{ marginTop: 16 }}>
          No tokens yet.
        </div>
      ) : null}
      <CreateTokenForm
        onCreated={(created) => {
          setShown({
            title: `the token for ${created.name}`,
            values: [
              { label: "Token", value: created.token },
              ...(created.webhook_secret
                ? [{ label: "Callback secret", value: created.webhook_secret }]
                : []),
            ],
          });
          load();
        }}
      />
      {failures.length ? (
        <>
          <div className="extension-subsection-title" style={{ marginTop: 24 }}>
            Failed callbacks
          </div>
          <div className="table-wrap" style={{ marginTop: 8 }}>
            <table>
              <thead>
                <tr>
                  <th>Scan</th>
                  <th>Event</th>
                  <th>URL</th>
                  <th>Tries</th>
                  <th>Last error</th>
                </tr>
              </thead>
              <tbody>
                {failures.map((item) => (
                  <tr key={item.id}>
                    <td>{item.scan_id}</td>
                    <td>{item.event}</td>
                    <td className="subtle api-token-webhook">{item.url}</td>
                    <td>{item.attempts}</td>
                    <td className="subtle">{item.last_error || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  );
}
