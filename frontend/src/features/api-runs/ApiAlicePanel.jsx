import * as apiRunsApi from "../../shared/api/apiRuns.js";

import { useState, useEffect, useRef, useCallback } from "react";

import { renderAliceBlocks, renderAliceTraceBox } from "../../shared/alice/render.jsx";
import { parseAliceTurnSegments } from "../../shared/alice/segments.js";
import { renderMarkdown } from "../../shared/alice/markdown.jsx";
import { normalizeAliceText } from "../../shared/alice/text.js";
import { IconSend } from "../../shared/ui/Icons.jsx";
import { useAutoFollowScroll } from "../../shared/hooks/useAutoFollowScroll.js";
import { AliceGoalBar } from "../../shared/ui/AliceGoalBar.jsx";

export function ApiAlicePanel({ runId, agent, onRunningChange }) {
  const [isExpanded, setExpanded] = useState(true);
  // ── ALICE chat state ──────────────────────────────────────────────────────
  const [aliceChats, setAliceChats] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(`api_alice_chats_${runId}`) || "null");
      return saved && saved.length
        ? saved
        : [
            {
              id: "tab-default",
              title: "Session 1",
              messages: [],
            },
          ];
    } catch {
      return [
        {
          id: "tab-default",
          title: "Session 1",
          messages: [],
        },
      ];
    }
  });
  const [activeAliceTabId, setActiveAliceTabId] = useState(() => {
    try {
      return localStorage.getItem(`api_alice_active_tab_${runId}`) || "tab-default";
    } catch {
      return "tab-default";
    }
  });
  const [aliceRunning, setAliceRunning] = useState(false);
  const [aliceInputText, setAliceInputText] = useState("");
  const [aliceExpandedThinkIds, setAliceExpandedThinkIds] = useState(new Set());
  const [aliceChatHeight, setAliceChatHeight] = useState(300);
  const streamRef = useRef(null);
  const activeAliceTabIdRef = useRef(activeAliceTabId);
  activeAliceTabIdRef.current = activeAliceTabId;
  const sessionsRef = useRef(aliceChats);
  sessionsRef.current = aliceChats;

  // ── Persist alice chats ───────────────────────────────────────────────────
  useEffect(() => {
    try {
      localStorage.setItem(`api_alice_chats_${runId}`, JSON.stringify(aliceChats));
      localStorage.setItem(`api_alice_active_tab_${runId}`, activeAliceTabId);
    } catch {}
    apiRunsApi
      .saveApiAliceSessions(runId, {
        chats: aliceChats,
        active_tab_id: activeAliceTabId,
      })
      .catch(() => {});
  }, [aliceChats, activeAliceTabId, runId]);

  // ── Cleanup stream on unmount ─────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.close();
        streamRef.current = null;
      }
    };
  }, []);

  // ── ALICE stream connection ───────────────────────────────────────────────
  const connectAliceStream = useCallback(
    (cursor = 0) => {
      if (streamRef.current) {
        streamRef.current.close();
        streamRef.current = null;
      }
      const es = new EventSource(`/api/api-test-runs/${runId}/alice/stream?cursor=${cursor}`);
      streamRef.current = es;
      // Re-accumulate from scratch on every (re)connect: the stream replays from
      // cursor 0, so we rebuild each message's text/stepData and REPLACE state
      // rather than append — otherwise a mid-run reconnect would double-count
      // text deltas and tool entries. Mirrors the web scan's aliceSessionConnect.
      const textAcc = {}; // msg_id -> accumulated text
      const stepAcc = {}; // msg_id -> stepData ({ [step]: { llmMessages, tools } })
      es.onmessage = (ev) => {
        try {
          const event = JSON.parse(ev.data);
          if (event.goal?.tab_id) {
            setAliceChats((prev) =>
              prev.map((tab) =>
                tab.id === event.goal.tab_id ? { ...tab, goal: event.goal } : tab,
              ),
            );
          }
          if (event.type === "state_snapshot" && event.tab_id) {
            textAcc[event.think_msg_id] = normalizeAliceText(event.thought || "");
            textAcc[event.reply_msg_id] = normalizeAliceText(event.message || "");
            setAliceChats((prev) =>
              prev.map((s) =>
                s.id !== event.tab_id
                  ? s
                  : {
                      ...s,
                      messages: s.messages.map((m) => {
                        if (m.id === event.think_msg_id)
                          return { ...m, text: textAcc[event.think_msg_id] };
                        if (m.id === event.reply_msg_id)
                          return { ...m, text: textAcc[event.reply_msg_id] };
                        return m;
                      }),
                    },
              ),
            );
          } else if (
            (event.type === "thinking_chunk" || event.type === "message_chunk") &&
            event.delta &&
            event.tab_id &&
            event.msg_id
          ) {
            textAcc[event.msg_id] = normalizeAliceText((textAcc[event.msg_id] || "") + event.delta);
            const text = textAcc[event.msg_id];
            setAliceChats((prev) =>
              prev.map((s) =>
                s.id !== event.tab_id
                  ? s
                  : {
                      ...s,
                      messages: s.messages.map((m) =>
                        m.id === event.msg_id
                          ? {
                              ...m,
                              text,
                            }
                          : m,
                      ),
                    },
              ),
            );
          } else if (event.type === "message_retract" && event.tab_id && event.msg_id) {
            textAcc[event.msg_id] = normalizeAliceText(event.message || "");
            const text = textAcc[event.msg_id];
            setAliceChats((prev) =>
              prev.map((s) =>
                s.id !== event.tab_id
                  ? s
                  : {
                      ...s,
                      messages: s.messages.map((m) => (m.id === event.msg_id ? { ...m, text } : m)),
                    },
              ),
            );
          } else if (event.type === "step_llm_call" && event.tab_id && event.msg_id) {
            const stepData = stepAcc[event.msg_id] || (stepAcc[event.msg_id] = {});
            const entry =
              stepData[event.step] ||
              (stepData[event.step] = {
                llmMessages: [],
                tools: [],
              });
            entry.llmMessages = event.messages || [];
            setAliceChats((prev) =>
              prev.map((s) =>
                s.id !== event.tab_id
                  ? s
                  : {
                      ...s,
                      messages: s.messages.map((m) =>
                        m.id === event.msg_id
                          ? {
                              ...m,
                              stepData,
                            }
                          : m,
                      ),
                    },
              ),
            );
          } else if (event.type === "step_tool_call" && event.tab_id && event.msg_id) {
            const stepData = stepAcc[event.msg_id] || (stepAcc[event.msg_id] = {});
            const entry =
              stepData[event.step] ||
              (stepData[event.step] = {
                llmMessages: [],
                tools: [],
              });
            entry.tools.push({
              tool: event.tool,
              input: event.input,
              result: null,
            });
            setAliceChats((prev) =>
              prev.map((s) =>
                s.id !== event.tab_id
                  ? s
                  : {
                      ...s,
                      messages: s.messages.map((m) =>
                        m.id === event.msg_id
                          ? {
                              ...m,
                              stepData,
                            }
                          : m,
                      ),
                    },
              ),
            );
          } else if (event.type === "step_tool_result" && event.tab_id && event.msg_id) {
            const stepData = stepAcc[event.msg_id] || (stepAcc[event.msg_id] = {});
            const entry =
              stepData[event.step] ||
              (stepData[event.step] = {
                llmMessages: [],
                tools: [],
              });
            const tools = entry.tools;
            if (tools.length > 0 && tools[tools.length - 1].result === null) {
              tools[tools.length - 1].result = event.result;
            }
            setAliceChats((prev) =>
              prev.map((s) =>
                s.id !== event.tab_id
                  ? s
                  : {
                      ...s,
                      messages: s.messages.map((m) =>
                        m.id === event.msg_id
                          ? {
                              ...m,
                              stepData,
                            }
                          : m,
                      ),
                    },
              ),
            );
          } else if (event.type === "done") {
            setAliceChats((prev) =>
              prev.map((s) =>
                s.id !== event.tab_id
                  ? s
                  : {
                      ...s,
                      messages: s.messages.map((m) => {
                        if (m.id === event.think_msg_id)
                          return {
                            ...m,
                            text: normalizeAliceText(event.thought || m.text),
                            stepData: stepAcc[event.think_msg_id] || m.stepData || {},
                          };
                        if (m.id === event.reply_msg_id && event.message)
                          return {
                            ...m,
                            text: normalizeAliceText(event.message),
                          };
                        return m;
                      }),
                    },
              ),
            );
            setAliceRunning(false);
            es.close();
            streamRef.current = null;
          }
        } catch {}
      };
      es.onerror = () => {
        es.close();
        streamRef.current = null;
        setAliceRunning(false);
      };
    },
    [runId],
  );

  // ── On mount: load sessions, agent log, check alice status ────────────────
  useEffect(() => {
    apiRunsApi
      .getApiAliceSessions(runId)
      .then((data) => {
        const chats = data.chats || [];
        if (chats.length) {
          setAliceChats(chats);
          const aid = data.active_tab_id || "tab-default";
          setActiveAliceTabId(aid);
          activeAliceTabIdRef.current = aid;
        }
      })
      .catch(() => {});

    apiRunsApi
      .getApiAliceStatus(runId)
      .then((st) => {
        if (st?.goal?.tab_id) {
          setAliceChats((prev) =>
            prev.map((tab) => (tab.id === st.goal.tab_id ? { ...tab, goal: st.goal } : tab)),
          );
        }
        if (st?.running) {
          setAliceRunning(true);
          connectAliceStream(0);
        }
      })
      .catch(() => {});
  }, [runId, connectAliceStream]);

  // ── ALICE send / stop ─────────────────────────────────────────────────────
  const submitAliceDirective = async (rawText) => {
    const userText = (typeof rawText === "string" ? rawText : aliceInputText).trim();
    if (!userText) return;
    if (aliceRunning) {
      const tabId = activeAliceTabIdRef.current;
      const activeGoal = sessionsRef.current.find((tab) => tab.id === tabId)?.goal;
      if (activeGoal?.status !== "active") return;
      const ts = new Date().toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
      });
      setAliceChats((prev) =>
        prev.map((tab) =>
          tab.id === tabId
            ? {
                ...tab,
                messages: [
                  ...tab.messages,
                  {
                    id: `steer-${Date.now()}`,
                    sender: "user",
                    type: "message",
                    text: userText,
                    ts,
                  },
                ],
              }
            : tab,
        ),
      );
      setAliceInputText("");
      apiRunsApi.steerApiAliceGoal(runId, { message: userText }).catch(() => {});
      return;
    }
    setAliceInputText("");
    const tabId = activeAliceTabIdRef.current;
    if (/^\/goal\s+resume$/i.test(userText)) {
      setAliceChats((prev) =>
        prev.map((tab) =>
          tab.id === tabId && tab.goal
            ? { ...tab, goal: { ...tab.goal, status: "active", pause_reason: "" } }
            : tab,
        ),
      );
    } else if (/^\/goal\s+clear$/i.test(userText)) {
      setAliceChats((prev) => prev.map((tab) => (tab.id === tabId ? { ...tab, goal: null } : tab)));
    }
    const thinkId = `think-${Date.now()}`;
    const replyId = `reply-${Date.now() + 1}`;
    const ts = new Date().toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
    });
    const userMsg = {
      id: `u-${Date.now()}`,
      sender: "user",
      type: "message",
      text: userText,
      ts,
    };
    const thinkMsg = {
      id: thinkId,
      sender: "alice",
      type: "thinking",
      text: "",
      ts,
    };
    const replyMsg = {
      id: replyId,
      sender: "alice",
      type: "message",
      text: "",
      ts,
    };
    setAliceChats((prev) =>
      prev.map((s) =>
        s.id !== tabId
          ? s
          : {
              ...s,
              messages: [...s.messages, userMsg, thinkMsg, replyMsg],
            },
      ),
    );
    setAliceRunning(true);
    const activeSession = sessionsRef.current.find((s) => s.id === tabId) || {
      messages: [],
    };
    const history = activeSession.messages.map((m) => ({
      sender: m.sender,
      text: m.text,
    }));
    try {
      await apiRunsApi.startApiAliceRun(runId, {
        message: userText,
        history,
        tab_id: tabId,
        think_msg_id: thinkId,
        reply_msg_id: replyId,
      });
      connectAliceStream(0);
    } catch {
      setAliceRunning(false);
    }
  };
  const handleAliceSend = () => submitAliceDirective(aliceInputText);
  const handleAliceStop = () => {
    apiRunsApi.stopApiAliceRun(runId).catch(() => {});
    if (streamRef.current) {
      streamRef.current.close();
      streamRef.current = null;
    }
    setAliceRunning(false);
    const tabId = activeAliceTabIdRef.current;
    setAliceChats((prev) =>
      prev.map((tab) =>
        tab.id === tabId && tab.goal
          ? {
              ...tab,
              goal: { ...tab.goal, status: "paused", pause_reason: "Paused by user." },
            }
          : tab,
      ),
    );
  };

  // ── ALICE tab management ──────────────────────────────────────────────────
  const createAliceTab = () => {
    const id = "tab-" + Date.now();
    setAliceChats((prev) => [
      ...prev,
      {
        id,
        title: `Session ${prev.length + 1}`,
        messages: [],
      },
    ]);
    setActiveAliceTabId(id);
  };
  const deleteAliceTab = (tabId, e) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    if (aliceChats.length <= 1) {
      setAliceChats([
        {
          id: "tab-default",
          title: "Session 1",
          messages: [],
        },
      ]);
      setActiveAliceTabId("tab-default");
      return;
    }
    const idx = aliceChats.findIndex((t) => t.id === tabId);
    const remaining = aliceChats.filter((t) => t.id !== tabId);
    setAliceChats(remaining);
    if (activeAliceTabId === tabId) setActiveAliceTabId(remaining[Math.max(0, idx - 1)].id);
  };
  const startAliceResize = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      const startY = e.clientY;
      const startH = aliceChatHeight;
      const onMove = (ev) =>
        setAliceChatHeight(Math.max(150, Math.min(800, startH + (ev.clientY - startY))));
      const onUp = () => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    },
    [aliceChatHeight],
  );

  const activeAliceTab = aliceChats.find((t) => t.id === activeAliceTabId) || aliceChats[0];
  const activeAliceGoal = activeAliceTab?.goal;
  const aliceMessages = activeAliceTab?.messages || [];
  const { historyRef: aliceHistoryRef, handleScroll: handleAliceHistoryScroll } =
    useAutoFollowScroll(activeAliceTabId, aliceMessages, aliceRunning);
  const isActive = agent.status === "active";
  useEffect(() => {
    onRunningChange(aliceRunning);
  }, [aliceRunning, onRunningChange]);
  return (
    <div
      className="agent-row agent-row--alice-chat agent-row--expandable"
      onClick={() => setExpanded((value) => !value)}
    >
      <span
        className={"agent-dot agent-dot--alice" + (isActive ? " agent-dot--active" : "")}
        aria-hidden="true"
      ></span>
      <span className={"agent-role-name" + (isActive ? " agent-role-name--pulse" : "")}>
        A.L.I.C.E.
      </span>
      <span
        className={
          "agent-badge" + (isActive ? " agent-badge-alice-active" : " agent-badge-alice-idle")
        }
      >
        {isActive ? "ACTIVE" : "STANDBY"}
      </span>
      <span className="agent-current-task">{agent.task}</span>
      <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
      {isExpanded && (
        <div className="alice-chat-container" onClick={(e) => e.stopPropagation()}>
          <div className="alice-chat-tabs-bar">
            {aliceChats.map((tab) => {
              const isActiveTab = tab.id === activeAliceTabId;
              return (
                <div
                  key={tab.id}
                  className={
                    "alice-chat-tab-pill" + (isActiveTab ? " alice-chat-tab-pill--active" : "")
                  }
                  onClick={() => setActiveAliceTabId(tab.id)}
                >
                  <span>{tab.title || "Session"}</span>
                  <span
                    className="alice-chat-tab-close"
                    onClick={(e) => deleteAliceTab(tab.id, e)}
                    title="Close"
                  >
                    ×
                  </span>
                </div>
              );
            })}
            <button className="alice-chat-add-tab-btn" onClick={createAliceTab} title="New Session">
              +
            </button>
          </div>
          <div
            className="alice-chat-history"
            style={{
              height: `${aliceChatHeight}px`,
            }}
            ref={aliceHistoryRef}
            onScroll={handleAliceHistoryScroll}
          >
            {aliceMessages.length === 0 && (
              <div
                style={{
                  padding: "24px",
                  textAlign: "center",
                  color: "var(--muted)",
                  fontSize: 13,
                }}
              >
                Send A.L.I.C.E. an instruction to begin interactive API testing.
              </div>
            )}
            {aliceMessages.map((msg, _msgIdx) => {
              // Thinking message renders as ordered trace boxes + chat bubbles.
              if (msg.type === "thinking") {
                if (!msg.text) return null;
                const segs = parseAliceTurnSegments(msg.text);
                return segs.map((seg, si) => {
                  if (seg.kind === "message") {
                    return (
                      <div key={msg.id + ":m" + si} className="alice-msg-row alice-msg-row--alice">
                        <div className="alice-msg-bubble alice-msg-bubble--alice">
                          <div>{renderMarkdown(seg.text)}</div>
                        </div>
                      </div>
                    );
                  }
                  const segKey = msg.id + ":t" + si;
                  return renderAliceTraceBox(
                    segKey,
                    seg.text,
                    msg.stepData || {},
                    aliceExpandedThinkIds.has(segKey),
                    () =>
                      setAliceExpandedThinkIds((prev) => {
                        const n = new Set(prev);
                        if (n.has(segKey)) n.delete(segKey);
                        else n.add(segKey);
                        return n;
                      }),
                  );
                });
              }
              const isUser = msg.sender === "user";
              if (!isUser && !msg.text) return null;
              return (
                <div
                  key={msg.id}
                  className={
                    "alice-msg-row" + (isUser ? " alice-msg-row--user" : " alice-msg-row--alice")
                  }
                >
                  <div
                    className={
                      "alice-msg-bubble" +
                      (isUser ? " alice-msg-bubble--user" : " alice-msg-bubble--alice")
                    }
                  >
                    {isUser
                      ? renderMarkdown(msg.text)
                      : renderAliceBlocks(msg.text, false, msg.stepData || {})}
                    <div className="alice-msg-meta">
                      <span>{msg.ts}</span>
                    </div>
                  </div>
                </div>
              );
            })}
            {aliceRunning && (
              <div className="alice-msg-row alice-msg-row--alice">
                <div className="alice-typing-bubble">
                  <div className="alice-typing-dot"></div>
                  <div className="alice-typing-dot"></div>
                  <div className="alice-typing-dot"></div>
                </div>
              </div>
            )}
          </div>
          <div className="alice-chat-resizer" onMouseDown={startAliceResize}></div>
          <AliceGoalBar
            goal={activeAliceGoal}
            running={aliceRunning}
            onPause={handleAliceStop}
            onResume={() => submitAliceDirective("/goal resume")}
            onEdit={() => {
              const objective = window.prompt(
                "Update the goal objective",
                activeAliceGoal?.objective || "",
              );
              if (objective?.trim()) submitAliceDirective(`/goal ${objective.trim()}`);
            }}
            onClear={() => submitAliceDirective("/goal clear")}
          />
          <div className="alice-chat-input-bar">
            <input
              className="alice-chat-input"
              placeholder={
                aliceRunning && activeAliceGoal?.status === "active"
                  ? "Add guidance to the active goal…"
                  : "Direct A.L.I.C.E., or use /goal <objective>…"
              }
              value={aliceInputText}
              disabled={aliceRunning && activeAliceGoal?.status !== "active"}
              onInput={(e) => setAliceInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleAliceSend();
                }
              }}
            />
            {aliceRunning && activeAliceGoal?.status !== "active" ? (
              <button className="alice-chat-stop-btn" onClick={handleAliceStop} title="Stop">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="4" y="4" width="16" height="16" rx="1" ry="1"></rect>
                </svg>
              </button>
            ) : (
              <button
                className="alice-chat-input-btn"
                disabled={!aliceInputText.trim()}
                onClick={handleAliceSend}
                title="Send"
              >
                <IconSend />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
