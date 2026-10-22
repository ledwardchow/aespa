import { useCallback, useEffect, useState } from "react";
import * as sastRunsApi from "../../shared/api/sastRuns.js";
import { ApiAlicePanel } from "../api-runs/ApiAlicePanel.jsx";

export function SastAlicePopout({ runId }) {
  const [runName, setRunName] = useState(`Run #${runId}`);

  const notifyOpener = useCallback(() => {
    const state = { type: "aespa-sast-alice-popout-close", runId, closed_at: Date.now() };
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage(state, window.location.origin);
    }
    try {
      localStorage.setItem(`aespa-sast-alice-popout-close:${runId}`, JSON.stringify(state));
    } catch {}
  }, [runId]);

  useEffect(() => {
    window.addEventListener("beforeunload", notifyOpener);
    return () => window.removeEventListener("beforeunload", notifyOpener);
  }, [notifyOpener]);

  useEffect(() => {
    let cancelled = false;
    sastRunsApi
      .getSastRun(runId)
      .then((run) => {
        if (!cancelled) setRunName(run.name || `Run #${runId}`);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [runId]);

  useEffect(() => {
    document.title = `A.L.I.C.E. · ${runName}`;
  }, [runName]);

  const handleBackToRun = (event) => {
    event.preventDefault();
    notifyOpener();
    if (window.opener || window.name === `aespa-sast-alice-${runId}`) {
      window.close();
    } else {
      window.location.hash = `#/sast-runs/${runId}/coverage`;
    }
  };

  return (
    <main className="alice-popout-page sast-alice-popout">
      <header className="alice-popout-header">
        <div>
          <div className="alice-popout-title">A.L.I.C.E.</div>
          <div className="alice-popout-subtitle">SAST run: {runName}</div>
        </div>
        <a
          className="btn ghost sm"
          href={`#/sast-runs/${runId}/coverage`}
          onClick={handleBackToRun}
        >
          Back to run
        </a>
      </header>
      <ApiAlicePanel
        runKind="sast"
        runId={runId}
        agent={{ status: "idle", task: "Ask about this source snapshot" }}
        popout
      />
    </main>
  );
}
