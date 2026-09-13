export type Route = {
  name: string;
  id?: number;
  siteId?: number;
  campaignId?: number;
  tab?: string;
  findingRef?: string;
  leadRef?: string;
  trafficCoverage?: {
    cellIds: number[];
    category?: string;
    testClass?: string;
  };
};

function cleanReference(value: string | null) {
  const reference = value?.trim();
  return reference ? reference.replace(/[.,;:!?]+$/, "") : undefined;
}

export function parseRoute(hash = "#/"): Route {
  if (!hash || hash === "#/" || hash === "#") return { name: "list" };

  const [rawRouteHash, queryString = ""] = hash.split("?", 2);
  // Keep bookmarks created before Applications was renamed to Systems working.
  const routeHash = rawRouteHash.replace(/^#\/applications(?=\/|$)/, "#/systems");
  const query = new URLSearchParams(queryString);
  const findingRef = cleanReference(query.get("finding"));
  const leadRef = cleanReference(query.get("lead"));
  const cellIds = (query.get("coverage_cells") || "")
    .split(",")
    .map(Number)
    .filter((value) => Number.isInteger(value) && value > 0);
  const trafficCoverage = cellIds.length
    ? {
        cellIds,
        category: cleanReference(query.get("coverage_category")),
        testClass: cleanReference(query.get("test_class")),
      }
    : undefined;
  let m;
  if ((m = routeHash.match(/^#\/sites\/new$/))) return { name: "site-new" };
  if ((m = routeHash.match(/^#\/sites\/(\d+)\/edit$/))) return { name: "site-edit", id: +m[1] };
  if ((m = routeHash.match(/^#\/sites\/(\d+)\/runs\/new$/)))
    return { name: "run-new", siteId: +m[1] };
  if ((m = routeHash.match(/^#\/sites\/(\d+)$/))) return { name: "site-detail", id: +m[1] };
  if ((m = routeHash.match(/^#\/apis\/new$/))) return { name: "api-new" };
  if ((m = routeHash.match(/^#\/apis\/(\d+)\/edit$/))) return { name: "api-edit", id: +m[1] };
  if ((m = routeHash.match(/^#\/apis\/(\d+)\/files$/))) return { name: "api-files", id: +m[1] };
  if ((m = routeHash.match(/^#\/apis\/(\d+)\/runs\/new$/)))
    return { name: "api-run-new", id: +m[1] };
  if ((m = routeHash.match(/^#\/apis\/(\d+)\/(runs|endpoints|credentials)$/)))
    return { name: "api-detail", id: +m[1], tab: m[2] };
  if ((m = routeHash.match(/^#\/apis\/(\d+)$/))) return { name: "api-detail", id: +m[1] };
  if (routeHash === "#/apis") return { name: "api-list" };
  if ((m = routeHash.match(/^#\/api-runs\/(\d+)\/([a-z]+)$/)))
    return { name: "api-run-detail", id: +m[1], tab: m[2], findingRef, trafficCoverage };
  if ((m = routeHash.match(/^#\/api-runs\/(\d+)$/)))
    return { name: "api-run-detail", id: +m[1], findingRef };
  if (routeHash === "#/sast-runs/new") return { name: "sast-run-new" };
  if (routeHash === "#/sast-runs") return { name: "sast-list" };
  if ((m = routeHash.match(/^#\/sast-runs\/(\d+)\/([a-z-]+)$/)))
    return { name: "sast-run-detail", id: +m[1], tab: m[2], leadRef };
  if ((m = routeHash.match(/^#\/sast-runs\/(\d+)$/)))
    return { name: "sast-run-detail", id: +m[1], leadRef };
  if ((m = routeHash.match(/^#\/runs\/(\d+)\/alice-popout$/)))
    return { name: "alice-popout", id: +m[1] };
  if ((m = routeHash.match(/^#\/runs\/(\d+)\/([a-z]+)$/)))
    return {
      name: "run-detail",
      id: +m[1],
      tab: m[2],
      findingRef,
      leadRef,
      trafficCoverage,
    };
  if ((m = routeHash.match(/^#\/runs\/(\d+)$/)))
    return { name: "run-detail", id: +m[1], findingRef, leadRef };
  if (routeHash === "#/systems/new") return { name: "system-new" };
  if ((m = routeHash.match(/^#\/systems\/(\d+)\/edit$/))) return { name: "system-edit", id: +m[1] };
  if ((m = routeHash.match(/^#\/systems\/(\d+)\/campaigns\/new$/)))
    return { name: "campaign-new", id: +m[1] };
  if ((m = routeHash.match(/^#\/systems\/(\d+)\/campaigns\/(\d+)\/([a-z]+)$/)))
    return { name: "campaign-detail", id: +m[1], campaignId: +m[2], tab: m[3], findingRef };
  if ((m = routeHash.match(/^#\/systems\/(\d+)\/campaigns\/(\d+)$/)))
    return { name: "campaign-detail", id: +m[1], campaignId: +m[2], findingRef };
  if ((m = routeHash.match(/^#\/systems\/(\d+)\/([a-z-]+)$/)))
    return { name: "system-detail", id: +m[1], tab: m[2] };
  if ((m = routeHash.match(/^#\/systems\/(\d+)$/))) return { name: "system-detail", id: +m[1] };
  if (routeHash === "#/systems") return { name: "system-list" };
  if (routeHash === "#/active-jobs") return { name: "active-jobs" };
  if (routeHash === "#/stats" || routeHash === "#/stats/usage") return { name: "stats" };
  if (routeHash === "#/settings") return { name: "settings" };
  if (routeHash === "#/scan-policy") return { name: "scan-policy" };
  if (routeHash === "#/external-integrations") return { name: "external-integrations" };
  if (routeHash === "#/debug") return { name: "debug" };
  if (routeHash === "#/reporting-debug") return { name: "reporting-debug" };
  if (routeHash === "#/benchmark-lab") return { name: "benchmark-lab" };
  if (routeHash === "#/benchmark-lab/evaluations/new") return { name: "benchmark-evaluation-new" };
  if ((m = routeHash.match(/^#\/benchmark-lab\/evaluations\/(\d+)\/([a-z-]+)$/)))
    return { name: "benchmark-evaluation-detail", id: +m[1], tab: m[2] };
  if ((m = routeHash.match(/^#\/benchmark-lab\/evaluations\/(\d+)$/)))
    return { name: "benchmark-evaluation-detail", id: +m[1] };
  if ((m = routeHash.match(/^#\/benchmark-lab\/comparisons\/(\d+)$/)))
    return { name: "benchmark-comparison-detail", id: +m[1] };

  return { name: "not-found" };
}
