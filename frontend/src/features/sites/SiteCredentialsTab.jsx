import { useId, useRef, useState } from "react";

import * as sitesApi from "../../shared/api/sites.js";
import { IconPlus } from "../../shared/ui/Icons.jsx";
import styles from "./SiteForm.module.css";

const LOGIN_METHODS = [
  { value: "auto", label: "Form fill", short: "Form fill" },
  { value: "totp", label: "Form fill + TOTP code", short: "Form + TOTP" },
  { value: "email_otp", label: "Form fill + email code", short: "Form + email code" },
  { value: "entra_id", label: "Microsoft Entra ID", short: "Entra ID" },
  { value: "guided", label: "Log in myself in a browser", short: "Log in myself" },
];

const defaultLoginFields = () => [
  { key: "username", label: "Username", value: "", sensitive: false, selector: "" },
  { key: "password", label: "Password", value: "", sensitive: true, selector: "" },
];

let lastKey = 0;
const draftKey = () => `account-${++lastKey}`;

export const newCredential = () => ({
  _key: draftKey(),
  label: "",
  login_url: "",
  login_fields: defaultLoginFields(),
  auth_mode: "auto",
  totp_seed: "",
  test_mailbox_url: "",
});

export const credentialFromSite = (c) => ({
  _key: draftKey(),
  id: c.id,
  label: c.label || "",
  login_url: c.login_url || "",
  login_fields: (c.login_fields?.length ? c.login_fields : defaultLoginFields()).map((field) => ({
    ...field,
    selector: field.selector || "",
  })),
  auth_mode: c.auth_mode || "auto",
  totp_seed: "",
  test_mailbox_url: c.test_mailbox_url || "",
});

const fieldKey = (label, index, used) => {
  const stem =
    (label || `field_${index + 1}`)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .replace(/^[^a-z]+/, "") || `field_${index + 1}`;
  let key = stem;
  let suffix = 2;
  while (used.has(key)) key = `${stem}_${suffix++}`;
  used.add(key);
  return key;
};

export const credentialPayload = (c) => {
  const usedKeys = new Set();
  const payload = {
    ...(c.id ? { id: c.id } : {}),
    login_fields: c.login_fields.map((field, index) => ({
      key: fieldKey(field.label, index, usedKeys),
      label: field.label.trim(),
      value: field.value,
      sensitive: Boolean(field.sensitive),
      selector: field.selector?.trim() || null,
    })),
    label: c.label || null,
    login_url: c.login_url?.trim() || null,
    auth_mode: c.auth_mode || "auto",
  };
  if (c.totp_seed?.trim()) payload.totp_seed = c.totp_seed.trim();
  if (c.test_mailbox_url?.trim()) payload.test_mailbox_url = c.test_mailbox_url.trim();
  return payload;
};

const accountName = (c, index) =>
  c.label.trim() ||
  c.login_fields.find((field) => !field.sensitive && field.value.trim())?.value.trim() ||
  `Account ${index + 1}`;

const methodLabel = (mode) =>
  LOGIN_METHODS.find((method) => method.value === mode)?.short || "Form fill";

const testSnapshot = (c, loginUrl, baseUrl) =>
  JSON.stringify([credentialPayload(c), c.totp_seed, loginUrl.trim(), baseUrl.trim()]);

// A result only counts while the account and URLs still match what was tested.
export const currentTest = (tests, c, loginUrl, baseUrl) => {
  const test = tests[c._key];
  if (!test) return null;
  if (test.state === "running") return test;
  return test.snapshot === testSnapshot(c, loginUrl, baseUrl) ? test : null;
};

const timeOf = (date) => date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function TestStatus({ test, mode }) {
  if (mode === "guided") return <span className={styles.muted}>Checked when a crawl starts</span>;
  if (!test) return <span className={styles.muted}>Not tested</span>;
  if (test.state === "running") return <span className={styles.muted}>Testing…</span>;
  if (test.state === "logged_in")
    return <span className={styles.ok}>Logged in at {timeOf(test.at)}</span>;
  if (test.state === "error") return <span className={styles.bad}>Couldn&apos;t test</span>;
  return <span className={styles.bad}>Failed at {timeOf(test.at)}</span>;
}

export function SiteCredentialsTab({
  siteId,
  baseUrl,
  requiresAuth,
  loginUrl,
  credentials,
  browser,
  tests,
  onTestsChange,
  onChange,
}) {
  const [selected, setSelected] = useState(0);
  const rootRef = useRef(null);
  const current = Math.min(selected, Math.max(credentials.length - 1, 0));
  const updateCredential = (index, changes) =>
    onChange({
      credentials: credentials.map((c, i) => (i === index ? { ...c, ...changes } : c)),
    });
  const addCredential = () => {
    onChange({ credentials: [...credentials, newCredential()] });
    setSelected(credentials.length);
  };
  const removeCredential = (index) => {
    onChange({ credentials: credentials.filter((_, i) => i !== index) });
    setSelected(Math.max(0, index - 1));
  };
  const setTest = (c, test) => onTestsChange((all) => ({ ...all, [c._key]: test }));
  const runTest = async (c, { report = false } = {}) => {
    const snapshot = testSnapshot(c, loginUrl, baseUrl);
    const at = new Date();
    const invalid = rootRef.current?.querySelector(
      `[data-account="${c._key}"] :is(input, select, textarea):invalid`,
    );
    if (invalid) {
      if (report) invalid.reportValidity();
      setTest(c, { state: "error", snapshot, at, message: "Fill in the missing values first." });
      return;
    }
    if (!baseUrl.trim()) {
      setTest(c, { state: "error", snapshot, at, message: "Enter the base URL on the Site tab." });
      return;
    }
    setTest(c, { state: "running", snapshot, at });
    try {
      const result = await sitesApi.testLogin({
        base_url: baseUrl.trim(),
        login_url: loginUrl.trim() || null,
        site_id: siteId ?? null,
        credential: credentialPayload(c),
      });
      setTest(c, { state: result.status, snapshot, at: new Date(), result });
    } catch (e) {
      setTest(c, { state: "error", snapshot, at: new Date(), message: e.message });
    }
  };
  const testable = credentials.filter((c) => c.auth_mode !== "guided");
  const anyRunning = credentials.some((c) => tests[c._key]?.state === "running");
  const testAll = async () => {
    for (const c of testable) await runTest(c);
  };

  return (
    <div className={styles.panelBody} ref={rootRef}>
      <div className={styles.loginToggleRow}>
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={requiresAuth}
            onChange={(e) => onChange({ requires_auth: e.target.checked })}
          />
          <span>This site requires login</span>
        </label>
        {requiresAuth && testable.length > 0 && (
          <button
            type="button"
            className="btn secondary sm"
            disabled={anyRunning}
            onClick={testAll}
          >
            Test all logins
          </button>
        )}
      </div>
      {requiresAuth && (
        <>
          <div className="field">
            <label htmlFor="site-login-url">Default login page URL</label>
            <input
              id="site-login-url"
              type="url"
              value={loginUrl}
              placeholder="https://target.example.com/login"
              onChange={(e) => onChange({ login_url: e.target.value })}
            />
          </div>
          <div className={styles.accounts}>
            <div className={styles.accountList}>
              <div className={styles.listHeading}>Accounts</div>
              {credentials.length === 0 && <div className="subtle">No accounts yet.</div>}
              {credentials.map((c, i) => (
                <button
                  type="button"
                  key={c._key}
                  className={`${styles.accountItem}${i === current ? ` ${styles.selected}` : ""}`}
                  aria-pressed={i === current}
                  onClick={() => setSelected(i)}
                >
                  <span className={styles.accountName}>{accountName(c, i)}</span>
                  <span className={styles.accountMeta}>{methodLabel(c.auth_mode)}</span>
                  <span className={styles.accountMeta}>
                    <TestStatus
                      test={currentTest(tests, c, loginUrl, baseUrl)}
                      mode={c.auth_mode}
                    />
                  </span>
                </button>
              ))}
              <button type="button" className="btn secondary sm" onClick={addCredential}>
                <IconPlus /> Add account
              </button>
              {testable.length > 0 && (
                <p className="field-hint">
                  A test logs in with a hidden browser. If filling the form isn&apos;t enough, it
                  asks the crawler model what to do next.
                </p>
              )}
            </div>
            {credentials.map((c, i) => (
              <AccountEditor
                key={c._key}
                hidden={i !== current}
                credential={c}
                defaultLoginUrl={loginUrl}
                browser={browser}
                test={currentTest(tests, c, loginUrl, baseUrl)}
                onTest={() => runTest(c, { report: true })}
                onShow={() => setSelected(i)}
                onChange={(changes) => updateCredential(i, changes)}
                onRemove={() => removeCredential(i)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function AccountEditor({
  hidden,
  credential: c,
  defaultLoginUrl,
  browser,
  test,
  onTest,
  onShow,
  onChange,
  onRemove,
}) {
  const id = useId();
  const [overrideOpen, setOverrideOpen] = useState(() => Boolean(c.login_url));
  const mode = c.auth_mode || "auto";
  const noDisplay = browser?.graphical_display_available === false;
  const updateField = (index, changes) =>
    onChange({
      login_fields: c.login_fields.map((field, i) =>
        i === index ? { ...field, ...changes } : field,
      ),
    });

  return (
    <div
      className={styles.accountEditor}
      data-account={c._key}
      hidden={hidden}
      onInvalidCapture={(event) => {
        onShow();
        if (event.target.closest("details")) setOverrideOpen(true);
      }}
    >
      <div className={styles.twoCol}>
        <div className="field">
          <label htmlFor={`${id}-label`}>
            Account label <span className="field-optional">(optional)</span>
          </label>
          <input
            id={`${id}-label`}
            type="text"
            value={c.label}
            placeholder="e.g. Test policyholder"
            onChange={(e) => onChange({ label: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor={`${id}-method`}>Login method</label>
          <select
            id={`${id}-method`}
            value={mode}
            title={noDisplay ? browser.graphical_display_message : undefined}
            onChange={(e) => onChange({ auth_mode: e.target.value })}
          >
            {LOGIN_METHODS.map((method) => (
              <option
                key={method.value}
                value={method.value}
                disabled={method.value === "guided" && noDisplay}
              >
                {method.label}
              </option>
            ))}
          </select>
          {noDisplay && <div className="field-hint">{browser.graphical_display_message}</div>}
        </div>
      </div>

      <div className={styles.loginFields}>
        <div className={styles.listHeading}>Login fields</div>
        <div className={`${styles.loginFieldRow} ${styles.loginFieldHead}`} aria-hidden="true">
          <span>Field</span>
          <span>Value</span>
          <span>Hidden</span>
          <span>CSS selector</span>
          <span />
        </div>
        {c.login_fields.map((field, index) => (
          <div className={styles.loginFieldRow} key={index}>
            <input
              type="text"
              required
              aria-label="Field name"
              value={field.label}
              placeholder="e.g. Policy Number"
              onChange={(e) => updateField(index, { label: e.target.value })}
            />
            <input
              type={field.sensitive ? "password" : "text"}
              required
              aria-label={`${field.label || "Field"} value`}
              value={field.value}
              onChange={(e) => updateField(index, { value: e.target.value })}
            />
            <label className={styles.hideToggle}>
              <input
                type="checkbox"
                aria-label={`Hide ${field.label || "field"} value`}
                checked={Boolean(field.sensitive)}
                onChange={(e) => updateField(index, { sensitive: e.target.checked })}
              />
              <span>Hidden</span>
            </label>
            <input
              type="text"
              aria-label={`${field.label || "Field"} CSS selector`}
              value={field.selector || ""}
              placeholder="optional"
              onChange={(e) => updateField(index, { selector: e.target.value })}
            />
            <button
              type="button"
              className="btn ghost sm"
              aria-label={`Remove ${field.label || "field"}`}
              disabled={c.login_fields.length === 1}
              onClick={() =>
                onChange({ login_fields: c.login_fields.filter((_, i) => i !== index) })
              }
            >
              ×
            </button>
          </div>
        ))}
        <button
          type="button"
          className="btn secondary sm"
          onClick={() =>
            onChange({
              login_fields: [
                ...c.login_fields,
                {
                  key: `field_${c.login_fields.length + 1}`,
                  label: "",
                  value: "",
                  sensitive: false,
                  selector: "",
                },
              ],
            })
          }
        >
          <IconPlus /> Add field
        </button>
      </div>

      {["totp", "entra_id"].includes(mode) && (
        <div className="field">
          <label htmlFor={`${id}-totp`}>
            TOTP seed{" "}
            <span className="field-optional">
              {mode === "entra_id"
                ? '(optional, for Entra "other app" code mode)'
                : "(base32 secret from authenticator app)"}
            </span>
          </label>
          <input
            id={`${id}-totp`}
            type="text"
            value={c.totp_seed || ""}
            placeholder="JBSWY3DPEHPK3PXP…"
            onChange={(e) => onChange({ totp_seed: e.target.value })}
          />
        </div>
      )}
      {mode === "email_otp" && (
        <div className="field">
          <label htmlFor={`${id}-mailbox`}>Test mailbox URL</label>
          <input
            id={`${id}-mailbox`}
            type="url"
            required
            value={c.test_mailbox_url || ""}
            placeholder="https://mail.example.test/inbox/test-user"
            onChange={(e) => onChange({ test_mailbox_url: e.target.value })}
          />
        </div>
      )}
      {mode === "guided" && (
        <div className={styles.note}>
          A browser window opens when a crawl or Dynamic Scan starts. Complete the login, including
          any SSO, MFA, or push prompts, then click <strong>I&apos;m Done</strong> in the run view.
          ALICE reuses the session from whichever phase runs first.
        </div>
      )}
      {mode === "entra_id" && (
        <div className={styles.note}>
          Handles Microsoft Entra ID pages for username, password, consent, account picker,
          stay-signed-in, Authenticator number matching, and TOTP codes. MFA policies that need
          manual steps may still need &quot;Log in myself in a browser&quot;.
        </div>
      )}

      <details
        className={styles.override}
        open={overrideOpen}
        onToggle={(e) => setOverrideOpen(e.currentTarget.open)}
      >
        <summary>Override login page URL</summary>
        <input
          type="url"
          aria-label="Login page URL for this account"
          value={c.login_url || ""}
          placeholder={
            defaultLoginUrl
              ? `Uses default: ${defaultLoginUrl}`
              : "Required if no default login URL"
          }
          onChange={(e) => onChange({ login_url: e.target.value })}
        />
      </details>

      {test && test.state !== "running" && <TestResult test={test} />}

      <div className={styles.editorActions}>
        <button type="button" className="btn ghost sm" onClick={onRemove}>
          Remove account
        </button>
        <button
          type="button"
          className="btn secondary sm"
          disabled={mode === "guided" || test?.state === "running"}
          title={
            mode === "guided" ? "This login method is checked when a crawl starts." : undefined
          }
          onClick={onTest}
        >
          {test?.state === "running" ? "Testing…" : test ? "Test again" : "Test login"}
        </button>
      </div>
    </div>
  );
}

function TestResult({ test }) {
  const { result } = test;
  const passed = test.state === "logged_in";
  return (
    <div
      className={`${styles.testResult} ${passed ? styles.testPassed : styles.testFailed}`}
      role="status"
    >
      <div className={styles.testTitle}>
        {passed
          ? "Login worked"
          : test.state === "error"
            ? "Couldn't run the test"
            : "Login failed"}
      </div>
      <div>{result?.message || test.message}</div>
      {result?.page_message && (
        <div>
          The page says: <q>{result.page_message}</q>
        </div>
      )}
      {result?.final_url && (
        <div className={styles.muted}>
          Ended on <code>{result.final_url}</code>
        </div>
      )}
      {result?.screenshot && (
        <details>
          <summary>Screenshot of the last page</summary>
          <img className={styles.testShot} src={result.screenshot} alt="Last page after login" />
        </details>
      )}
    </div>
  );
}
