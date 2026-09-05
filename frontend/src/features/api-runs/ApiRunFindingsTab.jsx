import { FindingDetails } from "../../shared/findings/FindingDetails.tsx";
import { FindingEditor } from "../../shared/findings/FindingEditor.tsx";
import { FindingFileControls } from "../../shared/findings/FindingFileControls.tsx";
import { useFindingEditor } from "../../shared/findings/useFindingEditor.ts";
import * as apiRunsApi from "../../shared/api/apiRuns.js";
import { ALICE_DEDUP_DIRECTIVE } from "../../shared/findings/reviewDirective.js";
import { useState, useCallback } from "react";

import {
  markdownExportFilename,
  findingsToMarkdown,
  parseFindingsMarkdown,
} from "../../shared/findings/files.js";
import { downloadTextFile } from "../../shared/lib/download.js";
import { usePolling } from "../../shared/hooks/usePolling.js";
import { FindingReferenceLink } from "../../shared/ui/FindingReferenceLink.jsx";

export function ApiRunFindingsTab({ runId, scanRunning, run, initialFindingRef }) {
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(new Set());
  const [clearBusy, setClearBusy] = useState(false);
  const [dedupeBusy, setDedupeBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      const data = await apiRunsApi.getApiFindings(runId);
      setFindings(data);
      if (initialFindingRef) {
        const match = data.find((f) => f.reference === initialFindingRef);
        if (match) setExpanded((previous) => new Set(previous).add(match.id));
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [runId, initialFindingRef]);
  usePolling(load, { enabled: scanRunning, intervalMs: 8000 });
  const toggle = (id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const onExportFindingsMarkdown = () => {
    try {
      const md = findingsToMarkdown(findings, {
        runName: run?.name,
        generatedAt: new Date(),
      });
      downloadTextFile(markdownExportFilename(run, null), md, "text/markdown;charset=utf-8");
    } catch (e) {
      setError(e.message);
    }
  };
  const onImportFindingsFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const imported = parseFindingsMarkdown(await file.text());
      if (!imported.length) throw new Error("No issues found in the selected file.");
      const result = await apiRunsApi.importApiFindings(runId, imported);
      setFindings(await apiRunsApi.getApiFindings(runId));
      alert(`Imported ${result.imported} issue${result.imported === 1 ? "" : "s"}.`);
    } catch (e) {
      setError(e.message);
    }
  };

  // Seed the dedup directive into ALICE and run it — the API analogue of the web
  // scan's "AI Review Issues" button. Because the ALICE chat lives in a separate
  // tab here, we persist the prompt into the active session (so it shows up when
  // the user opens the Agents tab), start the run, poll to completion, then reload.
  const onDeduplicateFindings = async () => {
    if (dedupeBusy) return;
    try {
      const st = await apiRunsApi.getApiAliceStatus(runId);
      if (st?.running) {
        setError("A.L.I.C.E. is already running — wait for it to finish.");
        return;
      }
    } catch {}
    setDedupeBusy(true);
    setError(null);
    try {
      const data = await apiRunsApi.getApiAliceSessions(runId);
      const chats =
        data.chats && data.chats.length
          ? data.chats
          : [
              {
                id: "tab-default",
                title: "Session 1",
                messages: [],
              },
            ];
      const tabId = data.active_tab_id || chats[0].id;
      const target = chats.find((c) => c.id === tabId) || chats[0];
      const history = target.messages.map((m) => ({
        sender: m.sender,
        text: m.text,
      }));
      const now = Date.now();
      const thinkId = `think-${now}`,
        replyId = `reply-${now + 1}`;
      const ts = new Date().toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
      });
      target.messages.push(
        {
          id: `u-${now}`,
          sender: "user",
          type: "message",
          text: ALICE_DEDUP_DIRECTIVE,
          ts,
        },
        {
          id: thinkId,
          sender: "alice",
          type: "thinking",
          text: "",
          ts,
        },
        {
          id: replyId,
          sender: "alice",
          type: "message",
          text: "",
          ts,
        },
      );
      await apiRunsApi.saveApiAliceSessions(runId, {
        chats,
        active_tab_id: tabId,
      });
      await apiRunsApi.startApiAliceRun(runId, {
        message: ALICE_DEDUP_DIRECTIVE,
        history,
        tab_id: tabId,
        think_msg_id: thinkId,
        reply_msg_id: replyId,
      });
      await new Promise((resolve) => {
        const t = setInterval(async () => {
          try {
            const s = await apiRunsApi.getApiAliceStatus(runId);
            if (!s?.running) {
              clearInterval(t);
              resolve();
            }
          } catch {
            clearInterval(t);
            resolve();
          }
        }, 3000);
      });
      await load();
      setExpanded(new Set());
    } catch (e) {
      setError(e.message);
    } finally {
      setDedupeBusy(false);
    }
  };
  const onClearFindings = async () => {
    if (!confirm("Clear all findings for this API test run?")) return;
    setClearBusy(true);
    setError(null);
    try {
      await apiRunsApi.clearApiFindings(runId);
      setFindings([]);
    } catch (e) {
      setError(e.message);
    } finally {
      setClearBusy(false);
    }
  };
  const onDeleteApiFinding = async (e, findingId) => {
    e.stopPropagation();
    try {
      await apiRunsApi.deleteApiFinding(runId, findingId);
      setFindings((prev) => prev.filter((f) => f.id !== findingId));
      setExpanded((prev) => {
        const next = new Set(prev);
        next.delete(findingId);
        return next;
      });
    } catch (err) {
      setError(err.message);
    }
  };
  const editor = useFindingEditor({
    runId,
    runKind: "api",
    onError: setError,
    onSaved: (id, updated) =>
      setFindings((previous) =>
        previous.map((finding) => (finding.id === id ? { ...finding, ...updated } : finding)),
      ),
  });
  const editingFinding = editor.editingId;
  const onEditApiFinding = (event, finding) => {
    event.stopPropagation();
    setExpanded((previous) => new Set(previous).add(finding.id));
    editor.edit(finding);
  };
  const sevCls = (s) =>
    ({
      critical: "sev-critical",
      high: "sev-high",
      medium: "sev-medium",
      low: "sev-low",
      info: "sev-info",
    })[s] || "sev-info";
  if (loading)
    return (
      <div
        className="subtle"
        style={{
          padding: 32,
        }}
      >
        Loading findings…
      </div>
    );
  return (
    <div
      style={{
        padding: "16px 24px",
      }}
    >
      {error && (
        <div
          className="alert error"
          style={{
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      )}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 16,
          flexWrap: "wrap",
        }}
      >
        <h3
          style={{
            margin: 0,
            marginRight: 4,
          }}
        >
          Security Findings
        </h3>
        {scanRunning && (
          <span
            className="badge warning"
            style={{
              fontSize: 12,
            }}
          >
            Scan running…
          </span>
        )}
        <span
          className="badge neutral"
          style={{
            fontSize: 12,
          }}
        >
          {findings.length} finding{findings.length !== 1 ? "s" : ""}
        </span>
        <div
          style={{
            flex: 1,
          }}
        ></div>
        <button className="btn sm" onClick={load}>
          Refresh
        </button>
        <FindingFileControls
          hasFindings={findings.length > 0}
          onExport={onExportFindingsMarkdown}
          onImport={onImportFindingsFile}
        />
        {findings.length > 0 && (
          <button
            className="btn sm"
            disabled={dedupeBusy || scanRunning}
            onClick={onDeduplicateFindings}
          >
            {dedupeBusy && <span className="inline-spinner"></span>}
            {dedupeBusy ? "Reviewing…" : "AI Review Issues"}
          </button>
        )}
        {findings.length > 0 && (
          <button className="btn danger-outline sm" disabled={clearBusy} onClick={onClearFindings}>
            {clearBusy ? "Clearing…" : "Clear all"}
          </button>
        )}
      </div>
      {findings.length === 0 ? (
        <div
          className="subtle"
          style={{
            padding: 24,
            textAlign: "center",
          }}
        >
          {scanRunning
            ? "Scan in progress — findings will appear here as they are discovered."
            : "No findings yet. Start a scan to test this API collection."}
        </div>
      ) : (
        findings.map((f) => (
          <div
            key={f.id}
            className="finding-card"
            style={{
              marginBottom: 8,
              border: "1px solid var(--border)",
              borderRadius: 8,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "10px 14px",
                cursor: "pointer",
                background: "var(--surface)",
              }}
              onClick={() => {
                if (editingFinding === f.id) return;
                toggle(f.id);
              }}
            >
              <FindingReferenceLink
                reference={f.reference}
                title={f.title}
                description={f.description}
                severity={f.severity}
                cvss_score={f.cvss_score}
                validation_status={f.validation_status}
                validation_note={f.validation_note}
                origin={f.origin}
                validated_by={f.validated_by}
                href={`#/api-runs/${runId}/findings?finding=${encodeURIComponent(f.reference || "")}`}
              />
              <span className={"sev-badge " + sevCls(f.severity)}>{f.severity}</span>
              <span
                style={{
                  fontWeight: 600,
                  flex: 1,
                }}
              >
                {f.title}
              </span>
              {f.validation_status === "confirmed" && (
                <span className="val-badge val-confirmed">confirmed</span>
              )}
              {f.validation_status === "unconfirmed" && (
                <span className="val-badge val-unconfirmed">unconfirmed</span>
              )}
              {(f.validation_status === "false_positive" ||
                f.validation_status === "low_confidence") && (
                <span className="val-badge val-fp">low conf</span>
              )}
              {f.owasp_api_category && (
                <span
                  className="badge neutral"
                  style={{
                    fontSize: 11,
                  }}
                >
                  {f.owasp_api_category}
                </span>
              )}
              {!f.owasp_api_category && f.owasp_category && (
                <span
                  className="badge neutral"
                  style={{
                    fontSize: 11,
                  }}
                >
                  {f.owasp_category}
                </span>
              )}
              <span
                style={{
                  color: "var(--muted)",
                  fontSize: 12,
                }}
              >
                {expanded.has(f.id) ? "▲" : "▼"}
              </span>
              <button
                className="btn ghost sm finding-del-btn"
                title="Edit finding"
                onClick={(e) => onEditApiFinding(e, f)}
              >
                ✎
              </button>
              <button
                className="btn ghost sm finding-del-btn"
                title="Delete finding"
                onClick={(e) => onDeleteApiFinding(e, f.id)}
              >
                🗑
              </button>
            </div>
            {expanded.has(f.id) && editingFinding === f.id && editor.draft && (
              <FindingEditor editor={editor} runKind="api" />
            )}
            {expanded.has(f.id) && editingFinding !== f.id && (
              <div
                style={{
                  padding: "12px 14px",
                  borderTop: "1px solid var(--border)",
                  background: "var(--bg)",
                }}
              >
                <FindingDetails finding={f} runKind="api" />
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--muted)",
                  }}
                >
                  {f.validation_status} · {f.origin?.label || f.finding_source}
                </div>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

// ── ApiRunEndpointsTab — per-endpoint prerequisites display ───────────────────
