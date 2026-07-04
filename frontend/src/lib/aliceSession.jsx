import { IconBrain } from "../components/Icons";
import { markdownText } from "./utilities";
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
async function aliceSessionStart(runId, tabId, {
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
const parseToolArgs = text => {
  const args = {};
  const jsonMatch = text.match(/\{.*\}/s);
  if (jsonMatch) {
    try {
      return JSON.parse(jsonMatch[0]);
    } catch  {}
  }

  // Extract key-value parameter pairs (e.g. url='http://...')
  const kvRegex = /([a-zA-Z0-9_]+)\s*=\s*(['"][^'"]*['"]|[^,)]+)/g;
  let match;
  while ((match = kvRegex.exec(text)) !== null) {
    let key = match[1];
    let val = match[2].trim();
    if (val.startsWith("'") && val.endsWith("'") || val.startsWith('"') && val.endsWith('"')) {
      val = val.slice(1, -1);
    }
    args[key] = val;
  }
  return Object.keys(args).length > 0 ? args : null;
};
const parseAliceThinking = text => {
  if (!text) return [];
  const blocks = [];
  const lines = text.split("\n");
  let currentParagraph = [];
  let inCodeBlock = false;
  let codeLang = "";
  const toolCntByStep = {}; // track how many Executing tool lines seen per step
  let codeContent = [];
  let inToolCall = false;
  let toolCallContent = [];
  let inToolResponse = false;
  let toolResponseContent = [];
  for (let line of lines) {
    const trimmed = line.trim();

    // Code block transition
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        // End of code block
        blocks.push({
          type: "code",
          lang: codeLang,
          text: codeContent.join("\n")
        });
        inCodeBlock = false;
        codeContent = [];
      } else {
        // Start of code block
        // Flush existing paragraph first
        if (currentParagraph.length > 0) {
          blocks.push({
            type: "thought",
            text: currentParagraph.join("\n")
          });
          currentParagraph = [];
        }
        inCodeBlock = true;
        codeLang = line.slice(3).trim();
      }
      continue;
    }
    if (inCodeBlock) {
      codeContent.push(line);
      continue;
    }

    // Tool Call tag handling (multi-line)
    if (inToolCall) {
      if (trimmed.includes("</tool_call>")) {
        const parts = line.split("</tool_call>");
        if (parts[0]) toolCallContent.push(parts[0]);
        inToolCall = false;
        const rawText = toolCallContent.join("\n");
        let toolName = "unknown";
        let toolArgsText = rawText;
        try {
          const parsed = JSON.parse(rawText.trim());
          if (parsed && parsed.name) {
            toolName = parsed.name;
            if (parsed.arguments) {
              toolArgsText = JSON.stringify(parsed.arguments);
            }
          }
        } catch  {
          const nameMatch = rawText.match(/"name"\s*:\s*"([^"]+)"/);
          if (nameMatch) toolName = nameMatch[1];
        }
        blocks.push({
          type: "tool_call",
          tool: toolName,
          text: toolArgsText
        });
        toolCallContent = [];
      } else {
        toolCallContent.push(line);
      }
      continue;
    }

    // Tool Response tag handling (multi-line)
    if (inToolResponse) {
      if (trimmed.includes("</tool_response>")) {
        const parts = line.split("</tool_response>");
        if (parts[0]) toolResponseContent.push(parts[0]);
        inToolResponse = false;
        blocks.push({
          type: "tool_response",
          text: toolResponseContent.join("\n")
        });
        toolResponseContent = [];
      } else {
        toolResponseContent.push(line);
      }
      continue;
    }

    // Start of Tool Call block
    if (trimmed.includes("<tool_call>")) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      if (trimmed.includes("</tool_call>")) {
        const startIndex = line.indexOf("<tool_call>");
        const endIndex = line.indexOf("</tool_call>");
        const content = line.substring(startIndex + 11, endIndex);
        let toolName = "unknown";
        let toolArgsText = content;
        try {
          const parsed = JSON.parse(content.trim());
          if (parsed && parsed.name) {
            toolName = parsed.name;
            if (parsed.arguments) {
              toolArgsText = JSON.stringify(parsed.arguments);
            }
          }
        } catch  {
          const nameMatch = content.match(/"name"\s*:\s*"([^"]+)"/);
          if (nameMatch) toolName = nameMatch[1];
        }
        blocks.push({
          type: "tool_call",
          tool: toolName,
          text: toolArgsText
        });
      } else {
        inToolCall = true;
        const parts = line.split("<tool_call>");
        if (parts[1]) toolCallContent.push(parts[1]);
      }
      continue;
    }

    // Start of Tool Response block
    if (trimmed.includes("<tool_response>")) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      if (trimmed.includes("</tool_response>")) {
        const startIndex = line.indexOf("<tool_response>");
        const endIndex = line.indexOf("</tool_response>");
        const content = line.substring(startIndex + 15, endIndex);
        blocks.push({
          type: "tool_response",
          text: content
        });
      } else {
        inToolResponse = true;
        const parts = line.split("<tool_response>");
        if (parts[1]) toolResponseContent.push(parts[1]);
      }
      continue;
    }

    // Step/Status logs
    if (trimmed.startsWith("[A.L.I.C.E. Initializing]") || trimmed.includes("Mapped target sitemap")) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "status",
        status: "initializing",
        text: trimmed
      });
      continue;
    }
    if (trimmed.startsWith("Evaluating prompt scope compliance:") || trimmed.includes("In-Scope verified")) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "status",
        status: "scope_check",
        text: trimmed
      });
      continue;
    }
    if (trimmed.startsWith("Scope compliance verified") || trimmed.includes("Starting agentic assessment loop")) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "status",
        status: "scope_check",
        text: trimmed
      });
      continue;
    }
    if (trimmed.startsWith("Routing directives to the LLM agent model:") || trimmed.includes("Routing directives")) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "status",
        status: "routing",
        text: trimmed
      });
      continue;
    }

    // [Step N] Calling LLM...
    const stepLLMMatch = trimmed.match(/^\[Step (\d+)\] Calling LLM/);
    if (stepLLMMatch) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "status",
        status: "routing",
        text: trimmed,
        stepNum: parseInt(stepLLMMatch[1]),
        stepKind: "llm_call"
      });
      continue;
    }

    // [Step N] Executing tool: name  (must come before generic toolCallRegex)
    const stepExecMatch = trimmed.match(/^\[Step (\d+)\] Executing tool:\s*(\S+)/);
    if (stepExecMatch) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      const stepNum = parseInt(stepExecMatch[1]);
      if (!toolCntByStep[stepNum]) toolCntByStep[stepNum] = 0;
      const toolIdx = toolCntByStep[stepNum]++;
      blocks.push({
        type: "status",
        status: "routing",
        text: trimmed,
        stepNum,
        stepKind: "tool_call",
        toolName: stepExecMatch[2],
        toolIdx
      });
      continue;
    }

    // [Step N] Tool result (N chars)
    const stepResultMatch = trimmed.match(/^\[Step (\d+)\] Tool result/);
    if (stepResultMatch) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      const stepNum = parseInt(stepResultMatch[1]);
      const toolIdx = (toolCntByStep[stepNum] || 1) - 1;
      blocks.push({
        type: "status",
        status: "routing",
        text: trimmed,
        stepNum,
        stepKind: "tool_result",
        toolIdx
      });
      continue;
    }
    if (trimmed.startsWith("[A.L.I.C.E. Boundary Violation Alert]")) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "alert",
        level: "danger",
        title: "Boundary Violation",
        text: trimmed
      });
      continue;
    }
    if (trimmed.startsWith("[ALICE Error]")) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "alert",
        level: "error",
        title: "Error",
        text: trimmed
      });
      continue;
    }

    // Generic tool execution detection (non-step-prefixed lines)
    const toolCallRegex = /(?:Calling|Invoking|Executing)\s+tool:?\s+([a-zA-Z0-9_]+)|(?:tool_call|toolCall):\s*([a-zA-Z0-9_]+)/i;
    const match = trimmed.match(toolCallRegex);
    if (match) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n")
        });
        currentParagraph = [];
      }
      const toolName = match[1] || match[2];
      blocks.push({
        type: "tool_call",
        tool: toolName,
        text: trimmed
      });
      continue;
    }

    // Standard text line
    if (trimmed !== "") {
      currentParagraph.push(line);
    } else if (currentParagraph.length > 0) {
      blocks.push({
        type: "thought",
        text: currentParagraph.join("\n")
      });
      currentParagraph = [];
    }
  }

  // Flush remaining paragraphs or code blocks
  if (inCodeBlock && codeContent.length > 0) {
    blocks.push({
      type: "code",
      lang: codeLang,
      text: codeContent.join("\n")
    });
  } else if (inToolCall && toolCallContent.length > 0) {
    blocks.push({
      type: "tool_call",
      tool: "unknown",
      text: toolCallContent.join("\n")
    });
  } else if (inToolResponse && toolResponseContent.length > 0) {
    blocks.push({
      type: "tool_response",
      text: toolResponseContent.join("\n")
    });
  } else if (currentParagraph.length > 0) {
    blocks.push({
      type: "thought",
      text: currentParagraph.join("\n")
    });
  }
  return blocks;
};
export const renderMarkdown = text => {
  if (!text) return "";
  if (typeof text !== "string") text = markdownText(text);
  if (!text) return "";
  const lines = text.split("\n");
  const elements = [];
  let inList = false;
  let listItems = [];
  let codeBlockContent = [];
  let inCodeBlock = false;
  let codeBlockLang = "";
  const renderTextWithFormatting = txt => {
    const inlineRegex = /(`[^`]+`|\*\*[^*]+\*\*)/g;
    const segments = txt.split(inlineRegex);
    return segments.map((seg, _idx) => {
      if (seg.startsWith("`") && seg.endsWith("`")) {
        return <code className="alice-inline-code">{seg.slice(1, -1)}</code>;
      }
      if (seg.startsWith("**") && seg.endsWith("**")) {
        return <strong className="alice-bold-text">{seg.slice(2, -2)}</strong>;
      }
      return seg;
    });
  };
  const parseTableRow = rowText => {
    const cells = rowText.split("|").map(c => c.trim());
    if (cells[0] === "") cells.shift();
    if (cells[cells.length - 1] === "") cells.pop();
    return cells;
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Code blocks
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        inCodeBlock = false;
        elements.push(<div className="alice-code-block-wrapper">
            <div className="alice-code-block-header">
              <span className="alice-code-block-lang">{codeBlockLang || "text"}</span>
            </div>
            <pre className="alice-code-block"><code>{codeBlockContent.join("\n")}</code></pre>
          </div>);
        codeBlockContent = [];
      } else {
        if (inList) {
          elements.push(<ul className="alice-markdown-list">{listItems.map(item => <li>{renderTextWithFormatting(item)}</li>)}</ul>);
          inList = false;
          listItems = [];
        }
        inCodeBlock = true;
        codeBlockLang = line.slice(3).trim();
      }
      continue;
    }
    if (inCodeBlock) {
      codeBlockContent.push(line);
      continue;
    }

    // Tables
    if (trimmed.startsWith("|")) {
      if (inList) {
        elements.push(<ul className="alice-markdown-list">{listItems.map(item => <li>{renderTextWithFormatting(item)}</li>)}</ul>);
        inList = false;
        listItems = [];
      }
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i].trim());
        i++;
      }
      i--; // Adjust loop counter

      if (tableLines.length >= 2) {
        const headers = parseTableRow(tableLines[0]);
        const rows = [];
        const bodyLines = tableLines.slice(2);
        for (const rLine of bodyLines) {
          if (rLine.includes("---")) continue;
          rows.push(parseTableRow(rLine));
        }
        elements.push(<div className="alice-table-wrapper">
            <table className="alice-table">
              <thead>
                <tr>
                  {headers.map(h => <th>{renderTextWithFormatting(h)}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.map(row => <tr>
                    {row.map(cell => <td>{renderTextWithFormatting(cell)}</td>)}
                  </tr>)}
              </tbody>
            </table>
          </div>);
        continue;
      }
    }

    // Headers
    if (trimmed.startsWith("### ")) {
      if (inList) {
        elements.push(<ul className="alice-markdown-list">{listItems.map(item => <li>{renderTextWithFormatting(item)}</li>)}</ul>);
        inList = false;
        listItems = [];
      }
      elements.push(<h4 className="alice-md-h3">{renderTextWithFormatting(trimmed.slice(4))}</h4>);
      continue;
    }
    if (trimmed.startsWith("## ")) {
      if (inList) {
        elements.push(<ul className="alice-markdown-list">{listItems.map(item => <li>{renderTextWithFormatting(item)}</li>)}</ul>);
        inList = false;
        listItems = [];
      }
      elements.push(<h3 className="alice-md-h2">{renderTextWithFormatting(trimmed.slice(3))}</h3>);
      continue;
    }

    // Lists
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      inList = true;
      listItems.push(trimmed.slice(2));
      continue;
    }

    // Paragraph
    if (trimmed === "") {
      if (inList) {
        elements.push(<ul className="alice-markdown-list">{listItems.map(item => <li>{renderTextWithFormatting(item)}</li>)}</ul>);
        inList = false;
        listItems = [];
      }
      elements.push(<div className="alice-md-space"></div>);
    } else {
      if (inList) {
        elements.push(<ul className="alice-markdown-list">{listItems.map(item => <li>{renderTextWithFormatting(item)}</li>)}</ul>);
        inList = false;
        listItems = [];
      }
      elements.push(<p className="alice-md-p">{renderTextWithFormatting(line)}</p>);
    }
  }
  if (inList) {
    elements.push(<ul className="alice-markdown-list">{listItems.map(item => <li>{renderTextWithFormatting(item)}</li>)}</ul>);
  }
  if (inCodeBlock && codeBlockContent.length > 0) {
    elements.push(<div className="alice-code-block-wrapper">
        <div className="alice-code-block-header">
          <span className="alice-code-block-lang">{codeBlockLang || "text"}</span>
        </div>
        <pre className="alice-code-block"><code>{codeBlockContent.join("\n")}</code></pre>
      </div>);
  }
  return elements;
};

// Summarize an ALICE thinking trace into a one-line label for the collapsed
// box: the last step number and the last tool that was called.
const aliceTraceSummary = text => {
  const blocks = parseAliceThinking(text);
  let lastStep = 0;
  let lastTool = null;
  for (const b of blocks) {
    if (b.type === "status" && b.stepNum) lastStep = Math.max(lastStep, b.stepNum);
    if (b.type === "status" && b.stepKind === "tool_call" && b.toolName) lastTool = b.toolName;
    if (b.type === "tool_call" && b.tool) lastTool = b.tool;
  }
  let label = lastStep > 0 ? `Step ${lastStep}` : "Reasoning";
  if (lastTool) label += ` · ${lastTool}`;
  return {
    label,
    lastStep,
    lastTool
  };
};

// Split a turn's thinking text into an ordered list of segments. Commentary the
// model emits mid-run is wrapped in [[ALICE_SAY]]...[[/ALICE_SAY]] markers; each
// such marker becomes a prominent chat bubble that breaks the surrounding trace
// into a box-above / box-below (Claude-code style).
const ALICE_SAY_RE = /\[\[ALICE_SAY\]\]([\s\S]*?)\[\[\/ALICE_SAY\]\]/g;
export const parseAliceTurnSegments = text => {
  if (!text) return [];
  const segments = [];
  let lastIndex = 0;
  let m;
  ALICE_SAY_RE.lastIndex = 0;
  while ((m = ALICE_SAY_RE.exec(text)) !== null) {
    const before = text.slice(lastIndex, m.index);
    if (before.trim()) segments.push({
      kind: "trace",
      text: before
    });
    const said = m[1].trim();
    if (said) segments.push({
      kind: "message",
      text: said
    });
    lastIndex = m.index + m[0].length;
  }
  const tail = text.slice(lastIndex);
  if (tail.trim()) segments.push({
    kind: "trace",
    text: tail
  });
  return segments;
};

// Render the collapsed "steps" box. Low-prominence; the summary shows the last
// step + tool, and expands to the full trace for that segment.
export const renderAliceTraceBox = (segKey, segText, stepData, isOpen, toggle) => {
  const traceSummary = aliceTraceSummary(segText);
  return <div key={segKey} className="alice-msg-row alice-msg-row--alice alice-msg-row--trace">
      <div className={"alice-trace-box" + (isOpen ? " alice-trace-box--open" : "")}>
        <div className="alice-trace-summary" onClick={toggle}>
          <IconBrain />
          <span className="alice-trace-summary-label">{traceSummary.label}</span>
          <span className="alice-trace-caret">{isOpen ? "▼" : "▶"}</span>
        </div>
        {isOpen && <div className="alice-thinking-inline">
            {renderAliceBlocks(segText, true, stepData || {})}
          </div>}
      </div>
    </div>;
};
export const renderAliceBlocks = (text, isThinking, stepData = {}) => {
  const blocks = parseAliceThinking(text);
  return blocks.map((block, idx) => {
    if (block.type === "status") {
      let icon = <span className="alice-status-dot"></span>;
      if (block.status === "initializing") {
        icon = <span className="alice-status-icon alice-status-icon--init">⚙️</span>;
      } else if (block.status === "scope_check") {
        icon = <span className="alice-status-icon alice-status-icon--success">🛡️</span>;
      } else if (block.status === "routing") {
        icon = <span className="alice-status-icon alice-status-icon--routing">⚡</span>;
      }

      // Expandable step blocks
      if (block.stepKind) {
        const stepEntry = (stepData || {})[block.stepNum] || {};
        let detailContent = null;
        if (block.stepKind === "llm_call" && stepEntry.llmMessages && stepEntry.llmMessages.length > 0) {
          detailContent = <div className="alice-step-detail">
              {stepEntry.llmMessages.map((m, i) => <div key={i} className={"alice-step-msg alice-step-msg--" + m.role}>
                  <span className="alice-step-msg-role">{m.role}</span>
                  <pre className="alice-step-msg-content">{m.content}</pre>
                </div>)}
            </div>;
        } else if (block.stepKind === "tool_call") {
          const toolEntry = stepEntry.tools && stepEntry.tools[block.toolIdx];
          if (toolEntry && toolEntry.input !== null && toolEntry.input !== undefined) {
            let inputStr;
            try {
              inputStr = JSON.stringify(toolEntry.input, null, 2);
            } catch  {
              inputStr = String(toolEntry.input);
            }
            detailContent = <div className="alice-step-detail">
                <pre className="alice-step-msg-content">{inputStr}</pre>
              </div>;
          }
        } else if (block.stepKind === "tool_result") {
          const toolEntry = stepEntry.tools && stepEntry.tools[block.toolIdx];
          if (toolEntry && toolEntry.result !== null && toolEntry.result !== undefined) {
            detailContent = <div className="alice-step-detail">
                <pre className="alice-step-msg-content">{toolEntry.result}</pre>
              </div>;
          }
        }
        if (detailContent) {
          return <details key={idx} className={"alice-step-details alice-step-details--" + block.stepKind} style={isThinking ? {} : {
            margin: "6px 0"
          }}>
              <summary className="alice-thinking-status-row alice-thinking-status-row--routing alice-step-summary">
                {icon}
                <span className="alice-status-text">{block.text}</span>
                <span className="alice-step-expand-caret">▶</span>
              </summary>
              {detailContent}
            </details>;
        }
      }
      return <div key={idx} className={"alice-thinking-status-row alice-thinking-status-row--" + block.status} style={isThinking ? {} : {
        margin: "6px 0"
      }}>
          {icon}
          <span className="alice-status-text">{block.text}</span>
        </div>;
    }
    if (block.type === "alert") {
      return <div key={idx} className={"alice-thinking-alert alice-thinking-alert--" + block.level} style={isThinking ? {} : {
        margin: "6px 0"
      }}>
          <span className="alice-alert-icon">⚠️</span>
          <div className="alice-alert-content">
            <div className="alice-alert-title">{block.title}</div>
            <div className="alice-alert-text">{block.text}</div>
          </div>
        </div>;
    }
    if (block.type === "tool_call") {
      const parsedArgs = parseToolArgs(block.text);
      return <div key={idx} className="alice-thinking-tool-call" style={{
        width: "100%",
        margin: "6px 0"
      }}>
          <div className="alice-tool-header-row">
            <span className="alice-tool-prompt">$</span>
            <span className="alice-tool-badge">CALL TOOL</span>
            <span className="alice-tool-name">{block.tool}</span>
          </div>
          {parsedArgs ? <div className="alice-tool-args-card">
              {Object.entries(parsedArgs).map(([key, val]) => <div key={key} className="alice-tool-arg-row">
                  <span className="alice-tool-arg-key">{key}:</span>
                  <span className="alice-tool-arg-val">{markdownText(val)}</span>
                </div>)}
            </div> : <div className="alice-tool-text">{block.text}</div>}
        </div>;
    }
    if (block.type === "tool_response") {
      let isJson = false;
      let formattedResponse = block.text;
      try {
        const parsed = JSON.parse(block.text.trim());
        formattedResponse = JSON.stringify(parsed, null, 2);
        isJson = true;
      } catch  {}
      return <div key={idx} className="alice-thinking-tool-response" style={{
        width: "100%",
        margin: "6px 0"
      }}>
          <div className="alice-tool-header-row" style={{
          borderLeft: "3px solid #10b981",
          paddingLeft: "10px"
        }}>
            <span className="alice-tool-prompt" style={{
            color: "#10b981"
          }}>←</span>
            <span className="alice-tool-badge" style={{
            background: "rgba(16, 185, 129, 0.15)",
            color: "#34d399"
          }}>RESPONSE</span>
          </div>
          <div className="alice-code-block-wrapper" style={{
          marginTop: "4px"
        }}>
            <div className="alice-code-block-header">
              <span className="alice-code-block-lang">{isJson ? "json" : "text"}</span>
            </div>
            <pre className="alice-code-block"><code style={{
              fontSize: "10.5px"
            }}>{formattedResponse}</code></pre>
          </div>
        </div>;
    }
    if (block.type === "code") {
      return <div key={idx} className="alice-code-block-wrapper">
          <div className="alice-code-block-header">
            <span className="alice-code-block-lang">{block.lang || "json"}</span>
          </div>
          <pre className="alice-code-block"><code>{block.text}</code></pre>
        </div>;
    }
    if (isThinking) {
      return <p key={idx} className="alice-thinking-paragraph">{block.text}</p>;
    } else {
      return <div key={idx} className="alice-reply-paragraph-wrapper">{renderMarkdown(block.text)}</div>;
    }
  });
};