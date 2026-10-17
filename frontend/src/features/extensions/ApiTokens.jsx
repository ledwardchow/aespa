import { useCallback, useEffect, useState } from "react";

import * as integrationApi from "../../shared/api/integrationApi.js";
import { API_PERMISSIONS, SCAN_ACCESS, permissionLabels } from "./apiPermissions.js";

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Never";
}

function CopyValue({ label, value }) {
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
    <div className="field">
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

// Values shown in a token's card: its token, a callback secret, or both.
function ShownValues({ shown, onDone }) {
  return (
    <div className="api-token-shown">
      {shown.note ? <div className="subtle">{shown.note}</div> : null}
      {shown.values.map((item) => (
        <CopyValue key={item.label} label={item.label} value={item.value} />
      ))}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn secondary sm" type="button" onClick={onDone}>
          Hide
        </button>
      </div>
    </div>
  );
}

const EMPTY_DRAFT = { name: "", scopes: ["sast"], scan_access: "own", webhook_url: "" };

function draftFrom(token) {
  return {
    name: token.name,
    scopes: token.scopes,
    scan_access: token.scan_access,
    webhook_url: token.webhook_url || "",
  };
}

// The settings a token has, for creating one or editing one.
function TokenForm({ idPrefix, initial, submitLabel, busyLabel, onSubmit, onCancel, children }) {
  const [draft, setDraft] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const set = (key, value) => setDraft((current) => ({ ...current, [key]: value }));
  const toggleScope = (value) =>
    set(
      "scopes",
      draft.scopes.includes(value)
        ? draft.scopes.filter((item) => item !== value)
        : [...draft.scopes, value],
    );

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        name: draft.name.trim(),
        scopes: draft.scopes,
        scan_access: draft.scan_access,
        webhook_url: draft.webhook_url.trim() || null,
      });
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="api-token-form">
      {error ? <div className="alert error">{error}</div> : null}
      <div className="field">
        <label htmlFor={`${idPrefix}-name`}>Name</label>
        <input
          id={`${idPrefix}-name`}
          required
          maxLength={100}
          placeholder="For example, GitHub Actions"
          value={draft.name}
          onChange={(event) => set("name", event.target.value)}
        />
      </div>
      <div className="api-token-choices">
        <fieldset className="api-token-scopes">
          <legend>Permissions</legend>
          {API_PERMISSIONS.map((scope) => (
            <label key={scope.value} className="checkbox-row">
              <input
                type="checkbox"
                checked={draft.scopes.includes(scope.value)}
                onChange={() => toggleScope(scope.value)}
              />
              <span>{scope.label}</span>
            </label>
          ))}
        </fieldset>
        <fieldset className="api-token-scopes">
          <legend>Scans it can see</legend>
          {SCAN_ACCESS.map((option) => (
            <label key={option.value} className="checkbox-row">
              <input
                type="radio"
                name={`${idPrefix}-scan-access`}
                value={option.value}
                checked={draft.scan_access === option.value}
                onChange={() => set("scan_access", option.value)}
              />
              <span>{option.label}</span>
            </label>
          ))}
          <div className="subtle api-token-hint">
            All scans includes scans started in AESPA and by other tokens, for the scan types this
            token may run.
          </div>
        </fieldset>
      </div>
      <div className="field">
        <label htmlFor={`${idPrefix}-webhook`}>Default callback URL (optional)</label>
        <input
          id={`${idPrefix}-webhook`}
          type="url"
          placeholder="https://ci.example.com/aespa-events"
          value={draft.webhook_url}
          onChange={(event) => set("webhook_url", event.target.value)}
        />
        <div className="subtle api-token-hint">
          Used for scans that do not set their own callback URL.
        </div>
      </div>
      {children}
      <div className="row api-token-form-actions">
        <button className="btn secondary" type="button" onClick={onCancel}>
          Cancel
        </button>
        <button
          className="btn"
          type="submit"
          disabled={saving || !draft.name.trim() || !draft.scopes.length}
        >
          {saving ? busyLabel : submitLabel}
        </button>
      </div>
    </form>
  );
}

function TokenCard({ token, shown, onShow, onHide, onChanged }) {
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const scanAccess = SCAN_ACCESS.find((option) => option.value === token.scan_access);

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

  const showToken = () =>
    run(async () => {
      const result = await integrationApi.showApiToken(token.id);
      onShow({ values: [{ label: "Token", value: result.token }] });
    });

  const newValue = () => {
    const message = token.can_show_token
      ? `Give ${token.name} a new value? Apps using the current value stop working.`
      : `Give ${token.name} a new value? Its current value can't be shown because it was created before AESPA kept tokens. Apps using it stop working.`;
    if (!window.confirm(message)) return;
    run(async () => {
      const result = await integrationApi.newApiTokenValue(token.id);
      onShow({
        note: "Update apps that use this token.",
        values: [{ label: "Token", value: result.token }],
      });
      onChanged();
    });
  };

  const newSecret = () => {
    if (
      !window.confirm(
        `Give ${token.name} a new callback secret? Update apps that check signatures.`,
      )
    ) {
      return;
    }
    run(async () => {
      const rotated = await integrationApi.rotateWebhookSecret(token.id);
      onShow({
        note: "This secret is not shown again.",
        values: [{ label: "Callback secret", value: rotated.webhook_secret }],
      });
    });
  };

  const setActive = (active) => {
    if (
      !active &&
      !window.confirm(
        `Turn off ${token.name}? Apps using it stop working until you turn it back on.`,
      )
    ) {
      return;
    }
    run(async () => {
      await (active
        ? integrationApi.reactivateApiToken(token.id)
        : integrationApi.deactivateApiToken(token.id));
      onChanged();
    });
  };

  const save = async (changes) => {
    const updated = await integrationApi.updateApiToken(token.id, {
      ...changes,
      webhook_url: changes.webhook_url ?? "",
    });
    if (updated.webhook_secret) {
      onShow({
        note: "A callback secret was created for the new callback URL. It is not shown again.",
        values: [{ label: "Callback secret", value: updated.webhook_secret }],
      });
    }
    setEditing(false);
    onChanged();
  };

  return (
    <article className={`api-token-card${token.active ? "" : " off"}`} aria-label={token.name}>
      <div className="api-token-head">
        <div className="api-token-title">
          <span className="api-token-name">{token.name}</span>
          <span className={`badge ${token.active ? "success" : "danger"}`}>
            {token.active ? "On" : "Off"}
          </span>
          <code className="subtle">{token.prefix}…</code>
        </div>
        <div className="row api-token-actions">
          {token.can_show_token ? (
            <button className="btn secondary sm" type="button" disabled={busy} onClick={showToken}>
              Show token
            </button>
          ) : null}
          {token.active ? null : (
            <button
              className="btn sm"
              type="button"
              disabled={busy}
              onClick={() => setActive(true)}
            >
              Turn on
            </button>
          )}
          <button
            className="btn secondary sm"
            type="button"
            disabled={busy}
            aria-expanded={editing}
            onClick={() => setEditing((value) => !value)}
          >
            {editing ? "Close" : "Edit"}
          </button>
        </div>
      </div>
      <dl className="api-token-facts">
        <div>
          <dt>Permissions</dt>
          <dd>{permissionLabels(token.scopes)}</dd>
        </div>
        <div>
          <dt>Scans it can see</dt>
          <dd>{scanAccess ? scanAccess.label : token.scan_access}</dd>
        </div>
        <div>
          <dt>Last used</dt>
          <dd>{formatDate(token.last_used_at)}</dd>
        </div>
        <div>
          <dt>Callback URL</dt>
          <dd className="api-token-url">{token.webhook_url || "None"}</dd>
        </div>
      </dl>
      {!token.can_show_token && !editing ? (
        <div className="subtle api-token-hint">
          Its value can't be shown because it was created before AESPA kept tokens. To get one you
          can show, choose Edit, then New token value.
        </div>
      ) : null}
      {error ? <div className="alert error">{error}</div> : null}
      {shown ? <ShownValues shown={shown} onDone={onHide} /> : null}
      {editing ? (
        <TokenForm
          idPrefix={`api-token-${token.id}`}
          initial={draftFrom(token)}
          submitLabel="Save"
          busyLabel="Saving…"
          onSubmit={save}
          onCancel={() => setEditing(false)}
        >
          <div className="api-token-more">
            <div className="api-token-more-title">Other actions</div>
            <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
              <button className="btn secondary sm" type="button" disabled={busy} onClick={newValue}>
                New token value
              </button>
              {token.has_webhook_secret ? (
                <button
                  className="btn secondary sm"
                  type="button"
                  disabled={busy}
                  onClick={newSecret}
                >
                  New callback secret
                </button>
              ) : null}
              {token.active ? (
                <button
                  className="btn secondary sm"
                  type="button"
                  disabled={busy}
                  onClick={() => setActive(false)}
                >
                  Turn off
                </button>
              ) : null}
            </div>
          </div>
        </TokenForm>
      ) : null}
    </article>
  );
}

export function ApiTokens() {
  const [tokens, setTokens] = useState(null);
  const [failures, setFailures] = useState([]);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);
  // Values on display, by token id.
  const [shown, setShown] = useState({});

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

  const show = (tokenId, values) => setShown((current) => ({ ...current, [tokenId]: values }));
  const hide = (tokenId) =>
    setShown((current) => {
      const next = { ...current };
      delete next[tokenId];
      return next;
    });

  const create = async (body) => {
    const created = await integrationApi.createApiToken(body);
    show(created.id, {
      note: created.webhook_secret
        ? "Copy the callback secret now; it is not shown again. You can show the token later."
        : "You can show the token again later.",
      values: [
        { label: "Token", value: created.token },
        ...(created.webhook_secret
          ? [{ label: "Callback secret", value: created.webhook_secret }]
          : []),
      ],
    });
    setCreating(false);
    load();
  };

  return (
    <section className="card api-tokens" aria-label="API tokens">
      <div className="api-tokens-head">
        <div>
          <div className="form-section-title">API tokens</div>
          <div className="subtle" style={{ marginTop: 4 }}>
            Apps send a token in the Authorization header. Tokens can only be managed here, on this
            computer.
          </div>
        </div>
        {creating ? null : (
          <button className="btn" type="button" onClick={() => setCreating(true)}>
            New token
          </button>
        )}
      </div>
      {error ? <div className="alert error">{error}</div> : null}
      {creating ? (
        <div className="api-token-card">
          <div className="api-token-name">New token</div>
          <TokenForm
            idPrefix="api-token-new"
            initial={EMPTY_DRAFT}
            submitLabel="Create token"
            busyLabel="Creating…"
            onSubmit={create}
            onCancel={() => setCreating(false)}
          />
        </div>
      ) : null}
      {tokens === null && !error ? <div className="subtle">Loading…</div> : null}
      {tokens?.length === 0 && !creating ? (
        <div className="subtle">No tokens yet. Create one so an app can use the API.</div>
      ) : null}
      {tokens?.length ? (
        <div className="api-token-list">
          {tokens.map((token) => (
            <TokenCard
              key={token.id}
              token={token}
              shown={shown[token.id]}
              onShow={(values) => show(token.id, values)}
              onHide={() => hide(token.id)}
              onChanged={load}
            />
          ))}
        </div>
      ) : null}
      {failures.length ? (
        <>
          <div className="extension-subsection-title" style={{ marginTop: 8 }}>
            Failed callbacks
          </div>
          <div className="table-wrap">
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
                    <td className="subtle api-token-url">{item.url}</td>
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
