import { _buildAgentsFromLog } from "./_buildAgentsFromLog";
import { useState, useEffect, useRef, useCallback, useContext } from "react";
import { api, formatError } from "../../lib/api";
import { SCAN_MODE_OPTIONS, SCAN_MODE_DEFINITIONS, ScanModeDefinitions, scanModeLabel, csv, defaultPolicyForm, policyToForm, policyPayload } from "../../lib/policy";
import { aliceSessionSubscribe, _aliceFlushRecovery, renderAliceBlocks, renderMarkdown, parseAliceTurnSegments, renderAliceTraceBox } from "../../lib/aliceSession";
import { IconApis, IconPlus, IconPlay, IconShield, IconChevronRight, IconMessageSquare, IconSend } from "../../components/Icons";


export function ApiRunAgentsTab({
  runId,
  scanRunning
}) {
  // ── Agent list state ──────────────────────────────────────────────────────
  const [agents, setAgents] = useState([]);
  const [collapsedAgentIds, setCollapsedAgentIds] = useState(new Set());
  const toggleAgentId = id => setCollapsedAgentIds(prev => {
    const n = new Set(prev);
    n.has(id) ? n.delete(id) : n.add(id);
    return n;
  });

  // ── ALICE chat state ──────────────────────────────────────────────────────
  const [aliceChats, setAliceChats] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(`api_alice_chats_${runId}`) || "null");
      return saved && saved.length ? saved : [{
        id: "tab-default",
        title: "Session 1",
        messages: []
      }];
    } catch {
      return [{
        id: "tab-default",
        title: "Session 1",
        messages: []
      }];
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

  // ── On mount: load sessions, agent log, check alice status ────────────────
  useEffect(() => {
    api.getApiAliceSessions(runId).then(data => {
      const chats = data.chats || [];
      if (chats.length) {
        setAliceChats(chats);
        const aid = data.active_tab_id || "tab-default";
        setActiveAliceTabId(aid);
        activeAliceTabIdRef.current = aid;
      }
    }).catch(() => {});
    api.getApiAgentLog(runId).then(rows => {
      setAgents(_buildAgentsFromLog(rows));
    }).catch(() => {});
    api.getApiAliceStatus(runId).then(st => {
      if (st?.running) {
        setAliceRunning(true);
        connectAliceStream(0);
      }
    }).catch(() => {});
  }, [runId]); // eslint-disable-line react-hooks/exhaustive-deps -- connectAliceStream declared below; keying on runId matches original behavior

  // ── SSE: real-time agent_status events ───────────────────────────────────
  useEffect(() => {
    const es = new EventSource(`/api/api-test-runs/${runId}/events`);
    es.onmessage = ev => {
      try {
        const evt = JSON.parse(ev.data);
        if (evt.type !== "agent_status") return;
        const ts = new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        });
        setAgents(prev => {
          const idx = prev.findIndex(a => a.id === evt.agent_id);
          const histEntry = {
            ts,
            task: evt.current_task || "",
            outcome: evt.outcome || ""
          };
          const existing = idx >= 0 ? prev[idx] : {
            id: evt.agent_id,
            name: evt.role || evt.agent_id,
            status: evt.status,
            task: evt.current_task || "",
            taskHistory: []
          };
          const updated = {
            ...existing,
            name: evt.role || existing.name,
            status: evt.status,
            task: evt.current_task || "",
            taskHistory: [...(existing.taskHistory || []), histEntry]
          };
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = updated;
            return next;
          }
          return [...prev, updated];
        });
      } catch {}
    };
    return () => es.close();
  }, [runId]);

  // ── Poll agent log while scanning or alice is running ────────────────────
  // Merge with existing state so SSE-only (non-persisted) step history is
  // not wiped on every poll cycle.
  useEffect(() => {
    if (!aliceRunning && !scanRunning) return;
    const t = setInterval(() => {
      api.getApiAgentLog(runId).then(rows => {
        const fromLog = _buildAgentsFromLog(rows);
        setAgents(prev => {
          const prevMap = new Map(prev.map(a => [a.id, a]));
          const merged = fromLog.map(a => {
            const existing = prevMap.get(a.id);
            if (!existing) return a;
            // Prefer the longer history — SSE may have more non-persisted entries
            const history = existing.taskHistory.length >= a.taskHistory.length ? existing.taskHistory : a.taskHistory;
            return {
              ...a,
              taskHistory: history
            };
          });
          // Keep SSE-only agents not yet written to the DB
          for (const a of prev) {
            if (!merged.find(m => m.id === a.id)) merged.push(a);
          }
          return merged;
        });
      }).catch(() => {});
    }, 4000);
    return () => clearInterval(t);
  }, [aliceRunning, scanRunning, runId]);

  // ── Persist alice chats ───────────────────────────────────────────────────
  useEffect(() => {
    try {
      localStorage.setItem(`api_alice_chats_${runId}`, JSON.stringify(aliceChats));
      localStorage.setItem(`api_alice_active_tab_${runId}`, activeAliceTabId);
    } catch {}
    api.saveApiAliceSessions(runId, {
      chats: aliceChats,
      active_tab_id: activeAliceTabId
    }).catch(() => {});
  }, [
	aliceChats,
	activeAliceTabId,
	runId
]);

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
  const connectAliceStream = useCallback((cursor = 0) => {
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
    es.onmessage = ev => {
      try {
        const event = JSON.parse(ev.data);
        if ((event.type === "thinking_chunk" || event.type === "message_chunk") && event.delta && event.tab_id && event.msg_id) {
          textAcc[event.msg_id] = (textAcc[event.msg_id] || "") + event.delta;
          const text = textAcc[event.msg_id];
          setAliceChats(prev => prev.map(s => s.id !== event.tab_id ? s : {
            ...s,
            messages: s.messages.map(m => m.id === event.msg_id ? {
              ...m,
              text
            } : m)
          }));
        } else if (event.type === "step_llm_call" && event.tab_id && event.msg_id) {
          const stepData = stepAcc[event.msg_id] || (stepAcc[event.msg_id] = {});
          const entry = stepData[event.step] || (stepData[event.step] = {
            llmMessages: [],
            tools: []
          });
          entry.llmMessages = event.messages || [];
          setAliceChats(prev => prev.map(s => s.id !== event.tab_id ? s : {
            ...s,
            messages: s.messages.map(m => m.id === event.msg_id ? {
              ...m,
              stepData
            } : m)
          }));
        } else if (event.type === "step_tool_call" && event.tab_id && event.msg_id) {
          const stepData = stepAcc[event.msg_id] || (stepAcc[event.msg_id] = {});
          const entry = stepData[event.step] || (stepData[event.step] = {
            llmMessages: [],
            tools: []
          });
          entry.tools.push({
            tool: event.tool,
            input: event.input,
            result: null
          });
          setAliceChats(prev => prev.map(s => s.id !== event.tab_id ? s : {
            ...s,
            messages: s.messages.map(m => m.id === event.msg_id ? {
              ...m,
              stepData
            } : m)
          }));
        } else if (event.type === "step_tool_result" && event.tab_id && event.msg_id) {
          const stepData = stepAcc[event.msg_id] || (stepAcc[event.msg_id] = {});
          const entry = stepData[event.step] || (stepData[event.step] = {
            llmMessages: [],
            tools: []
          });
          const tools = entry.tools;
          if (tools.length > 0 && tools[tools.length - 1].result === null) {
            tools[tools.length - 1].result = event.result;
          }
          setAliceChats(prev => prev.map(s => s.id !== event.tab_id ? s : {
            ...s,
            messages: s.messages.map(m => m.id === event.msg_id ? {
              ...m,
              stepData
            } : m)
          }));
        } else if (event.type === "done") {
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
  }, [runId]);

  // ── ALICE send / stop ─────────────────────────────────────────────────────
  const handleAliceSend = async () => {
    if (!aliceInputText.trim() || aliceRunning) return;
    const userText = aliceInputText;
    setAliceInputText("");
    const tabId = activeAliceTabIdRef.current;
    const thinkId = `think-${Date.now()}`;
    const replyId = `reply-${Date.now() + 1}`;
    const ts = new Date().toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit"
    });
    const userMsg = {
      id: `u-${Date.now()}`,
      sender: "user",
      type: "message",
      text: userText,
      ts
    };
    const thinkMsg = {
      id: thinkId,
      sender: "alice",
      type: "thinking",
      text: "",
      ts
    };
    const replyMsg = {
      id: replyId,
      sender: "alice",
      type: "message",
      text: "",
      ts
    };
    setAliceChats(prev => prev.map(s => s.id !== tabId ? s : {
      ...s,
      messages: [...s.messages, userMsg, thinkMsg, replyMsg]
    }));
    setAliceRunning(true);
    const activeSession = sessionsRef.current.find(s => s.id === tabId) || {
      messages: []
    };
    const history = activeSession.messages.map(m => ({
      sender: m.sender,
      text: m.text
    }));
    try {
      await api.startApiAliceRun(runId, {
        message: userText,
        history,
        tab_id: tabId,
        think_msg_id: thinkId,
        reply_msg_id: replyId
      });
      connectAliceStream(0);
    } catch {
      setAliceRunning(false);
    }
  };
  const handleAliceStop = () => {
    api.stopApiAliceRun(runId).catch(() => {});
    if (streamRef.current) {
      streamRef.current.close();
      streamRef.current = null;
    }
    setAliceRunning(false);
  };

  // ── ALICE tab management ──────────────────────────────────────────────────
  const createAliceTab = () => {
    const id = "tab-" + Date.now();
    setAliceChats(prev => [...prev, {
      id,
      title: `Session ${prev.length + 1}`,
      messages: []
    }]);
    setActiveAliceTabId(id);
  };
  const deleteAliceTab = (tabId, e) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    if (aliceChats.length <= 1) {
      setAliceChats([{
        id: "tab-default",
        title: "Session 1",
        messages: []
      }]);
      setActiveAliceTabId("tab-default");
      return;
    }
    const idx = aliceChats.findIndex(t => t.id === tabId);
    const remaining = aliceChats.filter(t => t.id !== tabId);
    setAliceChats(remaining);
    if (activeAliceTabId === tabId) setActiveAliceTabId(remaining[Math.max(0, idx - 1)].id);
  };
  const startAliceResize = useCallback(e => {
    e.preventDefault();
    e.stopPropagation();
    const startY = e.clientY;
    const startH = aliceChatHeight;
    const onMove = ev => setAliceChatHeight(Math.max(150, Math.min(800, startH + (ev.clientY - startY))));
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [aliceChatHeight]);

  // ── Build agent roster ────────────────────────────────────────────────────
  // API scan roster: A.L.I.C.E. → Test Lead → Specialist → Validator → Reporting
  const buildRoster = () => {
    const byId = Object.fromEntries(agents.map(a => [a.id, a]));
    const specialistChildren = agents.filter(a => a.id.startsWith("specialist-"));
    
    return [{
      id: "alice",
      name: "A.L.I.C.E.",
      status: aliceRunning ? "active" : byId["alice"]?.status || "idle",
      task: aliceRunning ? "Processing directive…" : byId["alice"]?.task || "Waiting for instruction",
      taskHistory: byId["alice"]?.taskHistory || []
    }, {
      id: "scanner",
      name: "Test Lead",
      status: scanRunning && !byId["scanner"] ? "active" : byId["scanner"]?.status || "idle",
      task: scanRunning && !byId["scanner"] ? "Coordinating API pentest" : byId["scanner"]?.task || "Standing by",
      taskHistory: byId["scanner"]?.taskHistory || []
    }, {
      id: "specialist",
      name: "Specialist",
      children: specialistChildren
    }, {
      id: "reporting",
      name: "Reporting",
      status: byId["reporting"]?.status || "idle",
      task: byId["reporting"]?.task || "Standing by",
      taskHistory: byId["reporting"]?.taskHistory || []
    }];
  };
  const activeAliceTab = aliceChats.find(t => t.id === activeAliceTabId) || aliceChats[0];
  const aliceMessages = activeAliceTab?.messages || [];
  const roster = buildRoster();

  // ── Render ────────────────────────────────────────────────────────────────
  return <div className="agents-panel" style={{
    padding: "8px 0"
  }}>
      {roster.map(agent => {
      // ── A.L.I.C.E. row with embedded chat ─────────────────────────────
      if (agent.id === "alice") {
        const isActive = agent.status === "active";
        const isExpanded = !collapsedAgentIds.has("alice");
        return <div key="alice" className="agent-row agent-row--alice-chat agent-row--expandable" onClick={() => toggleAgentId("alice")}>
              <span className={"agent-dot agent-dot--alice" + (isActive ? " agent-dot--active" : "")} aria-hidden="true"></span>
              <span className={"agent-role-name" + (isActive ? " agent-role-name--pulse" : "")}>A.L.I.C.E.</span>
              <span className={"agent-badge" + (isActive ? " agent-badge-alice-active" : " agent-badge-alice-idle")}>
                {isActive ? "ACTIVE" : "STANDBY"}
              </span>
              <span className="agent-current-task">{agent.task}</span>
              <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>
              {isExpanded && <div className="alice-chat-container" onClick={e => e.stopPropagation()}>
                  <div className="alice-chat-tabs-bar">
                    {aliceChats.map(tab => {
                const isActiveTab = tab.id === activeAliceTabId;
                return <div key={tab.id} className={"alice-chat-tab-pill" + (isActiveTab ? " alice-chat-tab-pill--active" : "")} onClick={() => setActiveAliceTabId(tab.id)}>
                          <span>{tab.title || "Session"}</span>
                          <span className="alice-chat-tab-close" onClick={e => deleteAliceTab(tab.id, e)} title="Close">×</span>
                        </div>;
              })}
                    <button className="alice-chat-add-tab-btn" onClick={createAliceTab} title="New Session">+</button>
                  </div>
                  <div className="alice-chat-history" style={{
              height: `${aliceChatHeight}px`
            }} ref={el => {
              if (el) el.scrollTop = el.scrollHeight;
            }}>
                    {aliceMessages.length === 0 && <div style={{
                padding: "24px",
                textAlign: "center",
                color: "var(--muted)",
                fontSize: 13
              }}>
                        Send A.L.I.C.E. an instruction to begin interactive API testing.
                      </div>}
                    {aliceMessages.map((msg, _msgIdx) => {
                // Thinking message renders as ordered trace boxes + chat bubbles.
                if (msg.type === "thinking") {
                  if (!msg.text) return null;
                  const segs = parseAliceTurnSegments(msg.text);
                  return segs.map((seg, si) => {
                    if (seg.kind === "message") {
                      return <div key={msg.id + ":m" + si} className="alice-msg-row alice-msg-row--alice">
                                <div className="alice-msg-bubble alice-msg-bubble--alice">
                                  <div>{renderMarkdown(seg.text)}</div>
                                </div>
                              </div>;
                    }
                    const segKey = msg.id + ":t" + si;
                    return renderAliceTraceBox(segKey, seg.text, msg.stepData || {}, aliceExpandedThinkIds.has(segKey), () => setAliceExpandedThinkIds(prev => {
                      const n = new Set(prev);
                      n.has(segKey) ? n.delete(segKey) : n.add(segKey);
                      return n;
                    }));
                  });
                }
                const isUser = msg.sender === "user";
                if (!isUser && !msg.text) return null;
                return <div key={msg.id} className={"alice-msg-row" + (isUser ? " alice-msg-row--user" : " alice-msg-row--alice")}>
                          <div className={"alice-msg-bubble" + (isUser ? " alice-msg-bubble--user" : " alice-msg-bubble--alice")}>
                            {isUser ? renderMarkdown(msg.text) : renderAliceBlocks(msg.text, false, msg.stepData || {})}
                            <div className="alice-msg-meta"><span>{msg.ts}</span></div>
                          </div>
                        </div>;
              })}
                    {aliceRunning && <div className="alice-msg-row alice-msg-row--alice">
                        <div className="alice-typing-bubble">
                          <div className="alice-typing-dot"></div>
                          <div className="alice-typing-dot"></div>
                          <div className="alice-typing-dot"></div>
                        </div>
                      </div>}
                  </div>
                  <div className="alice-chat-resizer" onMouseDown={startAliceResize}></div>
                  <div className="alice-chat-input-bar">
                    <input className="alice-chat-input" placeholder="Direct A.L.I.C.E. on what to test…" value={aliceInputText} disabled={aliceRunning} onInput={e => setAliceInputText(e.target.value)} onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleAliceSend();
                }
              }} />
                    {aliceRunning ? <button className="alice-chat-stop-btn" onClick={handleAliceStop} title="Stop">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="4" y="4" width="16" height="16" rx="1" ry="1"></rect>
                          </svg>
                        </button> : <button className="alice-chat-input-btn" disabled={!aliceInputText.trim()} onClick={handleAliceSend} title="Send">
                          <IconSend />
                        </button>}
                  </div>
                </div>}
            </div>;
      }

      // ── Specialist container row ───────────────────────────────────────
      if (agent.id === "specialist") {
        const children = agent.children || [];
        const anyActive = children.some(c => c.status === "active");
        const activeCount = children.filter(c => c.status === "active").length;
        const doneCount = children.length - activeCount;
        const summaryTask = children.length === 0 ? "No specialist dispatched" : activeCount > 0 && doneCount > 0 ? `${activeCount} running, ${doneCount} complete` : activeCount > 0 ? `${activeCount} thread${activeCount !== 1 ? "s" : ""} running` : `${doneCount} thread${doneCount !== 1 ? "s" : ""} complete`;
        const canExpand = children.length > 0;
        const isExpanded = canExpand && !collapsedAgentIds.has("specialist");
        return <div key="specialist" className={"agent-row" + (anyActive ? " agent-row--active" : " agent-row--complete") + (canExpand ? " agent-row--expandable" : "")} onClick={canExpand ? () => toggleAgentId("specialist") : undefined}>
              <span className={"agent-dot" + (anyActive ? " agent-dot--active" : "")} aria-hidden="true"></span>
              <span className={"agent-role-name" + (anyActive ? " agent-role-name--pulse" : "")}>Specialist</span>
              <span className={"agent-badge" + (anyActive ? " agent-badge-active" : " agent-badge-complete")}>
                {anyActive ? "ACTIVE" : children.length > 0 ? "COMPLETE" : "IDLE"}
              </span>
              <span className="agent-current-task">{summaryTask}</span>
              {canExpand && <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>}
              {canExpand && isExpanded && <div className="agent-task-history">
                  {children.map(c => {
              const cActive = c.status === "active";
              const cTask = c.task || (c.taskHistory || []).slice(-1)[0]?.task || "Initializing…";
              return <div key={c.id} className={"agent-thread-row" + (cActive ? " agent-thread-row--active" : "")}>
                        <span className={"agent-dot agent-dot--sm" + (cActive ? " agent-dot--active" : "")} aria-hidden="true"></span>
                        <span className="agent-thread-id">{c.id.replace("specialist-", "").replace(/-([0-9]+)$/, " #$1")}</span>
                        <span className={"agent-badge agent-badge--sm" + (cActive ? " agent-badge-active" : " agent-badge-complete")}>
                          {cActive ? "ACTIVE" : "DONE"}
                        </span>
                        <span className="agent-current-task" title={cTask}>{cTask.length > 90 ? cTask.slice(0, 89) + "…" : cTask}</span>
                      </div>;
            })}
                </div>}
            </div>;
      }

      // ── Validator container row ────────────────────────────────────────
      if (agent.id === "validator") {
        const children = agent.children || [];
        const anyActive = children.some(c => c.status === "active");
        const activeCount = children.filter(c => c.status === "active").length;
        const doneCount = children.length - activeCount;
        const summaryTask = children.length === 0 ? "No validation running" : activeCount > 0 && doneCount > 0 ? `${activeCount} validating, ${doneCount} complete` : activeCount > 0 ? `${activeCount} finding${activeCount !== 1 ? "s" : ""} validating` : `${doneCount} finding${doneCount !== 1 ? "s" : ""} validated`;
        const canExpand = children.length > 0;
        const isExpanded = canExpand && !collapsedAgentIds.has("validator");
        return <div key="validator" className={"agent-row" + (anyActive ? " agent-row--active" : " agent-row--complete") + (canExpand ? " agent-row--expandable" : "")} onClick={canExpand ? () => toggleAgentId("validator") : undefined}>
              <span className={"agent-dot" + (anyActive ? " agent-dot--active" : "")} aria-hidden="true"></span>
              <span className={"agent-role-name" + (anyActive ? " agent-role-name--pulse" : "")}>Validator</span>
              <span className={"agent-badge" + (anyActive ? " agent-badge-active" : " agent-badge-complete")}>
                {anyActive ? "ACTIVE" : children.length > 0 ? "COMPLETE" : "IDLE"}
              </span>
              <span className="agent-current-task">{summaryTask}</span>
              {canExpand && <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>}
              {canExpand && isExpanded && <div className="agent-task-history">
                  {children.map(va => {
              const vaActive = va.status === "active";
              const vaTask = va.task || (va.taskHistory || []).slice(-1)[0]?.task || "Initializing…";
              const vaOutcome = (va.taskHistory || []).slice(-1)[0]?.outcome;
              return <div key={va.id} className={"agent-thread-row" + (vaActive ? " agent-thread-row--active" : "")}>
                        <span className={"agent-dot agent-dot--sm" + (vaActive ? " agent-dot--active" : "")} aria-hidden="true"></span>
                        <span className="agent-thread-id">Finding #{va.id.replace("validator-", "")}</span>
                        <span className={"agent-badge agent-badge--sm" + (vaActive ? " agent-badge-active" : " agent-badge-complete")}>
                          {vaActive ? "ACTIVE" : "DONE"}
                        </span>
                        <span className="agent-current-task" title={vaTask}>{vaTask.length > 90 ? vaTask.slice(0, 89) + "…" : vaTask}</span>
                        {vaOutcome && !vaActive && <span className="agent-history-outcome">{vaOutcome}</span>}
                      </div>;
            })}
                </div>}
            </div>;
      }

      // ── Standard agent row (Test Lead, Reporting, etc.) ────────────────
      const isActive = agent.status === "active";
      const isComplete = ["complete", "completed", "done"].includes(agent.status);
      const taskHistory = agent.taskHistory || [];
      const canExpand = taskHistory.length > 1 || taskHistory.some(h => h.outcome);
      const isExpanded = canExpand && !collapsedAgentIds.has(agent.id);
      const task = agent.task || taskHistory.slice(-1)[0]?.task || "";
      return <div key={agent.id} className={"agent-row" + (isActive ? " agent-row--active" : " agent-row--complete") + (canExpand ? " agent-row--expandable" : "")} onClick={canExpand ? () => toggleAgentId(agent.id) : undefined}>
            <span className={"agent-dot" + (isActive ? " agent-dot--active" : "")} aria-hidden="true"></span>
            <span className={"agent-role-name" + (isActive ? " agent-role-name--pulse" : "")}>{agent.name}</span>
            <span className={"agent-badge" + (isActive ? " agent-badge-active" : " agent-badge-complete")}>
              {isActive ? "ACTIVE" : isComplete ? "DONE" : (agent.status || "IDLE").toUpperCase()}
            </span>
            {task && <span className="agent-current-task" title={task}>{task.length > 90 ? task.slice(0, 89) + "…" : task}</span>}
            {canExpand && <span className="activity-expand-chevron">{isExpanded ? "▲" : "▼"}</span>}
            {canExpand && isExpanded && <div className="agent-task-history">
                {taskHistory.slice().reverse().map((h, i) => <div key={i} className="agent-history-entry">
                    <span className="activity-ts">{h.ts || ""}</span>
                    <span className="agent-history-task">{h.task || ""}</span>
                    {h.outcome && <span className="agent-history-outcome">{h.outcome}</span>}
                  </div>)}
              </div>}
          </div>;
    })}
    </div>;
}
