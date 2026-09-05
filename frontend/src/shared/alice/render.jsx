import { parseAliceThinking } from "./thinking.js";

import { renderMarkdown } from "./markdown.jsx";

import { IconBrain } from "../ui/Icons.jsx";
import { markdownText } from "../lib/markdown.js";
// ── A.L.I.C.E. trace + markdown rendering ──────────────────────────────────
// Pure view helpers that turn ALICE's streamed thinking/reply text into React
// elements. No session or network state lives here — see aliceSession.js.

const parseToolArgs = (text) => {
  const args = {};
  const jsonMatch = text.match(/\{.*\}/s);
  if (jsonMatch) {
    try {
      return JSON.parse(jsonMatch[0]);
    } catch {}
  }

  // Extract key-value parameter pairs (e.g. url='http://...')
  const kvRegex = /([a-zA-Z0-9_]+)\s*=\s*(['"][^'"]*['"]|[^,)]+)/g;
  let match;
  while ((match = kvRegex.exec(text)) !== null) {
    let key = match[1];
    let val = match[2].trim();
    if ((val.startsWith("'") && val.endsWith("'")) || (val.startsWith('"') && val.endsWith('"'))) {
      val = val.slice(1, -1);
    }
    args[key] = val;
  }
  return Object.keys(args).length > 0 ? args : null;
};

// Summarize an ALICE thinking trace into a one-line label for the collapsed
// box: the last step number and the last tool that was called.
const aliceTraceSummary = (text) => {
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
    lastTool,
  };
};

// Split a turn's thinking text into an ordered list of segments. Commentary the
// model emits mid-run is wrapped in [[ALICE_SAY]]...[[/ALICE_SAY]] markers; each
// such marker becomes a prominent chat bubble that breaks the surrounding trace
// into a box-above / box-below (Claude-code style).

// Render the collapsed "steps" box. Low-prominence; the summary shows the last
// step + tool, and expands to the full trace for that segment.
export const renderAliceTraceBox = (segKey, segText, stepData, isOpen, toggle) => {
  const traceSummary = aliceTraceSummary(segText);
  return (
    <div key={segKey} className="alice-msg-row alice-msg-row--alice alice-msg-row--trace">
      <div className={"alice-trace-box" + (isOpen ? " alice-trace-box--open" : "")}>
        <div className="alice-trace-summary" onClick={toggle}>
          <IconBrain />
          <span className="alice-trace-summary-label">{traceSummary.label}</span>
          <span className="alice-trace-caret">{isOpen ? "▼" : "▶"}</span>
        </div>
        {isOpen && (
          <div className="alice-thinking-inline">
            {renderAliceBlocks(segText, true, stepData || {})}
          </div>
        )}
      </div>
    </div>
  );
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
        if (
          block.stepKind === "llm_call" &&
          stepEntry.llmMessages &&
          stepEntry.llmMessages.length > 0
        ) {
          detailContent = (
            <div className="alice-step-detail">
              {stepEntry.llmMessages.map((m, i) => (
                <div key={i} className={"alice-step-msg alice-step-msg--" + m.role}>
                  <span className="alice-step-msg-role">{m.role}</span>
                  <pre className="alice-step-msg-content">{m.content}</pre>
                </div>
              ))}
            </div>
          );
        } else if (block.stepKind === "tool_call") {
          const toolEntry = stepEntry.tools && stepEntry.tools[block.toolIdx];
          if (toolEntry && toolEntry.input !== null && toolEntry.input !== undefined) {
            let inputStr;
            try {
              inputStr = JSON.stringify(toolEntry.input, null, 2);
            } catch {
              inputStr = String(toolEntry.input);
            }
            detailContent = (
              <div className="alice-step-detail">
                <pre className="alice-step-msg-content">{inputStr}</pre>
              </div>
            );
          }
        } else if (block.stepKind === "tool_result") {
          const toolEntry = stepEntry.tools && stepEntry.tools[block.toolIdx];
          if (toolEntry && toolEntry.result !== null && toolEntry.result !== undefined) {
            detailContent = (
              <div className="alice-step-detail">
                <pre className="alice-step-msg-content">{toolEntry.result}</pre>
              </div>
            );
          }
        }
        if (detailContent) {
          return (
            <details
              key={idx}
              className={"alice-step-details alice-step-details--" + block.stepKind}
              style={
                isThinking
                  ? {}
                  : {
                      margin: "6px 0",
                    }
              }
            >
              <summary className="alice-thinking-status-row alice-thinking-status-row--routing alice-step-summary">
                {icon}
                <span className="alice-status-text">{block.text}</span>
                <span className="alice-step-expand-caret">▶</span>
              </summary>
              {detailContent}
            </details>
          );
        }
      }
      return (
        <div
          key={idx}
          className={"alice-thinking-status-row alice-thinking-status-row--" + block.status}
          style={
            isThinking
              ? {}
              : {
                  margin: "6px 0",
                }
          }
        >
          {icon}
          <span className="alice-status-text">{block.text}</span>
        </div>
      );
    }
    if (block.type === "alert") {
      return (
        <div
          key={idx}
          className={"alice-thinking-alert alice-thinking-alert--" + block.level}
          style={
            isThinking
              ? {}
              : {
                  margin: "6px 0",
                }
          }
        >
          <span className="alice-alert-icon">⚠️</span>
          <div className="alice-alert-content">
            <div className="alice-alert-title">{block.title}</div>
            <div className="alice-alert-text">{block.text}</div>
          </div>
        </div>
      );
    }
    if (block.type === "tool_call") {
      const parsedArgs = parseToolArgs(block.text);
      return (
        <div
          key={idx}
          className="alice-thinking-tool-call"
          style={{
            width: "100%",
            margin: "6px 0",
          }}
        >
          <div className="alice-tool-header-row">
            <span className="alice-tool-prompt">$</span>
            <span className="alice-tool-badge">CALL TOOL</span>
            <span className="alice-tool-name">{block.tool}</span>
          </div>
          {parsedArgs ? (
            <div className="alice-tool-args-card">
              {Object.entries(parsedArgs).map(([key, val]) => (
                <div key={key} className="alice-tool-arg-row">
                  <span className="alice-tool-arg-key">{key}:</span>
                  <span className="alice-tool-arg-val">{markdownText(val)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="alice-tool-text">{block.text}</div>
          )}
        </div>
      );
    }
    if (block.type === "tool_response") {
      let isJson = false;
      let formattedResponse = block.text;
      try {
        const parsed = JSON.parse(block.text.trim());
        formattedResponse = JSON.stringify(parsed, null, 2);
        isJson = true;
      } catch {}
      return (
        <div
          key={idx}
          className="alice-thinking-tool-response"
          style={{
            width: "100%",
            margin: "6px 0",
          }}
        >
          <div
            className="alice-tool-header-row"
            style={{
              borderLeft: "3px solid #10b981",
              paddingLeft: "10px",
            }}
          >
            <span
              className="alice-tool-prompt"
              style={{
                color: "#10b981",
              }}
            >
              ←
            </span>
            <span
              className="alice-tool-badge"
              style={{
                background: "rgba(16, 185, 129, 0.15)",
                color: "#34d399",
              }}
            >
              RESPONSE
            </span>
          </div>
          <div
            className="alice-code-block-wrapper"
            style={{
              marginTop: "4px",
            }}
          >
            <div className="alice-code-block-header">
              <span className="alice-code-block-lang">{isJson ? "json" : "text"}</span>
            </div>
            <pre className="alice-code-block">
              <code
                style={{
                  fontSize: "10.5px",
                }}
              >
                {formattedResponse}
              </code>
            </pre>
          </div>
        </div>
      );
    }
    if (block.type === "code") {
      return (
        <div key={idx} className="alice-code-block-wrapper">
          <div className="alice-code-block-header">
            <span className="alice-code-block-lang">{block.lang || "json"}</span>
          </div>
          <pre className="alice-code-block">
            <code>{block.text}</code>
          </pre>
        </div>
      );
    }
    if (isThinking) {
      return (
        <p key={idx} className="alice-thinking-paragraph">
          {block.text}
        </p>
      );
    } else {
      return (
        <div key={idx} className="alice-reply-paragraph-wrapper">
          {renderMarkdown(block.text)}
        </div>
      );
    }
  });
};
