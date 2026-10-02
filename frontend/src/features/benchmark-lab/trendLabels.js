function intersectsLine(box, line) {
  let first = 0;
  let last = 1;
  for (const axis of ["x", "y"]) {
    const delta = line.end[axis] - line.start[axis];
    if (delta === 0) {
      if (
        line.start[axis] < box[axis] ||
        line.start[axis] > box[axis] + box[axis === "x" ? "width" : "height"]
      )
        return false;
      continue;
    }
    const a = (box[axis] - line.start[axis]) / delta;
    const b = (box[axis] + box[axis === "x" ? "width" : "height"] - line.start[axis]) / delta;
    first = Math.max(first, Math.min(a, b));
    last = Math.min(last, Math.max(a, b));
    if (first > last) return false;
  }
  return true;
}

function overlaps(a, b) {
  return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
}

export function placeTrendLabels(trends, points, plot) {
  const occupied = points.map((point) => ({
    x: point.x - 10,
    y: point.y - 10,
    width: 20,
    height: 20,
  }));
  const labels = new Map();
  for (const trend of trends) {
    // Leave room for the text stroke and use a generous estimate of glyph width.
    const width = (trend.label || trend.name).length * 7 + 8;
    const height = 20;
    const candidates = [];
    for (let top = plot.top + 4; top + height <= plot.bottom - 4; top += 12) {
      for (let left = plot.left + 4; left + width <= plot.right - 4; left += 12) {
        candidates.push({ x: left, y: top, width, height });
      }
    }
    candidates.sort(
      (a, b) =>
        Math.hypot(a.x + width - trend.end.x, a.y + height / 2 - trend.end.y) -
        Math.hypot(b.x + width - trend.end.x, b.y + height / 2 - trend.end.y),
    );
    const box = candidates.find(
      (candidate) =>
        !occupied.some((obstacle) => overlaps(candidate, obstacle)) &&
        !trends.some((line) => intersectsLine(candidate, line)),
    );
    if (box) {
      occupied.push(box);
      labels.set(trend.name, { x: box.x + 4, y: box.y + 14 });
    }
    // If the plot is too crowded, the model name is still available in the legend.
  }
  return labels;
}
