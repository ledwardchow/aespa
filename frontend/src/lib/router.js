import { useState, useEffect } from "react";

export function useRoute() {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const cb = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", cb);
    return () => window.removeEventListener("hashchange", cb);
  }, []);

  if (!hash || hash === "#/" || hash === "#") return { name: "list" };

  let m;
  if ((m = hash.match(/^#\/sites\/new$/)))               return { name: "site-new" };
  if ((m = hash.match(/^#\/sites\/(\d+)\/edit$/)))       return { name: "site-edit",   id: +m[1] };
  if ((m = hash.match(/^#\/sites\/(\d+)\/runs\/new$/)))  return { name: "run-new",     siteId: +m[1] };
  if ((m = hash.match(/^#\/sites\/(\d+)$/)))             return { name: "site-detail", id: +m[1] };
  if ((m = hash.match(/^#\/apis\/new$/)))                return { name: "api-new" };
  if ((m = hash.match(/^#\/apis\/(\d+)\/edit$/)))        return { name: "api-edit",    id: +m[1] };
  if ((m = hash.match(/^#\/apis\/(\d+)\/files$/)))       return { name: "api-files",   id: +m[1] };
  if ((m = hash.match(/^#\/apis\/(\d+)\/runs\/new$/)))   return { name: "api-run-new", id: +m[1] };
  if ((m = hash.match(/^#\/apis\/(\d+)$/)))              return { name: "api-detail",  id: +m[1] };
  if (hash === "#/apis")                                 return { name: "api-list" };
  if ((m = hash.match(/^#\/api-runs\/(\d+)\/([a-z]+)$/))) return { name: "api-run-detail", id: +m[1], tab: m[2] };
  if ((m = hash.match(/^#\/api-runs\/(\d+)$/)))          return { name: "api-run-detail", id: +m[1] };
  if (hash === "#/sast-runs/new")                              return { name: "sast-run-new" };
  if (hash === "#/sast-runs")                                  return { name: "sast-list" };
  if ((m = hash.match(/^#\/sast-runs\/(\d+)\/([a-z-]+)$/))) return { name: "sast-run-detail", id: +m[1], tab: m[2] };
  if ((m = hash.match(/^#\/sast-runs\/(\d+)$/)))            return { name: "sast-run-detail", id: +m[1] };
  if ((m = hash.match(/^#\/runs\/(\d+)\/([a-z]+)$/)))   return { name: "run-detail",  id: +m[1], tab: m[2] };
  if ((m = hash.match(/^#\/runs\/(\d+)$/)))              return { name: "run-detail",  id: +m[1] };
  if (hash === "#/active-jobs")                          return { name: "active-jobs" };
  if (hash === "#/settings")                             return { name: "settings" };
  if (hash === "#/scan-policy")                          return { name: "scan-policy" };
  if (hash === "#/external-integrations")                return { name: "external-integrations" };
  if (hash === "#/debug")                                return { name: "debug" };
  if (hash === "#/reporting-debug")                      return { name: "reporting-debug" };

  return { name: "list" };
}

export const nav = (to) => { window.location.hash = to; };
