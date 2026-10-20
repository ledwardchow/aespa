import { expect, it } from "vitest";
import { markSiteEntries } from "./sitemapRootLayout.js";

it("marks configured entries without pinning or positioning nodes", () => {
  const nodes = [
    { id: 1, url: "https://example.test/home" },
    { id: 2, url: "https://example.test/login" },
    { id: 3, url: "https://example.test/other" },
  ];
  markSiteEntries(nodes, { base_url: "https://example.test/home/", login_url: "/login" });
  expect(nodes[0].entryRole).toBe("Landing page");
  expect(nodes[1].entryRole).toBe("Login page");
  expect(nodes[2].isSiteEntry).toBe(false);
  expect(nodes.every((node) => node.fx === undefined && node.x === undefined)).toBe(true);
});
