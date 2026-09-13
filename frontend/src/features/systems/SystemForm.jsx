import * as systemsApi from "../../shared/api/systems.js";
import { useState, useEffect } from "react";

import { nav } from "../../shared/navigation/router.js";
import { PageHeader, Crumb, Sep } from "../../shared/ui/PageHeader.jsx";

// ── SystemForm ──────────────────────────────────────────────────────────
// Create or edit a System's name/description. Everything else (code
// components, live targets, hints, campaigns) is managed from SystemDetail.

export function SystemForm({ systemId }) {
  const editing = systemId != null;
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!editing) return;
    systemsApi
      .getSystem(systemId)
      .then((a) => {
        setName(a.name || "");
        setDescription(a.description || "");
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, [systemId, editing]);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const body = { name: name.trim(), description: description.trim() || null };
      const app = editing
        ? await systemsApi.updateSystem(systemId, body)
        : await systemsApi.createSystem(body);
      nav(`#/systems/${app.id}`);
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  };

  if (loading)
    return (
      <div className="content scroll-content">
        <div className="subtle">Loading…</div>
      </div>
    );

  return (
    <>
      <PageHeader
        title={
          <>
            <Crumb href="#/systems">Systems</Crumb>
            <Sep />
            {editing ? "Edit system" : "New system"}
          </>
        }
      />
      <div className="content scroll-content">
        <form className="card" style={{ maxWidth: 560 }} onSubmit={onSubmit}>
          <div className="form-section-title">{editing ? "Edit system" : "New system"}</div>
          {error && <div className="alert error">{error}</div>}
          <div className="field">
            <label>
              Name <span className="field-required">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Acme Customer Portal"
              autoFocus
            />
          </div>
          <div className="field">
            <label>
              Description <span className="subtle">(optional)</span>
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What this system is and how its parts fit together."
            />
          </div>
          <div className="row spread" style={{ marginTop: 16 }}>
            <button
              type="button"
              className="btn ghost"
              onClick={() => nav(editing ? `#/systems/${systemId}` : "#/systems")}
            >
              Cancel
            </button>
            <button type="submit" className="btn" disabled={saving || !name.trim()}>
              {saving ? "Saving…" : editing ? "Save" : "Create system"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
