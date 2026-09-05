import { expect, test } from "vitest";
import { parseRoute } from "./parseRoute.ts";

test.each([
  ["#/", { name: "list" }],
  ["#/sites/new", { name: "site-new" }],
  ["#/sites/7/edit", { name: "site-edit", id: 7 }],
  ["#/sites/7/runs/new", { name: "run-new", siteId: 7 }],
  ["#/sites/7", { name: "site-detail", id: 7 }],
  ["#/apis", { name: "api-list" }],
  ["#/apis/new", { name: "api-new" }],
  ["#/apis/7/edit", { name: "api-edit", id: 7 }],
  ["#/apis/7/files", { name: "api-files", id: 7 }],
  ["#/apis/7/runs/new", { name: "api-run-new", id: 7 }],
  ["#/apis/7/endpoints", { name: "api-detail", id: 7, tab: "endpoints" }],
  [
    "#/api-runs/7/findings?finding=F-12.",
    { name: "api-run-detail", id: 7, tab: "findings", findingRef: "F-12" },
  ],
  ["#/runs/7/alice-popout", { name: "alice-popout", id: 7 }],
  [
    "#/runs/7/findings?finding=F-12&lead=L-3",
    { name: "run-detail", id: 7, tab: "findings", findingRef: "F-12", leadRef: "L-3" },
  ],
  ["#/sast-runs/7/progress", { name: "sast-run-detail", id: 7, tab: "progress" }],
  ["#/sast-runs/new", { name: "sast-run-new" }],
  ["#/applications/3/campaigns/new", { name: "campaign-new", id: 3 }],
  [
    "#/applications/3/campaigns/7/findings?finding=F-9",
    { name: "campaign-detail", id: 3, campaignId: 7, tab: "findings", findingRef: "F-9" },
  ],
  ["#/stats/usage", { name: "stats" }],
  ["#/settings", { name: "settings" }],
  ["#/scan-policy", { name: "scan-policy" }],
  ["#/external-integrations", { name: "external-integrations" }],
  ["#/debug", { name: "debug" }],
  ["#/reporting-debug", { name: "reporting-debug" }],
  ["#/does-not-exist", { name: "not-found" }],
])("%s resolves without changing existing identifiers", (hash, expected) => {
  expect(parseRoute(hash)).toMatchObject(expected);
});

test("run links round-trip run kind and encoded references", async () => {
  const { runHref } = await import("./links.ts");
  expect(
    parseRoute(runHref({ runKind: "api", runId: 7 }, "findings", { finding: "F-7 a&b" })),
  ).toMatchObject({ name: "api-run-detail", id: 7, findingRef: "F-7 a&b" });
  expect(
    parseRoute(runHref({ runKind: "sast", runId: 7 }, "candidates", { lead: "L-7" })),
  ).toMatchObject({ name: "sast-run-detail", id: 7, leadRef: "L-7" });
});
