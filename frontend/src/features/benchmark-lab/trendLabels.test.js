import { expect, test } from "vitest";
import { placeTrendLabels } from "./trendLabels.js";

const plot = { left: 0, right: 300, top: 0, bottom: 160 };

test("separates labels for overlapping trendlines and leaves room for scan points", () => {
  const lines = ["First model", "Second model"].map((name) => ({
    name,
    start: { x: 20, y: 140 },
    end: { x: 280, y: 20 },
  }));
  const labels = placeTrendLabels(lines, [lines[0].end], plot);
  expect(labels.size).toBe(2);
  const boxes = lines.map(({ name }) => {
    const label = labels.get(name);
    return {
      left: label.x - 4,
      top: label.y - 14,
      right: label.x - 4 + name.length * 7 + 8,
      bottom: label.y + 6,
    };
  });
  for (const box of boxes) {
    expect(box.left).toBeGreaterThanOrEqual(plot.left);
    expect(box.right).toBeLessThanOrEqual(plot.right);
    expect(box.top).toBeGreaterThanOrEqual(plot.top);
    expect(box.bottom).toBeLessThanOrEqual(plot.bottom);
    expect(box.right <= 270 || box.bottom <= 10 || box.top >= 30).toBe(true);
  }
  expect(
    boxes[0].right <= boxes[1].left ||
      boxes[1].right <= boxes[0].left ||
      boxes[0].bottom <= boxes[1].top ||
      boxes[1].bottom <= boxes[0].top,
  ).toBe(true);
});

test("omits labels when the plot has no free space", () => {
  const lines = [{ name: "Long model name", start: { x: 0, y: 0 }, end: { x: 20, y: 20 } }];
  expect(placeTrendLabels(lines, [], { left: 0, right: 20, top: 0, bottom: 20 }).size).toBe(0);
});
