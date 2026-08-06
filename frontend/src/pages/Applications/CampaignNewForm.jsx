import { useState, useMemo, useEffect } from "react";
import { api } from "../../lib/api";
import { nav } from "../../lib/router";
import { PageHeader, Crumb, Sep } from "../../components/PageHeader";
import { EmptyState } from "../../components/EmptyState";
import { useCampaignWizardData } from "./useCampaignWizardData";
import { formatBytes, shortHash } from "./_helpers";

// ── CampaignNewForm ──────────────────────────────────────────────────────────
// A short guided setup rather than one giant form: pick snapshots, pick
// targets, pick a profile/parallelism, then a frozen-selection review before
// creating (and starting) the campaign. All application targets and each
// component's latest snapshot are preselected per the plan.

export function CampaignNewForm({ applicationId }) {
  const { components, snapshotsByComponent, targets, profiles, error, setError } = useCampaignWizardData(applicationId);
  const [step, setStep] = useState("configure"); // "configure" | "review"
  const [name, setName] = useState("");
  const [includedComponents, setIncludedComponents] = useState(new Set());
  const [snapshotChoice, setSnapshotChoice] = useState({}); // component_id -> snapshot_id
  const [includedTargets, setIncludedTargets] = useState(new Set());
  const [llmProfileId, setLlmProfileId] = useState("");
  const [maxParallel, setMaxParallel] = useState(2);
  const [traceEdges, setTraceEdges] = useState("");
  const [traceComponents, setTraceComponents] = useState("");
  const [tracePaths, setTracePaths] = useState("");
  const [traceConfidence, setTraceConfidence] = useState("");
  const [saving, setSaving] = useState(false);
  // Set the instant POST /campaigns succeeds, before the start call — this
  // is what makes a retry after a failed start safe: onCreate below never
  // creates a second campaign once this is non-null, it only retries
  // starting the one that already exists.
  const [createdCampaignId, setCreatedCampaignId] = useState(null);

  // Preselect: every component that has at least one snapshot (latest
  // preselected), and every attached target.
  useEffect(() => {
    if (!components) return;
    const eligible = components.filter(c => c.latest_snapshot);
    setIncludedComponents(new Set(eligible.map(c => c.id)));
    const choices = {};
    eligible.forEach(c => { choices[c.id] = c.latest_snapshot.id; });
    setSnapshotChoice(choices);
  }, [components]);

  useEffect(() => {
    if (!targets) return;
    setIncludedTargets(new Set(targets.map(t => t.id)));
  }, [targets]);

  const missingSnapshotComponents = (components || []).filter(c => !c.latest_snapshot);

  const toggleComponent = id => setIncludedComponents(prev => {
    const n = new Set(prev);
    if (n.has(id)) n.delete(id); else n.add(id);
    return n;
  });
  const toggleTarget = id => setIncludedTargets(prev => {
    const n = new Set(prev);
    if (n.has(id)) n.delete(id); else n.add(id);
    return n;
  });

  const sourceMembers = useMemo(() => [...includedComponents].map(id => ({
    component_id: id, snapshot_id: snapshotChoice[id]
  })).filter(m => m.snapshot_id), [includedComponents, snapshotChoice]);

  const targetMembers = useMemo(() => [...includedTargets].map(id => ({ target_id: id })), [includedTargets]);

  const canProceed = name.trim() && sourceMembers.length > 0 && targetMembers.length > 0;

  const onCreate = async () => {
    setSaving(true);
    setError(null);
    try {
      let id = createdCampaignId;
      if (id == null) {
        const body = {
          name: name.trim(),
          source_members: sourceMembers,
          target_members: targetMembers,
          llm_profile_id: llmProfileId ? +llmProfileId : null,
          max_parallel_sast: maxParallel,
          max_trace_edges: traceEdges ? +traceEdges : null,
          max_trace_components: traceComponents ? +traceComponents : null,
          max_paths_per_lead: tracePaths ? +tracePaths : null,
          min_trace_confidence: traceConfidence ? +traceConfidence : null
        };
        const campaign = await api.createCampaign(applicationId, body);
        id = campaign.id;
        // Commit this before the start call can throw — a second click of
        // "Create & start"/"Retry start" after a failed start will see this
        // and only retry starting, never re-run createCampaign.
        setCreatedCampaignId(id);
      }
      await api.startCampaign(applicationId, id);
      nav(`#/applications/${applicationId}/campaigns/${id}/overview`);
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  };

  const onOpenDraft = () => nav(`#/applications/${applicationId}/campaigns/${createdCampaignId}/overview`);

  if (components === null || targets === null) {
    return <div className="content scroll-content">{error ? <div className="alert error">{error}</div> : <div className="subtle">Loading…</div>}</div>;
  }

  if (components.every(c => !c.latest_snapshot) || targets.length === 0) {
    return <>
      <PageHeader title={<><Crumb href={`#/applications/${applicationId}`}>Application</Crumb><Sep />New campaign</>} />
      <div className="content scroll-content">
        <EmptyState
          title="Not ready for a campaign yet"
          sub="A campaign needs at least one component with an uploaded snapshot and at least one attached live target."
          action={<button className="btn" onClick={() => nav(`#/applications/${applicationId}/components`)}>Go to Code Components</button>} />
      </div>
    </>;
  }

  return <>
    <PageHeader title={<><Crumb href={`#/applications/${applicationId}`}>Application</Crumb><Sep />New campaign</>} />
    <div className="content scroll-content">
      {error && <div className="alert error" style={{ marginBottom: 16 }}>{error}</div>}
      {step === "configure" && <div className="card" style={{ maxWidth: 720, display: "flex", flexDirection: "column", gap: 20 }}>
        <div className="field">
          <label>Campaign name <span className="field-required">*</span></label>
          <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. August release" autoFocus />
        </div>

        <div>
          <div className="form-section-title">1. Code snapshots</div>
          {missingSnapshotComponents.length > 0 && <div className="alert warning" style={{ marginBottom: 10 }}>
            {missingSnapshotComponents.map(c => c.name).join(", ")} {missingSnapshotComponents.length === 1 ? "has" : "have"} no uploaded snapshot and cannot be included.
          </div>}
          {components.filter(c => c.latest_snapshot).map(c => <div key={c.id} className="app-wizard-row">
            <label className="row" style={{ gap: 8, flex: 1 }}>
              <input type="checkbox" checked={includedComponents.has(c.id)} onChange={() => toggleComponent(c.id)} />
              <span style={{ fontWeight: 600 }}>{c.name}</span>
            </label>
            <select
              className="select"
              disabled={!includedComponents.has(c.id)}
              value={snapshotChoice[c.id] || ""}
              onChange={e => setSnapshotChoice(prev => ({ ...prev, [c.id]: +e.target.value }))}
            >
              {(snapshotsByComponent[c.id] || [c.latest_snapshot]).map(s => <option key={s.id} value={s.id}>
                {s.filename} · {shortHash(s.sha256)} · {formatBytes(s.size_bytes)}{s.id === c.latest_snapshot.id ? " (latest)" : ""}
              </option>)}
            </select>
          </div>)}
        </div>

        <div>
          <div className="form-section-title">2. Live targets</div>
          {targets.map(t => <label key={t.id} className="app-wizard-row" style={{ gap: 8 }}>
            <input type="checkbox" checked={includedTargets.has(t.id)} onChange={() => toggleTarget(t.id)} />
            <span className="badge neutral">{t.target_type === "site" ? "Site" : "API collection"}</span>
            <span style={{ fontWeight: 600 }}>{t.name || `#${t.target_id}`}</span>
          </label>)}
        </div>

        <div>
          <div className="form-section-title">3. Scan profile &amp; parallelism</div>
          <div className="row" style={{ gap: 20, flexWrap: "wrap", marginTop: 10 }}>
            <div className="field" style={{ minWidth: 240 }}>
              <label>LLM profile <span className="subtle">(optional)</span></label>
              <select className="select" value={llmProfileId} onChange={e => setLlmProfileId(e.target.value)}>
                <option value="">— Use global active profile —</option>
                {profiles.map(p => <option key={p.id} value={p.id}>{p.name}{p.default_model_name ? ` · ${p.default_model_name}` : ""}</option>)}
              </select>
            </div>
            <div className="field" style={{ minWidth: 180 }}>
              <label>Max parallel code scans</label>
              <input type="number" min={1} max={8} value={maxParallel} onChange={e => setMaxParallel(Math.min(8, Math.max(1, +e.target.value || 1)))} />
            </div>
            <div className="field" style={{ minWidth: 180 }}>
              <label>Trace edges <span className="subtle">(optional)</span></label>
              <input type="number" min={1} max={64} value={traceEdges} onChange={e => setTraceEdges(e.target.value)} placeholder="Global default" />
            </div>
            <div className="field" style={{ minWidth: 180 }}>
              <label>Trace components <span className="subtle">(optional)</span></label>
              <input type="number" min={1} max={32} value={traceComponents} onChange={e => setTraceComponents(e.target.value)} placeholder="Global default" />
            </div>
            <div className="field" style={{ minWidth: 180 }}>
              <label>Paths per lead <span className="subtle">(optional)</span></label>
              <input type="number" min={1} max={100} value={tracePaths} onChange={e => setTracePaths(e.target.value)} placeholder="Global default" />
            </div>
            <div className="field" style={{ minWidth: 180 }}>
              <label>Min trace confidence <span className="subtle">(optional)</span></label>
              <input type="number" min={0} max={1} step={0.05} value={traceConfidence} onChange={e => setTraceConfidence(e.target.value)} placeholder="Global default" />
            </div>
          </div>
        </div>

        <div className="row spread">
          <button type="button" className="btn ghost" onClick={() => nav(`#/applications/${applicationId}/campaigns`)}>Cancel</button>
          <button type="button" className="btn" disabled={!canProceed} onClick={() => setStep("review")}>Review &amp; create</button>
        </div>
      </div>}

      {step === "review" && <ReviewStep
        name={name}
        components={components}
        sourceMembers={sourceMembers}
        targets={targets}
        targetMembers={targetMembers}
        llmProfile={profiles.find(p => String(p.id) === String(llmProfileId))}
        maxParallel={maxParallel}
        traceOverrides={{ traceEdges, traceComponents, tracePaths, traceConfidence }}
        saving={saving}
        createdCampaignId={createdCampaignId}
        onBack={() => setStep("configure")}
        onCreate={onCreate}
        onOpenDraft={onOpenDraft}
      />}
    </div>
  </>;
}

function ReviewStep({ name, components, sourceMembers, targets, targetMembers, llmProfile, maxParallel, traceOverrides, saving, createdCampaignId, onBack, onCreate, onOpenDraft }) {
  const componentName = id => (components.find(c => c.id === id) || {}).name || `#${id}`;
  const targetById = id => targets.find(t => t.id === id);
  const created = createdCampaignId != null;
  return <div className="card" style={{ maxWidth: 720, display: "flex", flexDirection: "column", gap: 16 }}>
    <div className="form-section-title">Frozen selection — review</div>
    <div className="alert warning">
      This exact snapshot and target selection is frozen for this campaign. Changing the application later (new snapshots, attaching/detaching targets) will not alter it.
    </div>
    {created && <div className="alert warning">
      This campaign was already created (draft) — starting it failed. Retrying below only starts that same draft; it never creates a second campaign. Editing the selection above no longer applies to it — open the draft if you need to change anything.
    </div>}
    <div><strong>{name}</strong></div>
    <div>
      <div className="subtle" style={{ fontWeight: 700, marginBottom: 6 }}>Code snapshots ({sourceMembers.length})</div>
      {sourceMembers.map(m => <div key={m.component_id} className="app-wizard-row"><span>{componentName(m.component_id)}</span></div>)}
    </div>
    <div>
      <div className="subtle" style={{ fontWeight: 700, marginBottom: 6 }}>Live targets ({targetMembers.length})</div>
      {targetMembers.map(m => {
        const t = targetById(m.target_id);
        return <div key={m.target_id} className="app-wizard-row">
          <span className="badge neutral">{t?.target_type === "site" ? "Site" : "API collection"}</span>
          <span>{t?.name || `#${m.target_id}`}</span>
        </div>;
      })}
    </div>
    <div className="subtle">
      LLM profile: {llmProfile ? `${llmProfile.name}${llmProfile.default_model_name ? ` · ${llmProfile.default_model_name}` : ""}` : "global active profile"} · Max parallel scans: {maxParallel} · Trace overrides: {Object.values(traceOverrides).some(Boolean) ? "custom" : "global defaults"}
    </div>
    <div className="row spread">
      <button type="button" className="btn ghost" onClick={onBack} disabled={saving || created} title={created ? "This draft is already created — go to the application's Campaigns tab for a fresh attempt instead." : undefined}>Back</button>
      <div className="row" style={{ gap: 8 }}>
        {created && <button type="button" className="btn secondary" disabled={saving} onClick={onOpenDraft}>Open draft</button>}
        <button type="button" className="btn" disabled={saving} onClick={onCreate}>{saving ? "Starting…" : created ? "Retry start" : "Create & start campaign"}</button>
      </div>
    </div>
  </div>;
}
