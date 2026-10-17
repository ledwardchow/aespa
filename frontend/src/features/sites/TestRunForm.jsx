import * as settingsApi from "../../shared/api/settings.js";
import * as sitesApi from "../../shared/api/sites.js";
import { useState, useEffect } from "react";

import { nav } from "../../shared/navigation/router.js";
import { PageHeader, Breadcrumbs } from "../../shared/ui/PageHeader.jsx";
import { useRecordName } from "../../shared/hooks/useRecordName.ts";

export function TestRunForm({ siteId }) {
  const [form, setForm] = useState({
    name: "",
    max_depth: 3,
    max_pages: 500,
    crawler_mode: "url",
    page_selection: "each_url",
    llm_profile_id: null,
    llm_budget_usd: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const upd = (p) =>
    setForm((f) => ({
      ...f,
      ...p,
    }));
  const siteName = useRecordName(sitesApi.getSite, siteId);
  useEffect(() => {
    (async () => {
      try {
        const profs = await settingsApi.listLLMProfiles();
        setProfiles(profs || []);
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);
  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const run = await sitesApi.createRun(siteId, {
        name: form.name.trim() || null,
        max_depth: Number(form.max_depth),
        max_pages: Number(form.max_pages),
        crawler_mode: form.crawler_mode,
        page_selection: form.page_selection,
        llm_profile_id: form.llm_profile_id || null,
        llm_budget_usd: form.llm_budget_usd === "" ? null : Number(form.llm_budget_usd),
      });
      nav(`#/runs/${run.id}`);
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  };
  return (
    <>
      <PageHeader
        title={
          <>
            <Breadcrumbs
              items={[
                { label: "Sites", href: "#/" },
                { label: siteName || "Site", href: `#/sites/${siteId}` },
                { label: "New test run" },
              ]}
            />
          </>
        }
      />
      <div className="content scroll-content">
        <form className="card" onSubmit={onSubmit}>
          <div className="form-section-title">Run Configuration</div>
          <div className="field">
            <label>
              Name <span className="field-optional">(optional — auto-generated if blank)</span>
            </label>
            <input
              type="text"
              value={form.name}
              placeholder="e.g. Initial crawl"
              onChange={(e) =>
                upd({
                  name: e.target.value,
                })
              }
            />
          </div>
          <div className="two-col">
            <div className="field">
              <label>
                Max depth <span className="field-hint-inline">(1–10)</span>
              </label>
              <input
                type="number"
                required
                min="1"
                max="10"
                value={form.max_depth}
                onChange={(e) =>
                  upd({
                    max_depth: e.target.value,
                  })
                }
              />
            </div>
            <div className="field">
              <label>
                Max pages <span className="field-hint-inline">(5–500)</span>
              </label>
              <input
                type="number"
                required
                min="5"
                max="500"
                value={form.max_pages}
                onChange={(e) =>
                  upd({
                    max_pages: e.target.value,
                  })
                }
              />
            </div>
          </div>
          <div className="field">
            <label>Crawler mode</label>
            <select
              className="select"
              value={form.crawler_mode}
              onChange={(e) => upd({ crawler_mode: e.target.value, page_selection: "each_url" })}
            >
              <option value="url">URL crawl</option>
              <option value="interactive">Interactive SPA - major UI change is a page</option>
            </select>
            <div className="field-hint">
              Use "Interactive SPA" mode if your site doesn't change the URL when you navigate.
            </div>
          </div>
          {form.crawler_mode === "url" && (
            <div className="field">
              <label>Page selection</label>
              <select
                className="select"
                value={form.page_selection}
                onChange={(e) => upd({ page_selection: e.target.value })}
              >
                <option value="each_url">Visit each URL (current crawl)</option>
                <option value="group_similar">Group similar pages</option>
              </select>
              <div className="field-hint">
                Group similar pages samples repeated routes, such as large product catalogues. It
                keeps example pages for testing.
              </div>
            </div>
          )}
          <div
            className="alert"
            style={{
              marginTop: 12,
            }}
          >
            This run will use the global scan policy from Settings.
          </div>
          <div className="divider" />
          <div className="form-section-title">LLM Profile</div>
          <div className="field">
            <label>
              LLM profile{" "}
              <span className="field-optional">
                (optional — uses the globally active profile if not set)
              </span>
            </label>
            <select
              className="select"
              value={form.llm_profile_id || ""}
              onChange={(e) =>
                upd({
                  llm_profile_id: e.target.value ? Number(e.target.value) : null,
                })
              }
            >
              <option value="">— Use global active profile —</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>
              LLM budget{" "}
              <span className="field-optional">
                (optional — pauses all LLM work on this run when estimated spend reaches it)
              </span>
            </label>
            <div className="row" style={{ gap: 8 }}>
              <span>$</span>
              <input
                type="number"
                min="0.01"
                step="0.01"
                placeholder="No limit"
                style={{ width: 160 }}
                value={form.llm_budget_usd}
                onChange={(e) => upd({ llm_budget_usd: e.target.value })}
              />
            </div>
          </div>
          {error && (
            <div className="alert error form-error" role="alert">
              {error}
            </div>
          )}
          <div className="row spread">
            <button type="button" className="btn ghost" onClick={() => nav(`#/sites/${siteId}`)}>
              Cancel
            </button>
            <button type="submit" className="btn" disabled={saving}>
              {saving ? "Creating…" : "Create run"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
