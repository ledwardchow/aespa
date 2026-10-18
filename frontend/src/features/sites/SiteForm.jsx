import * as sitesApi from "../../shared/api/sites.js";
import * as settingsApi from "../../shared/api/settings.js";
import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";

import { nav } from "../../shared/navigation/router.js";
import { PageHeader, Crumb, Sep } from "../../shared/ui/PageHeader.jsx";
import { Tabs } from "../../shared/ui/Tabs.tsx";
import {
  SiteCredentialsTab,
  credentialFromSite,
  credentialPayload,
  currentTest,
} from "./SiteCredentialsTab.jsx";
import { SiteWorkflowsTab } from "./SiteWorkflowsTab.jsx";
import styles from "./SiteForm.module.css";

const emptyForm = {
  name: "",
  base_url: "",
  requires_auth: false,
  login_url: "",
  notes: "",
  scan_guidance: "",
  workflow_data: [],
  credentials: [],
};

const firstInvalid = (root) =>
  root?.querySelector("input:invalid, select:invalid, textarea:invalid");

const invalidTabs = (root) =>
  new Set(
    [...(root?.querySelectorAll("input:invalid, select:invalid, textarea:invalid") || [])]
      .map((el) => el.closest("[data-tab]")?.dataset.tab)
      .filter(Boolean),
  );

export function SiteForm({ siteId }) {
  const isEdit = typeof siteId === "number";
  const [form, setForm] = useState(emptyForm);
  const [hasSavedWorkflows, setHasSavedWorkflows] = useState(false);
  const [tab, setTab] = useState("site");
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [checked, setChecked] = useState(false);
  const [tabErrors, setTabErrors] = useState(new Set());
  const [browserCapabilities, setBrowserCapabilities] = useState(null);
  const [loginTests, setLoginTests] = useState({});
  const formRef = useRef(null);

  useEffect(() => {
    settingsApi
      .getBrowserDebugConfig()
      .then(setBrowserCapabilities)
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (!isEdit) return;
    (async () => {
      try {
        const d = await sitesApi.getSite(siteId);
        setForm({
          name: d.name,
          base_url: d.base_url,
          requires_auth: d.requires_auth,
          login_url: d.login_url || "",
          notes: d.notes || "",
          scan_guidance: d.scan_guidance || "",
          workflow_data: d.workflow_data || [],
          credentials: d.credentials.map(credentialFromSite),
        });
        setHasSavedWorkflows(Boolean(d.workflow_data?.length));
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [isEdit, siteId]);
  useEffect(() => {
    if (checked) setTabErrors(invalidTabs(formRef.current));
  }, [checked, form]);

  const upd = (p) => setForm((f) => ({ ...f, ...p }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setChecked(true);
    const invalid = firstInvalid(formRef.current);
    if (invalid) {
      // Show the tab, account, or workflow that holds the field before the
      // browser reports it; hidden fields cannot show a validation message.
      flushSync(() => {
        setTab(invalid.closest("[data-tab]")?.dataset.tab || "site");
        invalid.checkValidity();
      });
      invalid.reportValidity();
      return;
    }
    setSaving(true);
    const payload = {
      name: form.name.trim(),
      base_url: form.base_url.trim(),
      requires_auth: form.requires_auth,
      login_url: form.requires_auth ? form.login_url.trim() || null : null,
      notes: form.notes.trim() || null,
      scan_guidance: form.scan_guidance.trim() || null,
      workflow_data: form.workflow_data.map((item) => ({
        name: item.name.trim(),
        goal: item.goal.trim(),
        start_url: item.start_url.trim(),
        instructions: item.instructions.trim(),
      })),
      credentials: form.requires_auth ? form.credentials.map(credentialPayload) : [],
    };
    try {
      if (isEdit) {
        await sitesApi.updateSite(siteId, payload);
        nav(`#/sites/${siteId}`);
      } else {
        const s = await sitesApi.createSite(payload);
        nav(`#/sites/${s.id}`);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const failedLogins = form.requires_auth
    ? form.credentials.filter((c) =>
        ["failed", "error"].includes(
          currentTest(loginTests, c, form.login_url, form.base_url)?.state,
        ),
      ).length
    : 0;
  const tabLabel = (key, text, count, failed = 0) => (
    <>
      {text}
      {count > 0 && <span className={styles.count}>{count}</span>}
      {failed > 0 && <span className={styles.failedCount}>{failed} failed</span>}
      {tabErrors.has(key) && (
        <span className={styles.tabError} title="Has fields to fix">
          !
        </span>
      )}
    </>
  );
  const tabs = [
    { key: "site", label: tabLabel("site", "Site") },
    {
      key: "credentials",
      label: tabLabel(
        "credentials",
        "Credentials",
        form.requires_auth ? form.credentials.length : 0,
        failedLogins,
      ),
    },
    ...(hasSavedWorkflows
      ? [{ key: "workflows", label: tabLabel("workflows", "Workflows", form.workflow_data.length) }]
      : []),
    { key: "instructions", label: tabLabel("instructions", "Instructions") },
  ];

  const bc = isEdit ? (
    <>
      <Crumb href={`#/sites/${siteId}`}>{form.name || "Site"}</Crumb>
      <Sep />
      Edit
    </>
  ) : (
    "New site"
  );
  return (
    <>
      <PageHeader title={bc} />
      {loading ? (
        <div className="content">
          <div className="subtle">Loading…</div>
        </div>
      ) : (
        <form ref={formRef} className={`content ${styles.page}`} noValidate onSubmit={onSubmit}>
          <Tabs label="Site settings" tabs={tabs} value={tab} onChange={setTab} />
          <div className={styles.scroll}>
            <div className={styles.panel} data-tab="site" hidden={tab !== "site"}>
              <div className={styles.panelBody}>
                <div className={styles.twoCol}>
                  <div className="field">
                    <label htmlFor="site-name">Name</label>
                    <input
                      id="site-name"
                      type="text"
                      required
                      value={form.name}
                      placeholder="e.g. Juice Shop"
                      onChange={(e) => upd({ name: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="site-base-url">Base URL</label>
                    <input
                      id="site-base-url"
                      type="url"
                      required
                      value={form.base_url}
                      placeholder="https://target.example.com"
                      onChange={(e) => upd({ base_url: e.target.value })}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="site-notes">
                    Notes <span className="field-optional">(optional)</span>
                  </label>
                  <textarea
                    id="site-notes"
                    rows={4}
                    value={form.notes}
                    placeholder="Scope, contacts…"
                    onChange={(e) => upd({ notes: e.target.value })}
                  />
                  <div className="field-hint">
                    For you and your team. Not sent to the testing agents.
                  </div>
                </div>
              </div>
            </div>
            <div className={styles.panel} data-tab="credentials" hidden={tab !== "credentials"}>
              <SiteCredentialsTab
                siteId={isEdit ? siteId : null}
                baseUrl={form.base_url}
                requiresAuth={form.requires_auth}
                loginUrl={form.login_url}
                credentials={form.credentials}
                browser={browserCapabilities}
                tests={loginTests}
                onTestsChange={setLoginTests}
                onChange={upd}
              />
            </div>
            {hasSavedWorkflows && (
              <div className={styles.panel} data-tab="workflows" hidden={tab !== "workflows"}>
                <SiteWorkflowsTab
                  workflows={form.workflow_data}
                  onChange={(workflow_data) => upd({ workflow_data })}
                />
              </div>
            )}
            <div className={styles.panel} data-tab="instructions" hidden={tab !== "instructions"}>
              <div className={styles.panelBody}>
                <div className="field">
                  <label htmlFor="site-guidance">Instructions for the testing agents</label>
                  <textarea
                    id="site-guidance"
                    rows={14}
                    value={form.scan_guidance}
                    placeholder="How to finish a tricky login, what to focus on, what to avoid…"
                    onChange={(e) => upd({ scan_guidance: e.target.value })}
                  />
                  <div className="field-hint">Sent to the testing agents as written.</div>
                </div>
              </div>
            </div>
          </div>
          <div className={styles.footer}>
            <button
              type="button"
              className="btn ghost"
              onClick={() => (isEdit ? nav(`#/sites/${siteId}`) : nav("#/"))}
            >
              Cancel
            </button>
            {error && (
              <div className={`alert error ${styles.footerError}`} role="alert">
                {error}
              </div>
            )}
            <button type="submit" className="btn" disabled={saving}>
              {saving ? "Saving…" : isEdit ? "Save changes" : "Create site"}
            </button>
          </div>
        </form>
      )}
    </>
  );
}
