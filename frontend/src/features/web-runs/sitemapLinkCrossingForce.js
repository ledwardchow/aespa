const nodeId = (node) => String(node?.id ?? "");

function sharesEndpoint(first, second) {
  return (
    first.source === second.source ||
    first.source === second.target ||
    first.target === second.source ||
    first.target === second.target
  );
}

export function linksCross(first, second) {
  if (sharesEndpoint(first, second)) return false;
  const ax = first.target.x - first.source.x;
  const ay = first.target.y - first.source.y;
  const bx = second.target.x - second.source.x;
  const by = second.target.y - second.source.y;
  const denominator = ax * by - ay * bx;
  if (Math.abs(denominator) < 0.001) return false;
  const dx = second.source.x - first.source.x;
  const dy = second.source.y - first.source.y;
  const firstPosition = (dx * by - dy * bx) / denominator;
  const secondPosition = (dx * ay - dy * ax) / denominator;
  const margin = 0.04;
  return (
    firstPosition > margin &&
    firstPosition < 1 - margin &&
    secondPosition > margin &&
    secondPosition < 1 - margin
  );
}

export function forceAvoidLinkCrossings(links, strength = 5) {
  return (alpha) => {
    const push = Math.min(2.5, strength * alpha);
    for (let firstIndex = 0; firstIndex < links.length; firstIndex += 1) {
      const first = links[firstIndex];
      for (let secondIndex = firstIndex + 1; secondIndex < links.length; secondIndex += 1) {
        const second = links[secondIndex];
        if (!linksCross(first, second)) continue;
        const edgeX = first.target.x - first.source.x;
        const edgeY = first.target.y - first.source.y;
        const edgeLength = Math.hypot(edgeX, edgeY) || 1;
        const normalX = -edgeY / edgeLength;
        const normalY = edgeX / edgeLength;
        const firstMiddleX = (first.source.x + first.target.x) / 2;
        const firstMiddleY = (first.source.y + first.target.y) / 2;
        const secondMiddleX = (second.source.x + second.target.x) / 2;
        const secondMiddleY = (second.source.y + second.target.y) / 2;
        const side =
          Math.sign(
            (secondMiddleX - firstMiddleX) * normalX + (secondMiddleY - firstMiddleY) * normalY,
          ) ||
          (nodeId(second.source).localeCompare(nodeId(first.source), undefined, {
            numeric: true,
          }) >= 0
            ? 1
            : -1);
        for (const node of [first.source, first.target]) {
          node.vx -= normalX * push * side;
          node.vy -= normalY * push * side;
        }
        for (const node of [second.source, second.target]) {
          node.vx += normalX * push * side;
          node.vy += normalY * push * side;
        }
      }
    }
  };
}
