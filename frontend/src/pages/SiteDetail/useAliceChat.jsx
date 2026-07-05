import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../../lib/api";
import { getAliceSession, aliceSessionSubscribe, aliceSessionAbort, aliceSessionConnect, aliceSessionStart } from "../../lib/aliceSession";

// A.L.I.C.E. interactive chat state + lifecycle, extracted verbatim from
// TestRunDetail. Owns the server-backed chat sessions (with a localStorage
// instant-paint cache that is resilient to the SQLite run-id-reuse gotcha),
// reconnects to an in-flight stream on mount, and drives directive submission
// through the aliceSession singleton so streams survive component unmounts.
// `onActivate` fires when a directive is submitted so the caller can expand the
// A.L.I.C.E. agent panel.
export function useAliceChat(runId, { onActivate } = {}) {
  const ALICE_WELCOME_MESSAGE = "Hello! I am A.L.I.C.E, your interactive pentesting partner. To start a test, click Start Pentest at the top right, or you can tell me to work on something specific!";
  const _aliceDefaultChats = () => [{
    id: "tab-default",
    title: "Session 1",
    messages: [{
      id: "welcome",
      sender: "alice",
      type: "message",
      text: ALICE_WELCOME_MESSAGE,
      ts: new Date().toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit"
      })
    }]
  }];
  const [aliceChats, setAliceChats] = useState(() => {
    // Seed from localStorage for instant display; server load will overwrite below.
    try {
      const saved = localStorage.getItem(`alice_chats_${runId}`);
      if (saved) return JSON.parse(saved);
    } catch  {}
    return _aliceDefaultChats();
  });
  const [activeAliceTabId, setActiveAliceTabId] = useState(() => {
    try {
      const saved = localStorage.getItem(`alice_active_tab_${runId}`);
      if (saved) return saved;
    } catch  {}
    return "tab-default";
  });

  // Load sessions from the server on mount.
  // The server (DB rows scoped by test_run_id) is the source of truth for run
  // *identity*. localStorage is only an instant-paint cache; because SQLite
  // reuses run ids after the highest run is deleted, a cached chat under
  // alice_chats_<id> may actually belong to a different, deleted run. We compare
  // the server's stable run token against the one stored with the cache and
  // discard the cache when they disagree (or when the run has no chats yet),
  // which prevents one run from showing another run's chat.
  useEffect(() => {
    let cancelled = false;
    api.getAliceSessions(runId).then(data => {
      if (cancelled) return;
      const serverToken = data.run_created_at || "";
      const localToken = localStorage.getItem(`alice_chats_${runId}_runToken`) || "";
      const localIsForThisRun = !!serverToken && localToken === serverToken;

      // Helper: patch messages with the latest recovery-key text.
      const applyRecovery = (chats, tabId) => {
        try {
          const rec = JSON.parse(localStorage.getItem(`alice_recover_${runId}:${tabId}`) || "null");
          if (!rec || !rec.thinkMsgId) return chats;
          return chats.map(tab => {
            if (tab.id !== tabId) return tab;
            return {
              ...tab,
              messages: tab.messages.map(m => {
                if (m.id === rec.thinkMsgId && rec.thought) return {
                  ...m,
                  text: rec.thought
                };
                if (m.id === rec.replyMsgId && rec.message) return {
                  ...m,
                  text: rec.message
                };
                return m;
              })
            };
          });
        } catch  {
          return chats;
        }
      };
      if (!data.chats || data.chats.length === 0) {
        // The run has no persisted chat. If our cache is from a *different*
        // (reused-id) run, it would wrongly display that run's chat — reset to
        // a fresh default and overwrite the stale cache. Only keep the cache
        // when it provably belongs to this run (genuine not-yet-saved content).
        if (!localIsForThisRun) {
          const defaults = _aliceDefaultChats();
          setAliceChats(defaults);
          setActiveAliceTabId("tab-default");
          try {
            localStorage.setItem(`alice_chats_${runId}`, JSON.stringify(defaults));
            localStorage.setItem(`alice_active_tab_${runId}`, "tab-default");
            localStorage.setItem(`alice_chats_${runId}_runToken`, serverToken);
            localStorage.removeItem(`alice_chats_${runId}_savedAt`);
          } catch  {}
        }
        _aliceServerLoaded.current = true;
        return;
      }
      const serverUpdatedAt = data.updated_at ? new Date(data.updated_at).getTime() : 0;
      const localSavedAt = parseInt(localStorage.getItem(`alice_chats_${runId}_savedAt`) || "0", 10);
      const activeTabId = data.active_tab_id || "tab-default";

      // Prefer local only when it provably belongs to THIS run and is newer
      // (a page refresh mid-stream that hasn't flushed to the server yet).
      // Otherwise the server wins — this also covers the reused-id case, where
      // the local cache belongs to a deleted run and must be discarded.
      const preferLocal = localIsForThisRun && localSavedAt > serverUpdatedAt;
      if (!preferLocal) {
        const merged = applyRecovery(data.chats, activeTabId);
        _aliceServerLoaded.current = true;
        setAliceChats(merged);
        setActiveAliceTabId(activeTabId);
        try {
          localStorage.setItem(`alice_chats_${runId}`, JSON.stringify(merged));
          localStorage.setItem(`alice_active_tab_${runId}`, activeTabId);
          localStorage.setItem(`alice_chats_${runId}_runToken`, serverToken);
          localStorage.setItem(`alice_chats_${runId}_savedAt`, serverUpdatedAt.toString());
        } catch  {}
      } else {
        // Local is fresher and belongs to this run — keep it, but record the
        // run token so future loads recognise it.
        try {
          localStorage.setItem(`alice_chats_${runId}_runToken`, serverToken);
        } catch  {}
        _aliceServerLoaded.current = true;
      }
    }).catch(() => {
      _aliceServerLoaded.current = true; // unblock saves even if the API fails
    });
    return () => {
      cancelled = true;
    };
  }, [runId]);
  const [aliceInputText, setAliceInputText] = useState("");
  const [aliceChatHeight, setAliceChatHeight] = useState(300);
  const [aliceThinkingTabId, setAliceThinkingTabId] = useState(null);
  const aliceIsThinking = aliceThinkingTabId !== null;
  const [aliceGlobalRunning, setAliceGlobalRunning] = useState(false);
  const [aliceExpandedThinkIds, setAliceExpandedThinkIds] = useState(new Set());

  // On mount: check whether a background ALICE task is already running (e.g.
  // after a page refresh) and reconnect to its event stream if so.
  useEffect(() => {
    let cancelled = false;
    api.getAliceStatus(runId).then(st => {
      if (cancelled || !st.running) return;
      const {
        tab_id,
        think_msg_id,
        reply_msg_id
      } = st;
      setAliceGlobalRunning(true);
      setAliceThinkingTabId(tab_id);
      // Pre-populate session so the subscriber can find the right messages.
      const sess = getAliceSession(runId, tab_id);
      sess.thinkMsgId = think_msg_id;
      sess.replyMsgId = reply_msg_id;
      const done = () => {
        setAliceThinkingTabId(null);
        setAliceGlobalRunning(false);
      };
      aliceSessionConnect(runId, tab_id, {
        thinkMsgId: think_msg_id,
        replyMsgId: reply_msg_id,
        cursor: 0,
        onFinish: done,
        onFail: done
      });
    }).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [runId]);
  // Subscribe to in-flight stream on mount/tab-switch so navigating back
  // shows the spinner and receives live chunks from the singleton reader loop.
  useEffect(() => {
    const session = getAliceSession(runId, activeAliceTabId);
    if (session.active) {
      setAliceThinkingTabId(activeAliceTabId);
    }

    // Resolve the best available accumulated text: prefer the in-memory session
    // (same page load), fall back to the localStorage recovery key written
    // directly by aliceSessionStart (survives navigation + module resets).
    let recThinkId = session.thinkMsgId;
    let recReplyId = session.replyMsgId;
    let recThought = session.accumulatedThought;
    let recMessage = session.accumulatedMessage;
    if (!recThinkId || !recThought && !recMessage) {
      try {
        const saved = JSON.parse(localStorage.getItem(`alice_recover_${runId}:${activeAliceTabId}`) || "null");
        if (saved && saved.thinkMsgId) {
          recThinkId = recThinkId || saved.thinkMsgId;
          recReplyId = recReplyId || saved.replyMsgId;
          recThought = recThought || saved.thought;
          recMessage = recMessage || saved.message;
        }
      } catch  {}
    }
    if (recThinkId && (recThought || recMessage)) {
      setAliceChats(prev => prev.map(tab => {
        if (tab.id !== activeAliceTabId) return tab;
        return {
          ...tab,
          messages: tab.messages.map(m => {
            if (m.id === recThinkId && recThought) return {
              ...m,
              text: recThought
            };
            if (m.id === recReplyId && recMessage) return {
              ...m,
              text: recMessage
            };
            return m;
          })
        };
      }));
    }
    const unsub = aliceSessionSubscribe(runId, activeAliceTabId, {
      onChunk: event => {
        const {
          thinkMsgId,
          replyMsgId
        } = session;
        // Use session's running totals (not m.text + delta) so every render
        // sees the complete accumulated text — identical to the catch-up sync
        // on navigation-back, which ensures blocks parse and render graphically
        // rather than as an in-progress incremental string.
        setAliceChats(prev => prev.map(tab => {
          if (tab.id !== activeAliceTabId) return tab;
          return {
            ...tab,
            messages: tab.messages.map(m => {
              if (event.type === "thinking_chunk" && m.id === thinkMsgId) return {
                ...m,
                text: session.accumulatedThought,
                stepData: session.stepData
              };
              if (event.type === "message_chunk" && m.id === replyMsgId) return {
                ...m,
                text: session.accumulatedMessage
              };
              if (event.type === "warning" && m.id === replyMsgId) return {
                ...m,
                text: event.message
              };
              if (["step_llm_call", "step_tool_call", "step_tool_result"].includes(event.type) && m.id === thinkMsgId) return {
                ...m,
                stepData: {
                  ...session.stepData
                }
              };
              if (event.type === "done") {
                if (m.id === thinkMsgId) {
                  const upd = {
                    stepData: session.stepData
                  };
                  if (event.thought) upd.text = event.thought;
                  return {
                    ...m,
                    ...upd
                  };
                }
                if (m.id === replyMsgId && event.message) return {
                  ...m,
                  text: event.message
                };
              }
              return m;
            })
          };
        }));
      },
      onDone: () => {
        setAliceThinkingTabId(null);
        setAliceGlobalRunning(false);
      },
      onError: () => {
        setAliceThinkingTabId(null);
        setAliceGlobalRunning(false);
      }
    });
    return unsub;
  }, [runId, activeAliceTabId]);
  const _aliceSaveTimer = useRef(null);
  const _aliceServerLoaded = useRef(false);
  useEffect(() => {
    // Keep localStorage in sync for fast initial render on next mount.
    // savedAt lets the server-load effect decide which source is fresher.
    // Guard: skip until the initial server load has resolved so we don't
    // stamp a fresh localSavedAt timestamp before the comparison happens.
    if (!_aliceServerLoaded.current) return;
    const now = Date.now();
    try {
      localStorage.setItem(`alice_chats_${runId}`, JSON.stringify(aliceChats));
      localStorage.setItem(`alice_active_tab_${runId}`, activeAliceTabId);
      localStorage.setItem(`alice_chats_${runId}_savedAt`, now.toString());
    } catch  {}
    // Debounce server save so rapid streaming chunks don't hammer the API.
    if (_aliceSaveTimer.current) clearTimeout(_aliceSaveTimer.current);
    const capturedRunId = runId;
    const capturedChats = aliceChats;
    const capturedTabId = activeAliceTabId;
    _aliceSaveTimer.current = setTimeout(() => {
      api.saveAliceSessions(capturedRunId, {
        chats: capturedChats,
        active_tab_id: capturedTabId
      }).catch(() => {});
    }, 800);
    // Flush any pending save immediately on unmount so navigation away within the
    // debounce window doesn't silently drop the last change.
    return () => {
      if (_aliceSaveTimer.current) {
        clearTimeout(_aliceSaveTimer.current);
        _aliceSaveTimer.current = null;
        api.saveAliceSessions(capturedRunId, {
          chats: capturedChats,
          active_tab_id: capturedTabId
        }).catch(() => {});
      }
    };
  }, [aliceChats, activeAliceTabId, runId]);
  const activeAliceTab = aliceChats.find(t => t.id === activeAliceTabId) || aliceChats[0];
  const aliceMessages = activeAliceTab ? activeAliceTab.messages : [];
  const createAliceTab = () => {
    const newTabId = "tab-" + Date.now().toString();
    const newTab = {
      id: newTabId,
      title: `Session ${aliceChats.length + 1}`,
      messages: [{
        id: "welcome-" + newTabId,
        sender: "alice",
        type: "message",
        text: ALICE_WELCOME_MESSAGE,
        ts: new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit"
        })
      }]
    };
    setAliceChats(prev => [...prev, newTab]);
    setActiveAliceTabId(newTabId);
  };
  const deleteAliceTab = (tabId, e) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    if (aliceChats.length <= 1) {
      const resetTab = {
        id: "tab-default",
        title: "Session 1",
        messages: [{
          id: "welcome-reset",
          sender: "alice",
          type: "message",
          text: ALICE_WELCOME_MESSAGE,
          ts: new Date().toLocaleTimeString("en-US", {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit"
          })
        }]
      };
      setAliceChats([resetTab]);
      setActiveAliceTabId("tab-default");
      return;
    }
    const index = aliceChats.findIndex(t => t.id === tabId);
    if (index === -1) return;
    const remainingChats = aliceChats.filter(t => t.id !== tabId);
    setAliceChats(remainingChats);
    if (activeAliceTabId === tabId) {
      const nextActiveIndex = Math.max(0, index - 1);
      setActiveAliceTabId(remainingChats[nextActiveIndex].id);
    }
  };
  const startAliceResize = useCallback(e => {
    e.preventDefault();
    e.stopPropagation();
    const startY = e.clientY;
    const startH = aliceChatHeight;
    const onMove = ev => {
      const newH = Math.max(150, Math.min(800, startH + (ev.clientY - startY)));
      setAliceChatHeight(newH);
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [aliceChatHeight]);
  const handleAliceStop = () => {
    aliceSessionAbort(runId, activeAliceTabId);
    api.stopAliceRun(runId).catch(() => {});
    setAliceThinkingTabId(null);
    setAliceGlobalRunning(false);
  };

  // Core ALICE turn submission. `handleAliceSend` drives this from the chat input,
  // but other UI affordances (e.g. the De-duplicate Issues button) reuse it so a
  // click does exactly what typing the same directive into the chat would do.
  const submitAliceDirective = (rawText, {
    fromInput = false,
    onComplete = null
  } = {}) => {
    const userText = (rawText || "").trim();
    if (!userText || aliceIsThinking) return;
    if (fromInput) setAliceInputText("");
    const currentTabId = activeAliceTabId;

    // Make sure the A.L.I.C.E. panel is expanded so the user can watch it work.
    if (onActivate) onActivate();
    const userMsg = {
      id: Date.now().toString(),
      sender: "user",
      type: "message",
      text: userText,
      ts: new Date().toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit"
      })
    };
    const thinkMsgId = (Date.now() + 1).toString();
    const replyMsgId = (Date.now() + 2).toString();
    const thinkMsg = {
      id: thinkMsgId,
      sender: "alice",
      type: "thinking",
      text: "",
      ts: new Date().toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit"
      })
    };
    const replyMsg = {
      id: replyMsgId,
      sender: "alice",
      type: "message",
      text: "",
      ts: new Date().toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit"
      })
    };
    setAliceChats(prev => prev.map(tab => {
      if (tab.id === activeAliceTabId) {
        const isFirstPrompt = tab.messages.length <= 1;
        let newTitle = tab.title;
        if (isFirstPrompt) {
          const truncated = userText.trim().slice(0, 16);
          newTitle = truncated + (userText.trim().length > 16 ? "..." : "");
        }
        return {
          ...tab,
          title: newTitle,
          messages: [...tab.messages, userMsg, thinkMsg, replyMsg]
        };
      }
      return tab;
    }));
    setAliceThinkingTabId(currentTabId);
    setAliceGlobalRunning(true);
    const historyPayload = aliceMessages.map(m => ({
      sender: m.sender,
      text: m.text
    }));

    // Delegate all I/O to the module-level singleton so the stream survives
    // component unmounts caused by hash navigation.
    // State updates are handled by the useEffect subscriber above.
    aliceSessionStart(runId, currentTabId, {
      userText,
      historyPayload,
      thinkMsgId,
      replyMsgId,
      onFinish: () => {
        setAliceThinkingTabId(null);
        setAliceGlobalRunning(false);
        if (onComplete) onComplete(null);
      },
      onFail: err => {
        if (err.name === "AbortError") {
          setAliceChats(prev => prev.map(tab => {
            if (tab.id !== currentTabId) return tab;
            return {
              ...tab,
              messages: tab.messages.map(m => {
                if (m.id === thinkMsgId && !m.text) return {
                  ...m,
                  text: "[Generation Aborted]"
                };
                if (m.id === replyMsgId && !m.text) return {
                  ...m,
                  text: "Generation stopped by user."
                };
                return m;
              })
            };
          }));
        } else {
          setAliceChats(prev => prev.map(tab => {
            if (tab.id !== currentTabId) return tab;
            return {
              ...tab,
              messages: tab.messages.map(m => m.id === replyMsgId ? {
                ...m,
                text: `I encountered an error connecting to the agent: ${err.message}`
              } : m)
            };
          }));
        }
        setAliceThinkingTabId(null);
        setAliceGlobalRunning(false);
        if (onComplete) onComplete(err);
      }
    });
  };
  const handleAliceSend = () => submitAliceDirective(aliceInputText, {
    fromInput: true
  });

  return {
    aliceChats,
    setAliceChats,
    activeAliceTabId,
    setActiveAliceTabId,
    aliceInputText,
    setAliceInputText,
    aliceChatHeight,
    aliceThinkingTabId,
    aliceIsThinking,
    aliceGlobalRunning,
    aliceExpandedThinkIds,
    setAliceExpandedThinkIds,
    aliceMessages,
    createAliceTab,
    deleteAliceTab,
    startAliceResize,
    handleAliceStop,
    handleAliceSend,
    submitAliceDirective
  };
}
