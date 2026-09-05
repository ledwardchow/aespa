import { normalizeAliceText } from "./text.js";

export const parseAliceThinking = (text) => {
  text = normalizeAliceText(text);
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
          text: codeContent.join("\n"),
        });
        inCodeBlock = false;
        codeContent = [];
      } else {
        // Start of code block
        // Flush existing paragraph first
        if (currentParagraph.length > 0) {
          blocks.push({
            type: "thought",
            text: currentParagraph.join("\n"),
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
        } catch {
          const nameMatch = rawText.match(/"name"\s*:\s*"([^"]+)"/);
          if (nameMatch) toolName = nameMatch[1];
        }
        blocks.push({
          type: "tool_call",
          tool: toolName,
          text: toolArgsText,
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
          text: toolResponseContent.join("\n"),
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
          text: currentParagraph.join("\n"),
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
        } catch {
          const nameMatch = content.match(/"name"\s*:\s*"([^"]+)"/);
          if (nameMatch) toolName = nameMatch[1];
        }
        blocks.push({
          type: "tool_call",
          tool: toolName,
          text: toolArgsText,
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
          text: currentParagraph.join("\n"),
        });
        currentParagraph = [];
      }
      if (trimmed.includes("</tool_response>")) {
        const startIndex = line.indexOf("<tool_response>");
        const endIndex = line.indexOf("</tool_response>");
        const content = line.substring(startIndex + 15, endIndex);
        blocks.push({
          type: "tool_response",
          text: content,
        });
      } else {
        inToolResponse = true;
        const parts = line.split("<tool_response>");
        if (parts[1]) toolResponseContent.push(parts[1]);
      }
      continue;
    }

    // Step/Status logs
    const normalizedStatus = trimmed.replace(
      /^\[A\.L\.I\.C\.E\. Initiali[sz]ing\]/,
      "[A.L.I.C.E. Initialising]",
    );
    if (normalizedStatus !== trimmed || trimmed.includes("Mapped target sitemap")) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n"),
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "status",
        status: "initializing",
        text: normalizedStatus,
      });
      continue;
    }
    if (
      trimmed.startsWith("Evaluating prompt scope compliance:") ||
      trimmed.includes("In-Scope verified")
    ) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n"),
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "status",
        status: "scope_check",
        text: trimmed,
      });
      continue;
    }
    if (
      trimmed.startsWith("Scope compliance verified") ||
      trimmed.startsWith("Scope compliance check passed") ||
      trimmed.includes("Starting agentic assessment loop")
    ) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n"),
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "status",
        status: "scope_check",
        text: trimmed,
      });
      continue;
    }
    if (
      trimmed.startsWith("Routing directives to the LLM agent model:") ||
      trimmed.includes("Routing directives")
    ) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n"),
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "status",
        status: "routing",
        text: trimmed,
      });
      continue;
    }

    // [Step N] Calling LLM...
    const stepLLMMatch = trimmed.match(/^\[Step (\d+)\] Calling LLM/);
    if (stepLLMMatch) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n"),
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "status",
        status: "routing",
        text: trimmed,
        stepNum: parseInt(stepLLMMatch[1]),
        stepKind: "llm_call",
      });
      continue;
    }

    // [Step N] Executing tool: name  (must come before generic toolCallRegex)
    const stepExecMatch = trimmed.match(/^\[Step (\d+)\] Executing tool:\s*(\S+)/);
    if (stepExecMatch) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n"),
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
        toolIdx,
      });
      continue;
    }

    // [Step N] Tool result (N chars)
    const stepResultMatch = trimmed.match(/^\[Step (\d+)\] Tool result/);
    if (stepResultMatch) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n"),
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
        toolIdx,
      });
      continue;
    }
    if (trimmed.startsWith("[A.L.I.C.E. Boundary Violation Alert]")) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n"),
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "alert",
        level: "danger",
        title: "Boundary Violation",
        text: trimmed,
      });
      continue;
    }
    if (trimmed.startsWith("[ALICE Error]")) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n"),
        });
        currentParagraph = [];
      }
      blocks.push({
        type: "alert",
        level: "error",
        title: "Error",
        text: trimmed,
      });
      continue;
    }

    // Generic tool execution detection (non-step-prefixed lines)
    const toolCallRegex =
      /(?:Calling|Invoking|Executing)\s+tool:?\s+([a-zA-Z0-9_]+)|(?:tool_call|toolCall):\s*([a-zA-Z0-9_]+)/i;
    const match = trimmed.match(toolCallRegex);
    if (match) {
      if (currentParagraph.length > 0) {
        blocks.push({
          type: "thought",
          text: currentParagraph.join("\n"),
        });
        currentParagraph = [];
      }
      const toolName = match[1] || match[2];
      blocks.push({
        type: "tool_call",
        tool: toolName,
        text: trimmed,
      });
      continue;
    }

    // Standard text line
    if (trimmed !== "") {
      currentParagraph.push(line);
    } else if (currentParagraph.length > 0) {
      blocks.push({
        type: "thought",
        text: currentParagraph.join("\n"),
      });
      currentParagraph = [];
    }
  }

  // Flush remaining paragraphs or code blocks
  if (inCodeBlock && codeContent.length > 0) {
    blocks.push({
      type: "code",
      lang: codeLang,
      text: codeContent.join("\n"),
    });
  } else if (inToolCall && toolCallContent.length > 0) {
    blocks.push({
      type: "tool_call",
      tool: "unknown",
      text: toolCallContent.join("\n"),
    });
  } else if (inToolResponse && toolResponseContent.length > 0) {
    blocks.push({
      type: "tool_response",
      text: toolResponseContent.join("\n"),
    });
  } else if (currentParagraph.length > 0) {
    blocks.push({
      type: "thought",
      text: currentParagraph.join("\n"),
    });
  }
  return blocks;
};
