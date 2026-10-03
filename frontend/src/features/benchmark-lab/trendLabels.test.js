import { expect, test } from "vitest";
import { placeSingleScanLabels, placeTrendLabels } from "./trendLabels.js";

const plot = { left: 0, right: 300, top: 0, bottom: 160 };

function distanceToLine(label, line) {
  const dx = line.end.x - line.start.x;
  const dy = line.end.y - line.start.y;
  return (
    Math.abs(dx * (label.y - line.start.y) - dy * (label.x - line.start.x)) / Math.hypot(dx, dy)
  );
}

test("keeps overlapping trend labels near their own line and follows its angle", () => {
  const lines = ["First model", "Second model"].map((name) => ({
    name,
    start: { x: 20, y: 140 },
    end: { x: 280, y: 20 },
  }));
  const labels = placeTrendLabels(lines, [lines[0].end], plot);
  expect(labels.size).toBe(2);
  for (const line of lines) {
    const label = labels.get(line.name);
    expect(distanceToLine(label, line)).toBeLessThanOrEqual(7.1);
    expect(label.angle).toBeCloseTo((Math.atan2(-120, 260) * 180) / Math.PI);
  }
  expect(labels.get("First model")).not.toEqual(labels.get("Second model"));
});

test("keeps text readable on reversed steep lines", () => {
  const line = { name: "Model", start: { x: 160, y: 20 }, end: { x: 120, y: 140 } };
  const label = placeTrendLabels([line], [], plot).get(line.name);
  expect(label).toBeDefined();
  expect(label.angle).toBeCloseTo((Math.atan2(-120, 40) * 180) / Math.PI);
  expect(distanceToLine(label, line)).toBeLessThanOrEqual(7.1);
});

test("keeps the label on its line when the plot cannot fit the name", () => {
  const line = { name: "Long model name", start: { x: 0, y: 0 }, end: { x: 20, y: 20 } };
  const label = placeTrendLabels([line], [], { left: 0, right: 20, top: 0, bottom: 20 }).get(
    line.name,
  );
  expect(distanceToLine(label, line)).toBeLessThanOrEqual(7.1);
});

test("labels only models with one plotted scan and stays inside the plot", () => {
  const points = [
    { name: "Single", x: 280, y: 80 },
    { name: "Repeated", x: 50, y: 30 },
    { name: "Repeated", x: 100, y: 50 },
  ];
  const labels = placeSingleScanLabels(points, [], new Map(), plot);
  expect(labels.size).toBe(1);
  const label = labels.get("Single");
  expect(label.x).toBeLessThan(280);
  expect(label.y).toBe(80);
  expect(label.x - ("Single".length * 5.5 + 8) / 2).toBeGreaterThan(plot.left);
});

test("labels every line in a crowded graph, including short and flat lines", () => {
  const lines = Array.from({ length: 25 }, (_, index) => ({
    name: `Model with a long name ${index}`,
    start: { x: 140, y: 80 },
    end: { x: 141, y: 80 },
  }));
  const labels = placeTrendLabels(lines, [lines[0].start], plot);
  expect(labels.size).toBe(lines.length);
  for (const line of lines)
    expect(distanceToLine(labels.get(line.name), line)).toBeLessThanOrEqual(7.1);
});

test("moves a short MiniMax label past nearby points and extends its line to the label", () => {
  const line = { name: "minimax-m3", start: { x: 20, y: 80 }, end: { x: 45, y: 80 } };
  const points = [20, 30, 45, 65, 80, 100].map((x) => ({ x, y: 80 }));
  const label = placeTrendLabels([line], points, plot).get(line.name);
  const halfWidth = (line.name.length * label.fontSize * 0.6 + 8) / 2;
  expect(label.x - halfWidth).toBeGreaterThanOrEqual(114);
  expect(label.fontSize).toBe(10);
  expect(distanceToLine(label, line)).toBeLessThanOrEqual(7.1);
  expect(label.lineEnd.x).toBeGreaterThan(line.end.x);
  expect(label.lineEnd.x).toBeCloseTo(label.x);
  expect(label.lineEnd.y).toBe(80);
});

test("does not put another trendline between a label and its own line", () => {
  const line = { name: "Purple model", start: { x: 80, y: 150 }, end: { x: 120, y: 10 } };
  const other = { name: "Pink model", start: { x: 110, y: 100 }, end: { x: 280, y: 120 } };
  const label = placeTrendLabels([line, other], [], plot).get(line.name);
  expect(distanceToLine(label, line)).toBeLessThanOrEqual(7.1);
  expect(label.angle).toBeCloseTo((Math.atan2(-140, 40) * 180) / Math.PI);
});

test("labels a selected optimal point even when its model has multiple scans", () => {
  const points = [
    { name: "Model", x: 100, y: 80 },
    { name: "Model", x: 200, y: 40 },
  ];
  const labels = placeSingleScanLabels(points, [], new Map(), plot, {
    labelPoints: [points[1]],
    ensureAll: true,
  });
  expect(labels.get("Model").pointX).toBe(200);
  expect(labels.get("Model").pointY).toBe(40);
});
