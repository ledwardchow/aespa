import { describe, expect, it } from "vitest";

import { forceAvoidLinkCrossings, linksCross } from "./sitemapLinkCrossingForce.js";

const point = (id, x, y) => ({ id, x, y, vx: 0, vy: 0 });

describe("site map link crossing force", () => {
  it("recognises interior crossings but ignores shared endpoints", () => {
    const topLeft = point(1, 0, 0);
    const bottomRight = point(2, 100, 100);
    const bottomLeft = point(3, 0, 100);
    const topRight = point(4, 100, 0);
    const first = { source: topLeft, target: bottomRight };
    expect(linksCross(first, { source: bottomLeft, target: topRight })).toBe(true);
    expect(linksCross(first, { source: topLeft, target: topRight })).toBe(false);
  });

  it("pushes crossing page links apart", () => {
    const nodes = [point(1, 0, 0), point(2, 100, 100), point(3, 0, 100), point(4, 100, 0)];
    const links = [
      { source: nodes[0], target: nodes[1] },
      { source: nodes[2], target: nodes[3] },
    ];
    forceAvoidLinkCrossings(links)(1);
    expect(nodes.some((node) => node.vx !== 0 || node.vy !== 0)).toBe(true);
  });
});
