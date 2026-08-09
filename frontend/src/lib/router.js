import { useState, useEffect } from "react";

function cleanReference(value) {
  const reference = value?.trim();
  return reference ? reference.replace(/[.,;:!?]+$/, "") : undefined;
}

export function useRoute() {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const cb = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", cb);
    return () => window.removeEventListener("hashchange", cb);
  }, []);

  if (!hash || hash === "#/" || hash === "#") return { name: "list" };

  const [routeHash, queryString = ""] = hash.split("?", 2);
  const query = new URLSearchParams(queryString);
  const findingRef = cleanReference(query.get("finding"));
  const leadRef = cleanReference(query.get("lead"));
  let m;
  if ((m = routeHash.match(/^#\/sites\/new$/)))               return { name: "site-new" };
  if ((m = routeHash.match(/^#\/sites\/(\d+)\/edit$/)))       return { name: "site-edit",   id: +m[1] };
  if ((m = routeHash.match(/^#\/sites\/(\d+)\/runs\/new$/)))  return { name: "run-new",     siteId: +m[1] };
  if ((m = routeHash.match(/^#\/sites\/(\d+)$/)))             return { name: "site-detail", id: +m[1] };
  if ((m = routeHash.match(/^#\/apis\/new$/)))                return { name: "api-new" };
  if ((m = routeHash.match(/^#\/apis\/(\d+)\/edit$/)))        return { name: "api-edit",    id: +m[1] };
  if ((m = routeHash.match(/^#\/apis\/(\d+)\/files$/)))       return { name: "api-files",   id: +m[1] };
  if ((m = routeHash.match(/^#\/apis\/(\d+)\/runs\/new$/)))   return { name: "api-run-new", id: +m[1] };
  if ((m = routeHash.match(/^#\/apis\/(\d+)$/)))              return { name: "api-detail",  id: +m[1] };
  if (routeHash === "#/apis")                                 return { name: "api-list" };
  if ((m = routeHash.match(/^#\/api-runs\/(\d+)\/([a-z]+)$/))) return { name: "api-run-detail", id: +m[1], tab: m[2], findingRef };
  if ((m = routeHash.match(/^#\/api-runs\/(\d+)$/)))          return { name: "api-run-detail", id: +m[1], findingRef };
  if (routeHash === "#/sast-runs/new")                              return { name: "sast-run-new" };
  if (routeHash === "#/sast-runs")                                  return { name: "sast-list" };
  if ((m = routeHash.match(/^#\/sast-runs\/(\d+)\/([a-z-]+)$/))) return { name: "sast-run-detail", id: +m[1], tab: m[2], leadRef };
  if ((m = routeHash.match(/^#\/sast-runs\/(\d+)$/)))            return { name: "sast-run-detail", id: +m[1], leadRef };
  if ((m = routeHash.match(/^#\/runs\/(\d+)\/alice-popout$/))) return { name: "alice-popout", id: +m[1] };
  if ((m = routeHash.match(/^#\/runs\/(\d+)\/([a-z]+)$/)))   return { name: "run-detail",  id: +m[1], tab: m[2], findingRef, leadRef };
  if ((m = routeHash.match(/^#\/runs\/(\d+)$/)))              return { name: "run-detail",  id: +m[1], findingRef, leadRef };
  if (routeHash === "#/applications/new")                     return { name: "app-new" };
  if ((m = routeHash.match(/^#\/applications\/(\d+)\/edit$/))) return { name: "app-edit", id: +m[1] };
  if ((m = routeHash.match(/^#\/applications\/(\d+)\/campaigns\/new$/))) return { name: "campaign-new", id: +m[1] };
  if ((m = routeHash.match(/^#\/applications\/(\d+)\/campaigns\/(\d+)\/([a-z]+)$/))) return { name: "campaign-detail", id: +m[1], campaignId: +m[2], tab: m[3], findingRef };
  if ((m = routeHash.match(/^#\/applications\/(\d+)\/campaigns\/(\d+)$/))) return { name: "campaign-detail", id: +m[1], campaignId: +m[2], findingRef };
  if ((m = routeHash.match(/^#\/applications\/(\d+)\/([a-z-]+)$/))) return { name: "app-detail", id: +m[1], tab: m[2] };
  if ((m = routeHash.match(/^#\/applications\/(\d+)$/)))       return { name: "app-detail", id: +m[1] };
  if (routeHash === "#/applications")                         return { name: "app-list" };
  if (routeHash === "#/active-jobs")                          return { name: "active-jobs" };
  if (routeHash === "#/stats" || routeHash === "#/stats/usage")    return { name: "stats" };
  if (routeHash === "#/settings")                             return { name: "settings" };
  if (routeHash === "#/scan-policy")                          return { name: "scan-policy" };
  if (routeHash === "#/external-integrations")                return { name: "external-integrations" };
  if (routeHash === "#/debug")                                return { name: "debug" };
  if (routeHash === "#/reporting-debug")                      return { name: "reporting-debug" };

  return { name: "list" };
}

export const nav = (to) => { window.location.hash = to; };
