import { describe, expect, it } from "vitest";

import { buildSitemapDisplayGraph } from "./sitemapGraph.js";

const graph = {
  nodes: [
    { id: 1, url: "https://shop.test/orders", title: "Orders", depth: 1 },
    { id: 2, url: "https://shop.test/dashboard", title: "Dashboard", depth: 1 },
    {
      id: 3,
      url: "https://shop.test/api/orders?id=123&view=full",
      title: "API GET 200 /api/orders",
      context: "[API endpoint] Observed GET request",
      depth: 2,
    },
    {
      id: 4,
      url: "https://shop.test/api/orders?id=456",
      title: "API GET 200 /api/orders",
      context: "[API endpoint] Observed GET request",
      depth: 2,
    },
    {
      id: 5,
      url: "https://shop.test/api/orders/42",
      title: "API DELETE 204 /api/orders/42",
      context: "[API endpoint] Observed DELETE request",
      depth: 2,
    },
  ],
  links: [
    { source: 1, target: 3 },
    { source: 2, target: 3 },
    { source: 1, target: 4 },
    { source: 1, target: 5 },
  ],
};

describe("grouped sitemap API display", () => {
  it("groups API URL variants by method and normalized route", () => {
    const result = buildSitemapDisplayGraph(graph, new Set(), "grouped");
    const groups = result.nodes.filter((node) => node.isApiGroup);

    expect(groups).toHaveLength(2);
    expect(groups.find((node) => node.title === "GET /api/orders")).toMatchObject({
      variantCount: 2,
      callers: [expect.objectContaining({ id: 2 }), expect.objectContaining({ id: 1 })],
    });
    expect(groups.find((node) => node.title === "DELETE /api/orders/{id}")).toMatchObject({
      variantCount: 1,
      parameters: [{ name: "id", location: "Path", values: ["42"] }],
    });
    expect(result.links).toHaveLength(3);
    expect(
      result.links.find((link) => link.source === 1 && String(link.target).includes("GET")),
    ).toMatchObject({ count: 2 });
  });

  it("keeps individual and hidden modes available", () => {
    expect(buildSitemapDisplayGraph(graph, new Set(), "individual").nodes).toHaveLength(5);
    expect(buildSitemapDisplayGraph(graph, new Set(), "hidden").nodes).toHaveLength(2);
  });
});
