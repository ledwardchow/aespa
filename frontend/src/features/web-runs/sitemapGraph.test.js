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

  it("groups page IDs and query values while keeping interactive states separate", () => {
    const pageGraph = {
      nodes: [
        { id: 1, url: "https://shop.test/", depth: 0 },
        { id: 2, url: "https://shop.test/orders/123?tab=summary", depth: 1 },
        { id: 3, url: "https://shop.test/orders/456?tab=history", depth: 1 },
        {
          id: 4,
          url: "https://shop.test/orders/123?tab=summary",
          state_kind: "interactive",
          state_label: "Edit order dialog",
          depth: 2,
        },
      ],
      links: [
        { source: 1, target: 2 },
        { source: 1, target: 3 },
        { source: 2, target: 4 },
        { source: 3, target: 4 },
      ],
    };

    const grouped = buildSitemapDisplayGraph(pageGraph, new Set(), "hidden", "grouped");
    const route = grouped.nodes.find((node) => node.isPageGroup);

    expect(grouped.nodes).toHaveLength(3);
    expect(route).toMatchObject({
      title: "/orders/{id}",
      variantCount: 2,
      parameters: [
        { name: "id", location: "Path", values: ["123", "456"] },
        { name: "tab", location: "Query", values: ["history", "summary"] },
      ],
    });
    expect(grouped.links).toEqual([
      expect.objectContaining({ source: 1, target: route.id, count: 2 }),
      expect.objectContaining({ source: route.id, target: 4, count: 2 }),
    ]);
    expect(
      buildSitemapDisplayGraph(pageGraph, new Set(), "hidden", "individual").nodes,
    ).toHaveLength(4);
  });

  it("groups unattributed dynamic routes under a discovery node", () => {
    const dynamicGraph = {
      nodes: [
        { id: 1, url: "https://shop.test/", title: "Home", depth: 0 },
        {
          id: 2,
          url: "https://shop.test/api/direct",
          title: "Dynamic API route",
          context: "Discovered during Dynamic Scan.",
          state_kind: "api",
          depth: 0,
        },
      ],
      links: [],
    };

    const result = buildSitemapDisplayGraph(dynamicGraph, new Set(), "grouped");
    const hub = result.nodes.find((node) => node.isDiscoveryGroup);
    const endpoint = result.nodes.find((node) => node.isApiGroup);

    expect(hub).toMatchObject({ discoveryCount: 1 });
    expect(result.links).toContainEqual(
      expect.objectContaining({
        source: hub.id,
        target: endpoint.id,
        action_kind: "dynamic_discovery",
      }),
    );
    expect(buildSitemapDisplayGraph(dynamicGraph, new Set(), "hidden").nodes).toEqual([
      expect.objectContaining({ id: 1 }),
    ]);
  });

  it("does not add a discovery node when a dynamic route has a recovered source", () => {
    const dynamicGraph = {
      nodes: [
        { id: 1, url: "https://shop.test/account", title: "Account", depth: 1 },
        {
          id: 2,
          url: "https://shop.test/api/preferences",
          title: "Dynamic API route",
          context: "Discovered during Dynamic Scan.",
          state_kind: "api",
          depth: 0,
        },
      ],
      links: [{ source: 1, target: 2, action_kind: "dynamic_request" }],
    };

    const result = buildSitemapDisplayGraph(dynamicGraph, new Set(), "grouped");

    expect(result.nodes.some((node) => node.isDiscoveryGroup)).toBe(false);
    expect(result.links).toHaveLength(1);
  });
});
