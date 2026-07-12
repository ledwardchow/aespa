import { useState, useEffect, useCallback } from "react";
import { truncUrl, fmtDate } from "../../lib/utilities";
import { DebugFindingsTable } from "./DebugFindingsTable";
import { api } from "../../lib/api";
import { IconCheck } from "../../components/Icons";


export function ReportingDebugPage() {
  const [tab, setTab] = useState("prompt");
  const [promptKey, setPromptKey] = useState("reporting.analyse");
  const [promptVersions, setPromptVersions] = useState([]);
  const [selectedPromptVersionId, setSelectedPromptVersionId] = useState("");
  const [promptVersionName, setPromptVersionName] = useState("");
  const [promptText, setPromptText] = useState("");
  const [promptSaving, setPromptSaving] = useState(false);
  const [promptSaved, setPromptSaved] = useState(false);
  const [captures, setCaptures] = useState([]);
  const [captureDbPath, setCaptureDbPath] = useState("");
  const [selectedCaptureId, setSelectedCaptureId] = useState("");
  const [selectedCaptureDetail, setSelectedCaptureDetail] = useState(null);
  const [selectedReplayVersionId, setSelectedReplayVersionId] = useState("");
  const [replay, setReplay] = useState(null);
  const [replayBusy, setReplayBusy] = useState(false);
  const [replays, setReplays] = useState([]);
  const [selectedReplayId, setSelectedReplayId] = useState("");
  const [compareReplayId, setCompareReplayId] = useState("");
  const [compareReplay, setCompareReplay] = useState(null);
  const [error, setError] = useState(null);
  const selectedCapture = captures.find(c => String(c.id) === String(selectedCaptureId));
  const replayPromptKey = selectedCapture?.kind === "writeup" ? "reporting.writeup" : "reporting.analyse";
  const selectedPromptVersion = promptVersions.find(v => String(v.id) === String(selectedPromptVersionId));
  const promptKeyVersions = promptVersions.filter(v => v.key === promptKey);
  const replayPromptVersions = promptVersions.filter(v => v.key === replayPromptKey);
  const selectedReplayVersion = replayPromptVersions.find(v => String(v.id) === String(selectedReplayVersionId));
  const currentFindings = replay?.findings || [];
  const compareFindings = compareReplay?.findings || [];
  const setEditorVersion = version => {
    if (!version) return;
    setSelectedPromptVersionId(String(version.id));
    setPromptVersionName(version.name || "");
    setPromptText(version.prompt_text || "");
  };
  const loadPromptVersions = useCallback(async (key, selectedId = "") => {
    const d = await api.listReportingPromptVersions(key);
    const versions = d.versions || [];
    setPromptVersions(prev => [...prev.filter(v => v.key !== key), ...versions]);
    const current = versions.find(v => String(v.id) === String(selectedId)) || versions[0];
    if (key === promptKey) setEditorVersion(current);
    return versions;
  }, [promptKey]);
  const loadCaptures = useCallback(async () => {
    const d = await api.listReportingCaptures();
    setCaptures(d.captures || []);
    setCaptureDbPath(d.db_path || "");
    if (!selectedCaptureId && d.captures?.[0]) setSelectedCaptureId(String(d.captures[0].id));
  }, [selectedCaptureId]);
  const loadReplays = useCallback(async () => {
    const d = await api.listReportingReplays();
    setReplays(d.replays || []);
    if (!selectedReplayId && d.replays?.[0]) setSelectedReplayId(String(d.replays[0].id));
  }, [selectedReplayId]);
  useEffect(() => {
    loadPromptVersions("reporting.analyse").catch(e => setError(e.message));
    loadPromptVersions("reporting.writeup").catch(e => setError(e.message));
    loadCaptures().catch(e => setError(e.message));
    loadReplays().catch(e => setError(e.message));
  }, [
	loadPromptVersions,
	loadReplays,
	loadCaptures
]);
  useEffect(() => {
    setSelectedPromptVersionId("");
    loadPromptVersions(promptKey).catch(e => setError(e.message));
  }, [promptKey, loadPromptVersions]);
  useEffect(() => {
    if (replayPromptVersions.length === 0) {
      loadPromptVersions(replayPromptKey).catch(e => setError(e.message));
      return;
    }
    if (!selectedReplayVersionId || !replayPromptVersions.some(v => String(v.id) === String(selectedReplayVersionId))) {
      const builtin = replayPromptVersions.find(v => v.is_builtin) || replayPromptVersions[0];
      setSelectedReplayVersionId(String(builtin.id));
    }
  }, [
	replayPromptKey,
	selectedReplayVersionId,
	replayPromptVersions.length,
	loadPromptVersions,
	replayPromptVersions
]);
  useEffect(() => {
    if (!replay || !["queued", "running"].includes(replay.status)) return;
    const iv = setInterval(async () => {
      try {
        const next = await api.getReportingReplay(replay.id);
        setReplay(next);
        if (!["queued", "running"].includes(next.status)) {
          setReplayBusy(false);
          setSelectedReplayId(String(next.id));
          loadReplays().catch(() => {});
        }
      } catch (e) {
        setError(e.message);
        setReplayBusy(false);
      }
    }, 1500);
    return () => clearInterval(iv);
  }, [
	replay?.id,
	replay?.status,
	replay,
	loadReplays
]);
  useEffect(() => {
    if (!selectedReplayId) return;
    api.getReportingReplay(selectedReplayId).then(setReplay).catch(() => {});
  }, [selectedReplayId]);
  useEffect(() => {
    if (!compareReplayId) {
      setCompareReplay(null);
      return;
    }
    api.getReportingReplay(compareReplayId).then(setCompareReplay).catch(() => {});
  }, [compareReplayId]);
  useEffect(() => {
    if (!selectedCaptureId) {
      setSelectedCaptureDetail(null);
      return;
    }
    api.getReportingCapture(selectedCaptureId).then(setSelectedCaptureDetail).catch(() => {});
  }, [selectedCaptureId]);
  const savePrompt = async () => {
    if (!selectedPromptVersion || selectedPromptVersion.is_builtin) return;
    setPromptSaving(true);
    setPromptSaved(false);
    setError(null);
    try {
      const p = await api.updateReportingPromptVersion(selectedPromptVersion.id, {
        name: promptVersionName,
        prompt_text: promptText
      });
      await loadPromptVersions(promptKey, p.id);
      setPromptSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setPromptSaving(false);
    }
  };
  const createPromptVersion = async () => {
    const name = promptVersionName.trim() || `Version ${new Date().toLocaleString()}`;
    setPromptSaving(true);
    setPromptSaved(false);
    setError(null);
    try {
      const p = await api.createReportingPromptVersion({
        key: promptKey,
        name,
        prompt_text: promptText
      });
      await loadPromptVersions(promptKey, p.id);
      setPromptSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setPromptSaving(false);
    }
  };
  const deletePromptVersion = async () => {
    if (!selectedPromptVersion || selectedPromptVersion.is_builtin) return;
    if (!confirm(`Delete prompt version "${selectedPromptVersion.name}"? Saved replay findings remain available.`)) return;
    setPromptSaving(true);
    setPromptSaved(false);
    setError(null);
    try {
      await api.deleteReportingPromptVersion(selectedPromptVersion.id);
      await loadPromptVersions(promptKey);
    } catch (e) {
      setError(e.message);
    } finally {
      setPromptSaving(false);
    }
  };
  const startReplay = async () => {
    if (!selectedCaptureId || !selectedReplayVersion?.id) return;
    setReplayBusy(true);
    setError(null);
    setReplay(null);
    try {
      const r = await api.replayReportingCapture(selectedCaptureId, {
        prompt_version_id: Number(selectedReplayVersion.id)
      });
      setReplay(r);
      setSelectedReplayId(String(r.id));
      setTab("replay");
    } catch (e) {
      setError(e.message);
      setReplayBusy(false);
    }
  };
  return <>
    <div className="topbar">
      <div className="topbar-title">Reporting Lab</div>
    </div>
    <div className="content scroll-content settings-content">
      <div className="tab-bar settings-tab-bar">
        <button className={"tab-btn" + (tab === "prompt" ? " active" : "")} onClick={() => setTab("prompt")}>Prompt</button>
        <button className={"tab-btn" + (tab === "replay" ? " active" : "")} onClick={() => {
          setTab("replay");
          loadCaptures().catch(() => {});
        }}>Replay</button>
        <button className={"tab-btn" + (tab === "findings" ? " active" : "")} onClick={() => {
          setTab("findings");
          loadReplays().catch(() => {});
        }}>Debug Findings</button>
      </div>
      {error && <div className="alert error">{error}</div>}

      {tab === "prompt" && <div className="card">
          <div className="form-section-title">Reporting Prompt Versions</div>
          <div className="field-hint" style={{
          marginBottom: 12
        }}>
            Default versions load from reporting.py. New versions are saved in the Reporting Lab database and can be replayed against the same captures.
            <br />Reporting Lab uses the DEFAULT LLM setting and does not respect the overriden setting in the scan the data came from.
            <br />Set the Version name BEFORE clicking new version!
            <br />Batch reporting has {"{url}"} and {"{results}"} placeholders. 
            <br />During-scan writeups have {"{source}"}, {"{base_url}"}, {"{finding_json}"}, {"{evidence_json}"}.
          </div>
          <div className="form-row">
            <label className="form-label">Prompt</label>
            <select className="form-input" value={promptKey} onChange={e => {
            setPromptKey(e.target.value);
            setPromptSaved(false);
          }}>
              <option value="reporting.analyse">Final reporting batch</option>
              <option value="reporting.writeup">During-scan writeup replay</option>
            </select>
          </div>
          <div className="form-row">
            <label className="form-label">Version</label>
            <select className="form-input" value={selectedPromptVersionId} onChange={e => {
            const v = promptVersions.find(p => String(p.id) === String(e.target.value));
            setEditorVersion(v);
            setPromptSaved(false);
          }}>
              {promptKeyVersions.map(v => <option key={v.id} value={String(v.id)}>
                  {v.name}{v.is_builtin ? " (from reporting.py)" : ""}
                </option>)}
            </select>
          </div>
          <div className="form-row">
            <label className="form-label">Version name</label>
            <input className="form-input" value={promptVersionName} disabled={promptSaving} onInput={e => {
            setPromptSaved(false);
            setPromptVersionName(e.target.value);
          }} />
          </div>
          {selectedPromptVersion && <div className="row" style={{
          gap: 8,
          marginBottom: 8
        }}>
              <span className="source-badge">{selectedPromptVersion.is_builtin ? "from reporting.py" : "DB version"}</span>
              {selectedPromptVersion.updated_at && <span className="subtle">Updated {fmtDate(selectedPromptVersion.updated_at)}</span>}
            </div>}
          <textarea className="form-input mono" style={{
          minHeight: 520,
          whiteSpace: "pre",
          fontSize: 12
        }} value={promptText} disabled={promptSaving} onInput={e => {
          setPromptSaved(false);
          setPromptText(e.target.value);
        }} />
          <div className="row" style={{
          gap: 8,
          marginTop: 12
        }}>
            <button className="btn" onClick={savePrompt} disabled={promptSaving || !promptText.trim() || selectedPromptVersion?.is_builtin}>
              {promptSaving ? "Saving…" : "Save Prompt"}
            </button>
            <button className="btn secondary" onClick={createPromptVersion} disabled={promptSaving || !promptText.trim()}>
              New Version
            </button>
            <button className="btn danger-outline" onClick={deletePromptVersion} disabled={promptSaving || selectedPromptVersion?.is_builtin}>
              Delete Version
            </button>
            {promptSaved && <span className="save-confirm"><IconCheck /> Saved</span>}
          </div>
        </div>}

      {tab === "replay" && <div className="card">
          <div className="form-section-title">Replay Captured Reporting Batch</div>
          <div className="field-hint" style={{
          marginBottom: 12
        }}>
            Captures are read from <span className="mono">{captureDbPath || "reporting debug DB"}</span>.
          </div>
          <div className="row" style={{
          gap: 8,
          alignItems: "center",
          marginBottom: 12
        }}>
            <select className="form-input" style={{
            maxWidth: 520
          }} value={selectedCaptureId} onChange={e => {
            setSelectedCaptureId(e.target.value);
            setSelectedReplayVersionId("");
          }}>
              <option value="">Select a capture…</option>
              {captures.map(c => <option key={c.id} value={String(c.id)}>
                  #{c.id} · {c.kind === "writeup" ? "during-scan writeup" : "final reporting"} · {fmtDate(c.created_at)} · {truncUrl(c.url, 52)} · {c.finding_count} findings
                </option>)}
            </select>
            <select className="form-input" style={{
            maxWidth: 300
          }} value={selectedReplayVersionId} onChange={e => setSelectedReplayVersionId(e.target.value)}>
              <option value="">Select prompt version…</option>
              {replayPromptVersions.map(v => <option key={v.id} value={String(v.id)}>
                  {v.name}{v.is_builtin ? " (default)" : ""}
                </option>)}
            </select>
            <button className="btn secondary" onClick={() => loadCaptures().catch(e => setError(e.message))}>Refresh</button>
            <button className="btn" onClick={startReplay} disabled={replayBusy || !selectedCaptureId || !selectedReplayVersion?.id}>
              {replayBusy ? "Replaying…" : "Replay"}
            </button>
          </div>
          {selectedCapture && <>
            <div className="settings-list-row" style={{
            marginBottom: 8
          }}>
              <div>
                <strong>Capture #{selectedCapture.id}</strong>
                <div className="mono" style={{
                fontSize: 11,
                wordBreak: "break-all"
              }}>{selectedCapture.url}</div>
                <div className="subtle">
                  {selectedCapture.kind === "writeup" ? `Source ${selectedCapture.source || "unknown"}` : `Model ${selectedCapture.llm?.model || "unknown"} · ${selectedCapture.llm?.provider || "unknown"}`}
                </div>
                <div className="subtle">Prompt version {selectedReplayVersion?.name || "unknown"}</div>
              </div>
              <div><span className="finding-count-badge">{selectedCapture.finding_count}</span></div>
            </div>
            {selectedCaptureDetail?.findings?.length > 0 && <div style={{
            marginBottom: 12
          }}>
                <div className="subtle" style={{
              fontSize: 11,
              fontWeight: 600,
              marginBottom: 6,
              textTransform: "uppercase",
              letterSpacing: "0.05em"
            }}>Original findings in this capture</div>
                <DebugFindingsTable findings={selectedCaptureDetail.findings} />
              </div>}
          </>}
          {replay && <>
            <div className="activity-token-bar" style={{
            cursor: "default"
          }}>
              {["queued", "running"].includes(replay.status) && <span className="inline-spinner"></span>}
              <span className="token-bar-label">{replay.status}</span>
              <span>{replay.progress_message || ""}</span>
              {replay.prompt_version_name && <span className="source-badge">{replay.prompt_version_name}</span>}
              {replay.error && <span className="alert error" style={{
              marginLeft: 8
            }}>{replay.error}</span>}
            </div>
            {replay.status === "complete" && <div className="row" style={{
            gap: 8,
            marginTop: 12
          }}>
                <button className="btn" onClick={() => setTab("findings")}>
                  View {replay.finding_count} Debug Finding{replay.finding_count === 1 ? "" : "s"}
                </button>
              </div>}
          </>}
        </div>}

      {tab === "findings" && <div className="card">
          <div className="form-section-title">Debug Reporter Findings</div>
          <div className="row" style={{
          gap: 8,
          alignItems: "center",
          marginBottom: 12
        }}>
            <select className="form-input" style={{
            maxWidth: 460
          }} value={selectedReplayId} onChange={e => setSelectedReplayId(e.target.value)}>
              <option value="">Select a replay…</option>
              {replays.map(r => <option key={r.id} value={String(r.id)}>
                  Replay #{r.id} · {r.prompt_version_name || "unknown version"} · {r.status} · {fmtDate(r.started_at)} · {r.finding_count} findings
                </option>)}
            </select>
            <select className="form-input" style={{
            maxWidth: 460
          }} value={compareReplayId} onChange={e => setCompareReplayId(e.target.value)}>
              <option value="">Compare with…</option>
              {replays.filter(r => String(r.id) !== String(selectedReplayId)).map(r => <option key={r.id} value={String(r.id)}>
                  Replay #{r.id} · {r.prompt_version_name || "unknown version"} · {r.status} · {fmtDate(r.started_at)}
                </option>)}
            </select>
            <button className="btn secondary" onClick={() => loadReplays().catch(e => setError(e.message))}>Refresh</button>
          </div>
          {compareReplay ? <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit,minmax(360px,1fr))",
          gap: 16
        }}>
                <div>
                  <div className="form-section-title">Replay #{replay?.id || "—"} · {replay?.prompt_version_name || "unknown version"}</div>
                  {currentFindings.length === 0 ? <div className="subtle" style={{
              padding: 24,
              textAlign: "center"
            }}>No debug findings for this replay.</div> : <DebugFindingsTable findings={currentFindings} />}
                </div>
                <div>
                  <div className="form-section-title">Replay #{compareReplay.id} · {compareReplay.prompt_version_name || "unknown version"}</div>
                  {compareFindings.length === 0 ? <div className="subtle" style={{
              padding: 24,
              textAlign: "center"
            }}>No debug findings for this replay.</div> : <DebugFindingsTable findings={compareFindings} />}
                </div>
              </div> : currentFindings.length === 0 ? <div className="subtle" style={{
          padding: 24,
          textAlign: "center"
        }}>No debug findings for this replay.</div> : <DebugFindingsTable findings={currentFindings} />}
        </div>}
    </div></>;
}
