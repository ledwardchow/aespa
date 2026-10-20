import { describe, expect, it } from "vitest";

import {
  extractUrlExtension,
  filterSitemapGraph,
  isApiGraphNode,
  parseExcludedExtensions,
} from "./urlExtensions.js";

describe("URL extension filters", () => {
  it("normalizes comma-separated extensions", () => {
    expect([...parseExcludedExtensions("svg, .PNG,  .woff2 ")]).toEqual([".svg", ".png", ".woff2"]);
  });

  it("extracts an extension without including query strings or fragments", () => {
    expect(extractUrlExtension("https://example.test/assets/logo.SVG?v=2#mark")).toBe(".svg");
  });

  it("does not treat extensionless and hidden-file paths as extensions", () => {
    expect(extractUrlExtension("https://example.test/account/profile")).toBe("");
    expect(extractUrlExtension("https://example.test/.well-known")).toBe("");
  });

  it("removes excluded nodes and links while leaving the source graph intact", () => {
    const graph = {
      nodes: [
        { id: 1, url: "https://example.test/" },
        { id: 2, url: "https://example.test/logo.svg" },
        { id: 3, url: "https://example.test/account" },
      ],
      links: [
        { source: 1, target: 2 },
        { source: { id: 1 }, target: { id: 3 } },
      ],
    };

    const filtered = filterSitemapGraph(graph, new Set([".svg"]));

    expect(filtered.nodes.map((node) => node.id)).toEqual([1, 3]);
    expect(filtered.links).toEqual([{ source: { id: 1 }, target: { id: 3 } }]);
    expect(graph.nodes).toHaveLength(3);
  });

  it("identifies API nodes from crawler context or API request titles", () => {
    expect(isApiGraphNode({ context: "[API endpoint] Observed GET request" })).toBe(true);
    expect(isApiGraphNode({ title: "API POST 200 /orders" })).toBe(true);
    expect(isApiGraphNode({ title: "Account", context: "Interactive account page" })).toBe(false);
  });

  it("optionally hides API nodes while keeping them visible by default", () => {
    const graph = {
      nodes: [
        { id: 1, url: "https://example.test/" },
        {
          id: 2,
          url: "https://example.test/api/account",
          context: "[API endpoint] Observed GET request",
        },
      ],
      links: [{ source: 1, target: 2 }],
    };

    expect(filterSitemapGraph(graph, new Set()).nodes).toHaveLength(2);
    const filtered = filterSitemapGraph(graph, new Set(), true);
    expect(filtered.nodes.map((node) => node.id)).toEqual([1]);
    expect(filtered.links).toEqual([]);
  });
});
