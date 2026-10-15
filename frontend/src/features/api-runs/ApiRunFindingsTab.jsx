import { FindingFileControls } from "../../shared/findings/FindingFileControls.tsx";
import { FindingsList } from "../../shared/findings/FindingsList.tsx";
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
import { Notice, PageError } from "../../shared/ui/Notice.jsx";

export function ApiRunFindingsTab({ runId, scanRunning, run, initialFindingRef }) {
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [collapseToken, setCollapseToken] = useState(0);
  const [clearBusy, setClearBusy] = useState(false);
  const [dedupeBusy, setDedupeBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      const data = await apiRunsApi.getApiFindings(runId);
      setFindings(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [runId]);
  usePolling(load, { enabled: scanRunning, intervalMs: 8000 });
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
      setMessage(`Imported ${result.imported} issue${result.imported === 1 ? "" : "s"}.`);
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
      setCollapseToken((token) => token + 1);
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
  const onDeleteApiFinding = async (findingId) => {
    try {
      await apiRunsApi.deleteApiFinding(runId, findingId);
      setFindings((prev) => prev.filter((f) => f.id !== findingId));
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
    <>
      <PageError error={error} onDismiss={() => setError(null)} />
      {message && (
        <Notice variant="success" onDismiss={() => setMessage(null)}>
          {message}
        </Notice>
      )}
      <div className="findings-panel flush">
        <div className="findings-status-bar">
          <div className="findings-status-summary">
            {scanRunning && <span className="badge warning">Scan running…</span>}
            <span className="badge neutral">
              {findings.length} finding{findings.length !== 1 ? "s" : ""}
            </span>
            {dedupeBusy && (
              <span className="val-status-badge val-running dedupe-status">
                <span className="inline-spinner"></span>
                A.L.I.C.E. is reviewing findings…
              </span>
            )}
          </div>
          <div className="findings-actions">
            <button className="btn secondary sm" onClick={load}>
              Refresh
            </button>
            <FindingFileControls
              hasFindings={findings.length > 0}
              onExport={onExportFindingsMarkdown}
              onImport={onImportFindingsFile}
            />
            {findings.length > 0 && (
              <button
                className="btn secondary sm"
                disabled={dedupeBusy || scanRunning}
                onClick={onDeduplicateFindings}
              >
                {dedupeBusy && <span className="inline-spinner"></span>}
                {dedupeBusy ? "Reviewing…" : "Review with AI"}
              </button>
            )}
            {findings.length > 0 && (
              <button
                className="btn danger-outline sm"
                disabled={clearBusy}
                onClick={onClearFindings}
              >
                {clearBusy ? "Clearing…" : "Clear all"}
              </button>
            )}
          </div>
        </div>
        <FindingsList
          findings={findings}
          runKind="api"
          findingHref={(reference) =>
            `#/api-runs/${runId}/findings?finding=${encodeURIComponent(reference)}`
          }
          editor={editor}
          emptyMessage={
            scanRunning
              ? "Scan in progress — findings will appear here as they are discovered."
              : "No findings yet. Start a scan to test this API collection."
          }
          initialFindingRef={initialFindingRef}
          collapseToken={collapseToken}
          onDeleteFinding={onDeleteApiFinding}
        />
      </div>
    </>
  );
}

// ── ApiRunEndpointsTab — per-endpoint prerequisites display ───────────────────
