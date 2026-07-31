import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import { useAliceChat } from "./useAliceChat";
import { AliceChatPanel } from "./AliceChatPanel";

export function AliceChatPopout({ runId }) {
  const alice = useAliceChat(runId);
  const [appName, setAppName] = useState("Application");
  const [runName, setRunName] = useState(`Run #${runId}`);
  const aliceChatsRef = useRef(alice.aliceChats);
  const activeAliceTabIdRef = useRef(alice.activeAliceTabId);
  aliceChatsRef.current = alice.aliceChats;
  activeAliceTabIdRef.current = alice.activeAliceTabId;

  const notifyOpener = useCallback(() => {
    const state = {
      type: "aespa-alice-popout-close",
      runId,
      chats: aliceChatsRef.current,
      active_tab_id: activeAliceTabIdRef.current
    };
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage(state, window.location.origin);
    }
    try {
      localStorage.setItem(`aespa-alice-popout-close:${runId}`, JSON.stringify({
        ...state,
        closed_at: Date.now()
      }));
    } catch {}
  }, [runId]);

  const handleBackToRun = event => {
    event.preventDefault();
    notifyOpener();
    if (window.opener || window.name === `aespa-alice-${runId}`) {
      window.close();
    } else {
      window.location.hash = `#/runs/${runId}/activity`;
    }
  };

  useEffect(() => {
    // Re-open the inline chat when the pop-out is closed with the window close
    // control as well as when the user clicks Back to run.
    window.addEventListener("beforeunload", notifyOpener);
    return () => window.removeEventListener("beforeunload", notifyOpener);
  }, [notifyOpener]);

  useEffect(() => {
    let cancelled = false;
    api.getRun(runId).then(run => {
      if (cancelled) return;
      setRunName(run.name || `Run #${runId}`);
      if (run.site_id) {
        api.getSite(run.site_id).then(site => {
          if (!cancelled) setAppName(site.name || `Site #${run.site_id}`);
        }).catch(() => {});
      }
    }).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [runId]);

  useEffect(() => {
    document.title = `${appName} · ${runName}`;
  }, [appName, runName]);

  return <main className="alice-popout-page">
    <header className="alice-popout-header">
      <div>
        <div className="alice-popout-title">{appName}</div>
        <div className="alice-popout-subtitle">Run: {runName}</div>
      </div>
      <a className="btn ghost sm" href={`#/runs/${runId}/activity`} onClick={handleBackToRun}>Back to run</a>
    </header>
    <AliceChatPanel
      runId={runId}
      aliceChats={alice.aliceChats}
      activeAliceTabId={alice.activeAliceTabId}
      setActiveAliceTabId={alice.setActiveAliceTabId}
      deleteAliceTab={alice.deleteAliceTab}
      createAliceTab={alice.createAliceTab}
      aliceChatHeight={alice.aliceChatHeight}
      aliceMessages={alice.aliceMessages}
      aliceExpandedThinkIds={alice.aliceExpandedThinkIds}
      setAliceExpandedThinkIds={alice.setAliceExpandedThinkIds}
      startAliceResize={alice.startAliceResize}
      aliceInputText={alice.aliceInputText}
      setAliceInputText={alice.setAliceInputText}
      isActiveThinking={alice.aliceThinkingTabId === alice.activeAliceTabId}
      aliceIsThinking={alice.aliceIsThinking}
      handleAliceSend={alice.handleAliceSend}
      handleAliceStop={alice.handleAliceStop}
      popout
    />
  </main>;
}
