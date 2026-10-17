import { req } from "./request.ts";

export const API_EXTENSION_ID = "aespa.api";
const BASE = `/extension/${API_EXTENSION_ID}/admin`;

export const getApiDefinition = (url) => req(url);

export const listApiTokens = () => req(`${BASE}/tokens`);
export const createApiToken = (body) => req(`${BASE}/tokens`, { method: "POST", body });
export const updateApiToken = (id, body) => req(`${BASE}/tokens/${id}`, { method: "PATCH", body });
export const deactivateApiToken = (id) => req(`${BASE}/tokens/${id}/deactivate`, { method: "POST" });
export const reactivateApiToken = (id) => req(`${BASE}/tokens/${id}/reactivate`, { method: "POST" });
export const showApiToken = (id) => req(`${BASE}/tokens/${id}/token`);
export const rotateWebhookSecret = (id) =>
  req(`${BASE}/tokens/${id}/webhook-secret`, { method: "POST" });
export const listFailedDeliveries = () => req(`${BASE}/deliveries?status=failed&limit=20`);
