import { importJson } from "./request.ts";
import { req } from "./request.ts";

export const listApiCollections = () => req("/api/api-collections");

export const getApiCollection = (id) => req(`/api/api-collections/${id}`);

export const createApiCollection = (b) => req("/api/api-collections", { method: "POST", body: b });

export const updateApiCollection = (id, b) =>
  req(`/api/api-collections/${id}`, { method: "PUT", body: b });

export const deleteApiCollection = (id) => req(`/api/api-collections/${id}`, { method: "DELETE" });

export const importApiCollection = (text) => importJson("/api/api-collections/import", text);

export const listApiDocuments = (id) => req(`/api/api-collections/${id}/documents`);

export const uploadApiDocuments = (id, files) => {
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  return req(`/api/api-collections/${id}/documents`, { method: "POST", body: fd });
};

export const downloadApiDocument = (id, docId) => {
  window.location.href = `/api/api-collections/${id}/documents/${docId}/download`;
};

export const deleteApiDocument = (id, docId) =>
  req(`/api/api-collections/${id}/documents/${docId}`, { method: "DELETE" });

export const parseApiDocument = (id, docId) =>
  req(`/api/api-collections/${id}/documents/${docId}/parse`, { method: "POST" });

export const listApiEndpoints = (id) => req(`/api/api-collections/${id}/endpoints`);

export const patchEndpointScope = (id, eid, b) =>
  req(`/api/api-collections/${id}/endpoints/${eid}/scope`, { method: "PATCH", body: b });

export const listApiCredentials = (id) => req(`/api/api-collections/${id}/credentials`);

export const createApiCredential = (id, b) =>
  req(`/api/api-collections/${id}/credentials`, { method: "POST", body: b });

export const deleteApiCredential = (id, cid) =>
  req(`/api/api-collections/${id}/credentials/${cid}`, { method: "DELETE" });

export const getApiReadiness = (id) => req(`/api/api-collections/${id}/readiness`);

export const runApiReadiness = (id) =>
  req(`/api/api-collections/${id}/readiness`, { method: "POST" });

export const purgeCollectionData = (id) =>
  req(`/api/api-collections/${id}/data`, { method: "DELETE" });

export const listApiRuns = (id) => req(`/api/api-collections/${id}/test-runs`);

export const createApiRun = (id, b) =>
  req(`/api/api-collections/${id}/test-runs`, { method: "POST", body: b });
