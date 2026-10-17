import { beforeEach, expect, test } from "vitest";
import {
  acknowledgeWorkflowIds,
  readAcknowledgedWorkflowIds,
  visibleWorkflowInputNotes,
} from "./workflowAcknowledgement.js";

beforeEach(() => localStorage.clear());

test("keeps acknowledged attempts hidden after reload and leaves new attempts visible", () => {
  const acknowledged = acknowledgeWorkflowIds(7, readAcknowledgedWorkflowIds(7), [11]);
  expect(acknowledged.has(11)).toBe(true);
  const notes = [
    { id: 11, needs_input: true, status: "needs_input" },
    { id: 12, retry_of: 11, needs_input: true, status: "needs_input" },
  ];
  expect(visibleWorkflowInputNotes(notes, {}, readAcknowledgedWorkflowIds(7))).toEqual([notes[1]]);
  expect(readAcknowledgedWorkflowIds(8).has(11)).toBe(false);
});
