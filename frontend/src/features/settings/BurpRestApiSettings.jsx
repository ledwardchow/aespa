import * as settingsApi from "../../shared/api/settings.js";
import { useState, useEffect } from "react";
import { burpRestApiPayload, burpRestApiToForm } from "./burpForm.js";

import { IconCheck } from "../../shared/ui/Icons.jsx";

export function BurpRestApiSettings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [connTest, setConnTest] = useState(null);
  const [connTesting, setConnTesting] = useState(false);
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
        setForm(burpRestApiToForm(await settingsApi.getBurpRestApiConfig()));
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
      const savedConfig = await settingsApi.upsertBurpRestApiConfig(burpRestApiPayload(form));
      setForm(burpRestApiToForm(savedConfig));
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };
  const onTestConnection = async () => {
    setConnTest(null);
    setConnTesting(true);
    try {
      const result = await settingsApi.testBurpConnection();
      setConnTest(result);
    } catch (e) {
      setConnTest({
        ok: false,
        message: e.message,
      });
    } finally {
      setConnTesting(false);
    }
  };
  return (
    <>
      {!form && !error && <div className="subtle">Loading…</div>}
      {error && <div className="alert error">{error}</div>}
      {form && (
        <form className="card" onSubmit={onSubmit}>
          <div className="form-section-title">Burp Suite Active Scan</div>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(e) =>
                upd({
                  enabled: e.target.checked,
                })
              }
            />
            <span>Enable Burp Suite active scan integration</span>
          </label>
          <div
            className="field-hint"
            style={{
              marginBottom: "12px",
            }}
          >
            When enabled, the scanner automatically triggers Burp Suite active scans for enabled
            vulnerability classes as the LLM discovers candidate endpoints. Requires Burp Suite
            Professional with the REST API enabled (Burp menu → Settings → Suite → REST API).
          </div>
          <div className="field">
            <label>REST API URL</label>
            <input
              type="url"
              required
              value={form.api_url}
              placeholder="http://127.0.0.1:1337"
              onChange={(e) =>
                upd({
                  api_url: e.target.value,
                })
              }
            />
            <div className="field-hint">
              Default: http://127.0.0.1:1337. Configure under Burp → Settings → Suite → REST API.
            </div>
          </div>
          <div className="field">
            <label>
              API key <span className="subtle">(optional)</span>
            </label>
            <div className="row" style={{ gap: "8px" }}>
              <input
                type="password"
                value={form.api_key}
                placeholder={
                  form.clear_api_key
                    ? "Key will be removed on save"
                    : form.has_api_key && !form.api_key
                      ? "•••••••• (leave blank to keep current key)"
                      : "Leave blank if not configured"
                }
                onChange={(e) =>
                  upd({
                    api_key: e.target.value,
                    clear_api_key: false,
                  })
                }
                style={{ flex: 1 }}
              />
              {form.has_api_key &&
                (form.clear_api_key ? (
                  <button
                    type="button"
                    className="btn ghost"
                    onClick={() => upd({ clear_api_key: false })}
                  >
                    Undo clear
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn ghost"
                    onClick={() => upd({ clear_api_key: true, api_key: "" })}
                  >
                    Clear key
                  </button>
                ))}
            </div>
            <div className="field-hint">
              Set an API key in Burp REST API settings and paste it here for authentication.
            </div>
          </div>
          <div className="field">
            <label>
              Scan configuration <span className="subtle">(optional)</span>
            </label>
            <input
              type="text"
              value={form.scan_configuration_name}
              placeholder="Audit checks - all except time-based detection methods"
              onChange={(e) =>
                upd({
                  scan_configuration_name: e.target.value,
                })
              }
            />
            <div className="field-hint">
              Only enter a named configuration that exists in your Burp project. Blank avoids
              Unknown configuration errors.
            </div>
          </div>
          <div className="divider" />
          <div className="form-section-title">Vulnerability Classes to Active Scan</div>
          <div
            className="field-hint"
            style={{
              marginBottom: "8px",
            }}
          >
            When the LLM investigates a selected vulnerability class on a URL, Burp will actively
            scan that endpoint.
          </div>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.scan_sqli}
              onChange={(e) =>
                upd({
                  scan_sqli: e.target.checked,
                })
              }
            />
            <span>SQL Injection (A03)</span>
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.scan_xss}
              onChange={(e) =>
                upd({
                  scan_xss: e.target.checked,
                })
              }
            />
            <span>Cross-Site Scripting / XSS (A03)</span>
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.scan_command_injection}
              onChange={(e) =>
                upd({
                  scan_command_injection: e.target.checked,
                })
              }
            />
            <span>OS Command Injection (A03)</span>
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.scan_path_traversal}
              onChange={(e) =>
                upd({
                  scan_path_traversal: e.target.checked,
                })
              }
            />
            <span>Path Traversal / File Inclusion (A01/A05)</span>
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.scan_ssrf}
              onChange={(e) =>
                upd({
                  scan_ssrf: e.target.checked,
                })
              }
            />
            <span>Server-Side Request Forgery / SSRF (A10)</span>
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.scan_xxe}
              onChange={(e) =>
                upd({
                  scan_xxe: e.target.checked,
                })
              }
            />
            <span>XML External Entity / XXE (A05)</span>
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={form.scan_ssti}
              onChange={(e) =>
                upd({
                  scan_ssti: e.target.checked,
                })
              }
            />
            <span>Server-Side Template Injection / SSTI (A03)</span>
          </label>
          <div className="divider" />
          {connTest && (
            <div
              className={"alert " + (connTest.ok ? "success" : "error")}
              style={{
                marginBottom: "12px",
              }}
            >
              {connTest.message}
            </div>
          )}
          <div className="row spread">
            <div
              className="row"
              style={{
                gap: "8px",
              }}
            >
              {saved && (
                <span className="save-confirm">
                  <IconCheck /> Saved
                </span>
              )}
              <button
                type="button"
                className="btn secondary"
                disabled={connTesting}
                onClick={onTestConnection}
              >
                {connTesting ? "Testing…" : "Test Connection"}
              </button>
            </div>
            <button type="submit" className="btn" disabled={saving}>
              {saving ? "Saving…" : "Save Burp Settings"}
            </button>
          </div>
        </form>
      )}
    </>
  );
}

// Actual runtime defaults used by the backend when base_url is blank
