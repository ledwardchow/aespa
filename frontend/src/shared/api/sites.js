import { importJson } from "./request.ts";
import { req } from "./request.ts";

export const listSites = () => req("/api/sites");

export const getSite = (id) => req(`/api/sites/${id}`);

export const createSite = (b) => req("/api/sites", { method: "POST", body: b });

export const updateSite = (id, b) => req(`/api/sites/${id}`, { method: "PUT", body: b });

export const deleteSite = (id) => req(`/api/sites/${id}`, { method: "DELETE" });

export const importSite = (text) => importJson("/api/sites/import", text);

export const listRuns = (siteId) => req(`/api/sites/${siteId}/test-runs`);

export const createRun = (siteId, b) =>
  req(`/api/sites/${siteId}/test-runs`, { method: "POST", body: b });

export const updateScopeHosts = (siteId, hosts) =>
  req(`/api/sites/${siteId}/scope-hosts`, { method: "PUT", body: { scope_hosts: hosts } });
