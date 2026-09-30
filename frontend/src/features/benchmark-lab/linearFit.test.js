import { expect, test } from "vitest";
import { linearFit } from "./linearFit.js";

test("fits all points instead of connecting the endpoints", () => {
  expect(
    linearFit([
      { x: 1, y: 0 },
      { x: 2, y: 4 },
      { x: 3, y: 2 },
    ]),
  ).toEqual({ start: { x: 1, y: 1 }, end: { x: 3, y: 3 } });
});
test("handles timestamps with a centered fit", () => {
  const start = Date.UTC(2026, 8, 30);
  expect(
    linearFit([
      { x: start, y: 2 },
      { x: start + 3600000, y: 4 },
    ]),
  ).toEqual({ start: { x: start, y: 2 }, end: { x: start + 3600000, y: 4 } });
});
test("requires two distinct horizontal values", () => {
  expect(linearFit([{ x: 1, y: 2 }])).toBeNull();
  expect(
    linearFit([
      { x: 1, y: 2 },
      { x: 1, y: 4 },
    ]),
  ).toBeNull();
});
