function overlaps(a, b) {
  // Check the edges of both rotated rectangles, rather than their much larger
  // axis-aligned bounds, so steep labels can still sit beside their lines.
  for (const polygon of [a, b]) {
    for (let index = 0; index < 2; index += 1) {
      const edge = {
        x: polygon[index + 1].x - polygon[index].x,
        y: polygon[index + 1].y - polygon[index].y,
      };
      const project = (point) => point.x * -edge.y + point.y * edge.x;
      const first = a.map(project);
      const second = b.map(project);
      if (Math.max(...first) <= Math.min(...second) || Math.max(...second) <= Math.min(...first))
        return false;
    }
  }
  return true;
}

function corners(x, y, width, height, cosine, sine) {
  return [
    [-1, -1],
    [1, -1],
    [1, 1],
    [-1, 1],
  ].map(([horizontal, vertical]) => ({
    x: x + (horizontal * width * cosine - vertical * height * sine) / 2,
    y: y + (horizontal * width * sine + vertical * height * cosine) / 2,
  }));
}

function intersectsLine(label, line) {
  const local = (point) => ({
    x: (point.x - label.x) * label.cosine + (point.y - label.y) * label.sine,
    y: -(point.x - label.x) * label.sine + (point.y - label.y) * label.cosine,
  });
  const start = local(line.start);
  const end = local(line.end);
  let first = 0;
  let last = 1;
  for (const [axis, size] of [
    ["x", label.width],
    ["y", label.height],
  ]) {
    const delta = end[axis] - start[axis];
    if (Math.abs(delta) < 1e-8) {
      if (Math.abs(start[axis]) > size / 2) return false;
      continue;
    }
    const a = (-size / 2 - start[axis]) / delta;
    const b = (size / 2 - start[axis]) / delta;
    first = Math.max(first, Math.min(a, b));
    last = Math.min(last, Math.max(a, b));
    if (first > last) return false;
  }
  return true;
}

export function placeTrendLabels(trends, points, plot) {
  const occupied = points.map((point) => corners(point.x, point.y, 28, 28, 1, 0));
  const labels = new Map();
  for (const trend of trends) {
    const dx = trend.end.x - trend.start.x;
    const dy = trend.end.y - trend.start.y;
    const length = Math.hypot(dx, dy);
    const direction = dx < 0 || (dx === 0 && dy < 0) ? -1 : 1;
    const cosine = length ? (dx / length) * direction : 1;
    const sine = length ? (dy / length) * direction : 0;
    const angle = (Math.atan2(sine, cosine) * 180) / Math.PI;
    let chosen;
    let fallback;
    for (const fontSize of [10, 9, 8]) {
      const width = (trend.label || trend.name).length * fontSize * 0.6 + 8;
      const height = fontSize + 2;
      const margin = width / 2 + 4;
      const distances = [];
      for (let distance = length - margin; distance >= margin; distance -= 8)
        distances.push(distance);
      distances.push(length / 2, length, 0, -margin, length + margin);
      // Short lines can end inside a cluster of points. Look further along
      // the same line before shrinking the label or accepting an overlap.
      const reach = Math.hypot(plot.right - plot.left, plot.bottom - plot.top);
      for (let extra = 8; extra <= reach; extra += 8) {
        distances.push(length + margin + extra, -margin - extra);
      }
      for (const distance of distances) {
        for (const offset of [-height / 2 - 1, height / 2 + 1, 0]) {
          const lineX = trend.start.x + (dx * distance) / (length || 1);
          const lineY = trend.start.y + (dy * distance) / (length || 1);
          const x = lineX - sine * offset;
          const y = lineY + cosine * offset;
          const polygon = corners(x, y, width, height, cosine, sine);
          if (
            !polygon.every(
              (point) =>
                point.x >= plot.left + 2 &&
                point.x <= plot.right - 2 &&
                point.y >= plot.top + 2 &&
                point.y <= plot.bottom - 2,
            )
          )
            continue;
          const collisions = occupied.filter((obstacle) => overlaps(polygon, obstacle)).length;
          const placement = { x, y, angle, polygon, fontSize, collisions };
          // Keep a crowded fallback directly on its own line. The text outline
          // preserves readability without moving the name across other lines.
          if (offset === 0 && (!fallback || collisions <= fallback.collisions))
            fallback = placement;
          const corridor = {
            x: (x + lineX) / 2,
            y: (y + lineY) / 2,
            width,
            height: Math.abs(offset) + height,
            cosine,
            sine,
          };
          if (
            !collisions &&
            !trends.some(
              (line) =>
                line !== trend &&
                // Coincident lines sit under this line, rather than between
                // it and the label, so they do not force text onto the dashes.
                (Math.abs(
                  (line.start.x - trend.start.x) * sine - (line.start.y - trend.start.y) * cosine,
                ) > 0.01 ||
                  Math.abs(
                    (line.end.x - trend.start.x) * sine - (line.end.y - trend.start.y) * cosine,
                  ) > 0.01) &&
                intersectsLine(corridor, line),
            )
          ) {
            chosen = placement;
            break;
          }
        }
        if (chosen) break;
      }
      if (chosen) break;
    }
    chosen ||= fallback || {
      x: (trend.start.x + trend.end.x) / 2,
      y: (trend.start.y + trend.end.y) / 2,
      angle,
      fontSize: 8,
      polygon: corners(
        (trend.start.x + trend.end.x) / 2,
        (trend.start.y + trend.end.y) / 2,
        trend.name.length * 4.8 + 8,
        10,
        cosine,
        sine,
      ),
    };
    occupied.push(chosen.polygon);
    const distance =
      length > 0 ? ((chosen.x - trend.start.x) * dx + (chosen.y - trend.start.y) * dy) / length : 0;
    const alongLine = (distance) => ({
      x: trend.start.x + (dx * distance) / (length || 1),
      y: trend.start.y + (dy * distance) / (length || 1),
    });
    labels.set(trend.name, {
      x: chosen.x,
      y: chosen.y,
      angle: chosen.angle,
      fontSize: chosen.fontSize,
      lineStart: alongLine(Math.min(0, distance)),
      lineEnd: alongLine(Math.max(length, distance)),
    });
  }
  return labels;
}

export function placeSingleScanLabels(
  points,
  trends,
  trendLabels,
  plot,
  { labelPoints = points, ensureAll = false } = {},
) {
  const occupied = points.map((point) => corners(point.x, point.y, 20, 20, 1, 0));
  for (const [name, label] of trendLabels) {
    const angle = (label.angle * Math.PI) / 180;
    occupied.push(
      corners(
        label.x,
        label.y,
        name.length * (label.fontSize || 10) * 0.6 + 8,
        14,
        Math.cos(angle),
        Math.sin(angle),
      ),
    );
  }
  const counts = new Map();
  for (const point of labelPoints) counts.set(point.name, (counts.get(point.name) || 0) + 1);
  const labels = new Map();
  for (const point of labelPoints) {
    if (counts.get(point.name) !== 1) continue;
    const width = point.name.length * 5.5 + 8;
    const height = 14;
    let chosen;
    let fallback;
    for (const gap of [14, 22, 30, 38, 46, 54, 62, 70, 78, 86, 102, 118, 134, 150, 180, 210]) {
      const candidates = [
        { x: point.x + width / 2 + gap, y: point.y },
        { x: point.x - width / 2 - gap, y: point.y },
        { x: point.x, y: point.y - height / 2 - gap },
        { x: point.x, y: point.y + height / 2 + gap },
        { x: point.x + width / 2 + gap, y: point.y - height / 2 - gap },
        { x: point.x + width / 2 + gap, y: point.y + height / 2 + gap },
        { x: point.x - width / 2 - gap, y: point.y - height / 2 - gap },
        { x: point.x - width / 2 - gap, y: point.y + height / 2 + gap },
      ];
      for (const candidate of candidates) {
        const polygon = corners(candidate.x, candidate.y, width, height, 1, 0);
        if (
          polygon.every(
            (corner) =>
              corner.x >= plot.left + 2 &&
              corner.x <= plot.right - 2 &&
              corner.y >= plot.top + 2 &&
              corner.y <= plot.bottom - 2,
          ) &&
          !occupied.some((obstacle) => overlaps(polygon, obstacle))
        ) {
          const placement = { ...candidate, polygon };
          fallback ||= placement;
          if (
            !trends.some((line) =>
              intersectsLine({ ...candidate, width, height, cosine: 1, sine: 0 }, line),
            )
          ) {
            chosen = placement;
            break;
          }
        }
      }
      if (chosen) break;
    }
    chosen ||= fallback;
    if (!chosen && ensureAll) {
      const x = Math.max(plot.left + width / 2 + 2, Math.min(plot.right - width / 2 - 2, point.x));
      const y = Math.max(
        plot.top + height / 2 + 2,
        Math.min(plot.bottom - height / 2 - 2, point.y + 20),
      );
      chosen = { x, y, polygon: corners(x, y, width, height, 1, 0) };
    }
    if (chosen) {
      occupied.push(chosen.polygon);
      labels.set(point.name, {
        x: chosen.x,
        y: chosen.y,
        pointX: point.x,
        pointY: point.y,
        edgeX: Math.max(chosen.x - width / 2, Math.min(point.x, chosen.x + width / 2)),
        edgeY: Math.max(chosen.y - height / 2, Math.min(point.y, chosen.y + height / 2)),
      });
    }
  }
  return labels;
}
