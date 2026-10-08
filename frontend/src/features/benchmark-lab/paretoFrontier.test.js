import { expect, test } from "vitest";
import { paretoFrontier } from "./paretoFrontier.js";

test("keeps only scans with the best findings for their cost, sorted by cost", () => {
  const points = [
    { x: 0.4, y: 20 },
    { x: 0.3, y: 12 },
    { x: 0.1, y: 10 },
    { x: 0.2, y: 15 },
    { x: 0.5, y: 20 },
  ];
  expect(paretoFrontier(points)).toEqual([points[2], points[3], points[0]]);
  expect(points[0].x).toBe(0.4);
});

test("keeps tied models, drops worse scans at the same cost, and includes free scans", () => {
  const points = [
    { x: 0, y: 5, model: "Free" },
    { x: 1, y: 8, model: "A" },
    { x: 1, y: 8, model: "B" },
    { x: 1, y: 6 },
    { x: 2, y: 8 },
  ];
  expect(paretoFrontier(points)).toEqual(points.slice(0, 3));
});

test("handles empty, single, and unavailable cost data", () => {
  expect(paretoFrontier([])).toEqual([]);
  expect(
    paretoFrontier([
      { x: null, y: 10 },
      { x: NaN, y: 8 },
      { x: -1, y: 20 },
      { x: 0.2, y: 5 },
    ]),
  ).toEqual([{ x: 0.2, y: 5 }]);
});
