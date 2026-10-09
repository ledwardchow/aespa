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

export const listSavedCrawls = (siteId) => req(`/api/sites/${siteId}/saved-crawls`);

export const updateSavedCrawl = (siteId, savedId, b) =>
  req(`/api/sites/${siteId}/saved-crawls/${savedId}`, { method: "PATCH", body: b });

export const deleteSavedCrawl = (siteId, savedId) =>
  req(`/api/sites/${siteId}/saved-crawls/${savedId}`, { method: "DELETE" });

export const downloadSavedCrawl = (siteId, savedId) => {
  window.location.href = `/api/sites/${siteId}/saved-crawls/${savedId}/export`;
};

export const uploadSavedCrawl = (siteId, file, name) => {
  const fd = new FormData();
  fd.append("file", file);
  if (name) fd.append("name", name);
  return req(`/api/sites/${siteId}/saved-crawls/upload`, { method: "POST", body: fd });
};
