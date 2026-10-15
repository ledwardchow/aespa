import { expect, test } from "vitest";

import { parseDuration } from "./format.js";

test("reads reset times copied from ChatGPT", () => {
  expect(parseDuration("3h 12m")).toBe((3 * 60 + 12) * 60_000);
  expect(parseDuration("2d 4h")).toBe((2 * 24 + 4) * 3_600_000);
  expect(parseDuration("45 min")).toBe(45 * 60_000);
  expect(parseDuration("")).toBeNull();
  expect(parseDuration("soon")).toBeNull();
  expect(parseDuration("3h later")).toBeNull();
});
