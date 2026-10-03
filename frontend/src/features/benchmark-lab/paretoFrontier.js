// Lower cost and more findings are better. Keep all scans tied at an optimal
// point so every model with the same cost and finding count is represented.
export function paretoFrontier(points) {
  const sorted = points
    .filter((point) => Number.isFinite(point.x) && point.x >= 0 && Number.isFinite(point.y))
    .toSorted((a, b) => a.x - b.x || b.y - a.y);
  const frontier = [];
  let bestCount = -Infinity;
  let bestCost;
  for (const point of sorted) {
    if (point.y > bestCount) {
      bestCount = point.y;
      bestCost = point.x;
      frontier.push(point);
    } else if (point.y === bestCount && point.x === bestCost) {
      frontier.push(point);
    }
  }
  return frontier;
}
