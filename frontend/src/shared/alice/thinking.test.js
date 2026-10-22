import { expect, test } from "vitest";
import { parseAliceThinking } from "./thinking.js";

test("SAST tool activity appears as separate reasoning rows", () => {
  const blocks = parseAliceThinking(
    "Reading saved source snapshot…\nUsed tool: sast_context\nUsed tool: read_file\n",
  );
  expect(blocks).toEqual([
    { type: "thought", text: "Reading saved source snapshot…" },
    {
      type: "status",
      status: "routing",
      text: "Used tool: sast_context",
      stepKind: "tool_call",
      toolName: "sast_context",
      toolOrdinal: 0,
    },
    {
      type: "status",
      status: "routing",
      text: "Used tool: read_file",
      stepKind: "tool_call",
      toolName: "read_file",
      toolOrdinal: 1,
    },
  ]);
});

test("saved SAST chats with numbered tool lines use the new labels", () => {
  const blocks = parseAliceThinking("[Step 1] sast_context\n[Step 2] read_file\n");
  expect(blocks.map((block) => block.text)).toEqual([
    "Used tool: sast_context",
    "Used tool: read_file",
  ]);
});
