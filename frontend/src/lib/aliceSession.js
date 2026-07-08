// ── A.L.I.C.E. Session Manager ─────────────────────────────────────────────
// Module-level singleton: keeps the stream reader loop alive even when the
// TestRunDetail component unmounts (user navigates away). Subscribers
// (React setState callbacks) are registered/deregistered as the component
// mounts and unmounts. On re-mount, the component can re-subscribe and
// immediately get the current live state.
export const aliceSessionStore = {};
export function getAliceSession(runId, tabId) {
  const key = `${runId}:${tabId}`;
  if (!aliceSessionStore[key]) {
    aliceSessionStore[key] = {
      active: false,
      abortController: null,
      thinkMsgId: null,
      replyMsgId: null,
      accumulatedThought: "",
      accumulatedMessage: "",
      stepData: {},
      subscribers: new Set()
    };
  }
  return aliceSessionStore[key];
}
export function aliceSessionSubscribe(runId, tabId, handlers) {
  const session = getAliceSession(runId, tabId);
  session.subscribers.add(handlers);
  return () => session.subscribers.delete(handlers);
}
export function aliceSessionAbort(runId, tabId) {
  const key = `${runId}:${tabId}`;
  const session = aliceSessionStore[key];
  if (session?.abortController) {
    session.abortController.abort();
  }
}
export const _aliceFlushRecovery = (runId, tabId, thinkMsgId, replyMsgId, thought, message) => {
  try {
    localStorage.setItem(`alice_recover_${runId}:${tabId}`, JSON.stringify({
      thinkMsgId,
      replyMsgId,
      thought,
      message
    }));
  } catch  {}
};

// Connect to /alice/stream?cursor=N and pump events through the session.
// Called both for fresh sessions (cursor=0) and reconnects after a page refresh.
export async function aliceSessionConnect(runId, tabId, {
  thinkMsgId,
  replyMsgId,
  cursor = 0,
  onFinish,
  onFail
}) {
  const session = getAliceSession(runId, tabId);
  if (session.active) return;
  session.active = true;
  session.thinkMsgId = thinkMsgId;
  session.replyMsgId = replyMsgId;
  // Re-accumulate from cursor 0 on every connect so the totals are always correct.
  session.accumulatedThought = "";
  session.accumulatedMessage = "";
  session.stepData = {};
  const controller = new AbortController();
  session.abortController = controller;
  try {
    const response = await fetch(`/api/test-runs/${runId}/alice/stream?cursor=${cursor}`, {
      signal: controller.signal
    });
    if (!response.ok) throw new Error(`HTTP error ${response.status}`);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const {
        value,
        done
      } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {
        stream: true
      });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data: ")) continue;
        try {
          const event = JSON.parse(trimmed.slice(6));
          if (event.type === "thinking_chunk" && event.delta) session.accumulatedThought += event.delta;else if (event.type === "message_chunk" && event.delta) session.accumulatedMessage += event.delta;else if (event.type === "done") {
            if (event.thought) session.accumulatedThought = event.thought;
            if (event.message) session.accumulatedMessage = event.message;
          } else if (event.type === "step_llm_call") {
            if (!session.stepData[event.step]) session.stepData[event.step] = {
              llmMessages: [],
              tools: []
            };
            session.stepData[event.step].llmMessages = event.messages || [];
          } else if (event.type === "step_tool_call") {
            if (!session.stepData[event.step]) session.stepData[event.step] = {
              llmMessages: [],
              tools: []
            };
            session.stepData[event.step].tools.push({
              tool: event.tool,
              input: event.input,
              result: null
            });
          } else if (event.type === "step_tool_result") {
            if (!session.stepData[event.step]) session.stepData[event.step] = {
              llmMessages: [],
              tools: []
            };
            const tools = session.stepData[event.step].tools;
            if (tools.length > 0 && tools[tools.length - 1].result === null) {
              tools[tools.length - 1].result = event.result;
            }
          }
          _aliceFlushRecovery(runId, tabId, thinkMsgId, replyMsgId, session.accumulatedThought, session.accumulatedMessage);
          session.subscribers.forEach(h => h.onChunk && h.onChunk(event));
        } catch  {}
      }
    }
    session.subscribers.forEach(h => h.onDone && h.onDone());
    if (onFinish) onFinish();
  } catch (err) {
    session.subscribers.forEach(h => h.onError && h.onError(err));
    if (onFail) onFail(err);
  } finally {
    session.active = false;
    session.abortController = null;
  }
}

// Start a new ALICE turn: POST to /alice/run (starts background task on server),
// then open the event stream so the client receives events in real time.
export async function aliceSessionStart(runId, tabId, {
  userText,
  historyPayload,
  thinkMsgId,
  replyMsgId,
  onFinish,
  onFail
}) {
  // Seed recovery immediately so a fast refresh can find the message IDs.
  _aliceFlushRecovery(runId, tabId, thinkMsgId, replyMsgId, "", "");
  try {
    const resp = await fetch(`/api/test-runs/${runId}/alice/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message: userText,
        history: historyPayload,
        tab_id: tabId,
        think_msg_id: thinkMsgId,
        reply_msg_id: replyMsgId
      })
    });
    if (!resp.ok) throw new Error(`HTTP error ${resp.status}`);
  } catch (err) {
    if (onFail) onFail(err);
    return;
  }
  await aliceSessionConnect(runId, tabId, {
    thinkMsgId,
    replyMsgId,
    cursor: 0,
    onFinish,
    onFail
  });
}
