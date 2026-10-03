export function linearFit(points) {
  if (points.length < 2) return null;
  const meanX = points.reduce((sum, point) => sum + point.x, 0) / points.length;
  const meanY = points.reduce((sum, point) => sum + point.y, 0) / points.length;
  const variance = points.reduce((sum, point) => sum + (point.x - meanX) ** 2, 0);
  if (variance === 0) return null;
  const slope =
    points.reduce((sum, point) => sum + (point.x - meanX) * (point.y - meanY), 0) / variance;
  const predict = (value) => meanY + slope * (value - meanX);
  const first = Math.min(...points.map((point) => point.x));
  const last = Math.max(...points.map((point) => point.x));
  return { start: { x: first, y: predict(first) }, end: { x: last, y: predict(last) } };
}
