import { useState, useMemo } from "react";
import { useTargets } from "./useTargets";
import { useHints } from "./useHints";
import { MultiSelectSearch } from "./MultiSelectSearch";
import { EmptyState } from "../../components/EmptyState";
import { IconPlus } from "../../components/Icons";

// ── TargetsTab ───────────────────────────────────────────────────────────────
// Attach/detach existing Sites and API Collections via a searchable
// multi-select, plus optional component ownership links and connection hints.

export function TargetsTab({ applicationId, components, onChanged }) {
  const { targets, allSites, allApiCollections, error, setError, attachMany, detach, setComponent } = useTargets(applicationId, onChanged);
  const { hints, error: hintError, setError: setHintError, create: createHint, remove: removeHint } = useHints(applicationId, onChanged);
  const [picking, setPicking] = useState(false);

  const attachedSiteIds = useMemo(() => new Set((targets || []).filter(t => t.target_type === "site").map(t => t.target_id)), [targets]);
  const attachedApiIds = useMemo(() => new Set((targets || []).filter(t => t.target_type === "api_collection").map(t => t.target_id)), [targets]);

  return <div>
    {error && <div className="alert error" style={{ marginBottom: 16 }}>{error}</div>}
    <div className="row spread" style={{ marginBottom: 14 }}>
      <div className="form-section-title" style={{ margin: 0, border: "none", padding: 0 }}>Live targets</div>
      <button className="btn secondary sm" onClick={() => setPicking(p => !p)}><IconPlus /> Attach targets</button>
    </div>

    {picking && <AttachTargetsPicker
      allSites={allSites}
      allApiCollections={allApiCollections}
      attachedSiteIds={attachedSiteIds}
      attachedApiIds={attachedApiIds}
      onCancel={() => setPicking(false)}
      onAttach={async items => { await attachMany(items).catch(e => setError(e.message)); setPicking(false); }}
    />}

    {targets === null && <div className="subtle">Loading…</div>}
    {targets !== null && targets.length === 0 && !picking && <EmptyState
      title="No live targets attached"
      sub="Attach the Sites and API Collections that make up this application's live surface so a campaign can test them."
      action={<button className="btn" onClick={() => setPicking(true)}><IconPlus /> Attach targets</button>} />}
    {targets && targets.length > 0 && <div className="app-target-list">
      {targets.map(t => <div key={t.id} className="app-target-row">
        <div style={{ flex: 1, minWidth: 220 }}>
          <div className="row" style={{ gap: 8 }}>
            <span className="badge neutral">{t.target_type === "site" ? "Site" : "API collection"}</span>
            <span style={{ fontWeight: 600 }}>{t.name || `#${t.target_id}`}</span>
          </div>
          <label className="subtle" style={{ display: "block", fontSize: 12, marginTop: 8 }}>
            Code component <span style={{ fontWeight: 400 }}>(optional)</span>
            <select
              className="select"
              value={t.component_id || ""}
              onChange={e => setComponent(t.id, e.target.value ? +e.target.value : null).catch(err => setError(err.message))}
              style={{ display: "block", marginTop: 4, maxWidth: 320 }}
            >
              <option value="">No explicit component</option>
              {(components || []).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
        </div>
        <button className="btn danger-outline sm" onClick={() => {
          if (!confirm(`Detach "${t.name || t.target_id}" from this application?`)) return;
          detach(t.id).catch(e => setError(e.status === 409 ? "Cannot detach — it is still referenced by a campaign." : e.message));
        }}>Detach</button>
      </div>)}
    </div>}

    <div className="form-section-title" style={{ marginTop: 28 }}>Connection hints <span className="subtle" style={{ textTransform: "none", fontWeight: 400 }}>(optional)</span></div>
    <div className="subtle" style={{ fontSize: 12, marginBottom: 10 }}>
      Use these for inferred component-to-component communication. An explicit code component selected above automatically routes that component's reportable SAST leads to the target; these hints remain advisory.
    </div>
    {hintError && <div className="alert error" style={{ marginBottom: 12 }}>{hintError}</div>}
    <HintsEditor
      components={components || []}
      targets={targets || []}
      hints={hints}
      onCreate={body => createHint(body).catch(e => setHintError(e.message))}
      onDelete={hintId => removeHint(hintId).catch(e => setHintError(e.message))}
    />
  </div>;
}

function AttachTargetsPicker({ allSites, allApiCollections, attachedSiteIds, attachedApiIds, onCancel, onAttach }) {
  const [selectedSites, setSelectedSites] = useState(new Set());
  const [selectedApis, setSelectedApis] = useState(new Set());
  const [saving, setSaving] = useState(false);

  const siteItems = allSites.filter(s => !attachedSiteIds.has(s.id)).map(s => ({ id: s.id, label: s.name }));
  const apiItems = allApiCollections.filter(a => !attachedApiIds.has(a.id)).map(a => ({ id: a.id, label: a.name }));

  const toggleSite = id => setSelectedSites(prev => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const toggleApi = id => setSelectedApis(prev => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; });

  const submit = async () => {
    setSaving(true);
    const items = [
      ...[...selectedSites].map(targetId => ({ targetType: "site", targetId })),
      ...[...selectedApis].map(targetId => ({ targetType: "api_collection", targetId }))
    ];
    await onAttach(items);
    setSaving(false);
  };

  const total = selectedSites.size + selectedApis.size;

  return <div className="card" style={{ marginBottom: 14, maxWidth: 640 }}>
    <div className="row" style={{ gap: 24, flexWrap: "wrap" }}>
      <div style={{ flex: 1, minWidth: 240 }}>
        <label>Sites</label>
        <MultiSelectSearch items={siteItems} selectedIds={selectedSites} onToggle={toggleSite} placeholder="Search sites…" emptyLabel="No unattached sites." />
      </div>
      <div style={{ flex: 1, minWidth: 240 }}>
        <label>API collections</label>
        <MultiSelectSearch items={apiItems} selectedIds={selectedApis} onToggle={toggleApi} placeholder="Search API collections…" emptyLabel="No unattached API collections." />
      </div>
    </div>
    <div className="row spread" style={{ marginTop: 12 }}>
      <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>
      <button type="button" className="btn" disabled={saving || total === 0} onClick={submit}>{saving ? "Attaching…" : `Attach ${total || ""}`.trim()}</button>
    </div>
  </div>;
}

function HintsEditor({ components, targets, hints, onCreate, onDelete }) {
  const [componentId, setComponentId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  const componentName = id => (components.find(c => c.id === id) || {}).name || `#${id}`;
  const targetName = id => { const t = targets.find(x => x.id === id); return t ? (t.name || `#${t.target_id}`) : `#${id}`; };

  const submit = async e => {
    e.preventDefault();
    if (!componentId || !targetId) return;
    setSaving(true);
    await onCreate({ component_id: +componentId, target_id: +targetId, note: note.trim() || null });
    setNote("");
    setSaving(false);
  };

  return <div>
    {hints && hints.length > 0 && <div className="app-hint-list" style={{ marginBottom: 12 }}>
      {hints.map(h => <div key={h.id} className="app-hint-row">
        <span>{componentName(h.component_id)} → {targetName(h.target_id)}</span>
        {h.note && <span className="subtle" style={{ fontSize: 12 }}>{h.note}</span>}
        <button className="btn danger-outline sm" onClick={() => onDelete(h.id)}>Remove</button>
      </div>)}
    </div>}
    {components.length === 0 || targets.length === 0 ? <div className="subtle" style={{ fontSize: 12 }}>Add at least one component and one live target to create a hint.</div> : <form className="row" style={{ gap: 8, flexWrap: "wrap", alignItems: "center" }} onSubmit={submit}>
      <select className="select" value={componentId} onChange={e => setComponentId(e.target.value)}>
        <option value="">Component…</option>
        {components.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
      <span className="subtle">talks to</span>
      <select className="select" value={targetId} onChange={e => setTargetId(e.target.value)}>
        <option value="">Target…</option>
        {targets.map(t => <option key={t.id} value={t.id}>{t.name || `#${t.target_id}`}</option>)}
      </select>
      <input type="text" value={note} onChange={e => setNote(e.target.value)} placeholder="Note (optional)" style={{ minWidth: 180 }} />
      <button type="submit" className="btn secondary sm" disabled={saving || !componentId || !targetId}>Add hint</button>
    </form>}
  </div>;
}
