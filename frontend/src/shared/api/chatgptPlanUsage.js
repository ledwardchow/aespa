import { req } from "./request.ts";

export const PLAN_USAGE_EXTENSION_ID = "aespa.chatgptplanusage";
const BASE = `/extension/${PLAN_USAGE_EXTENSION_ID}`;

export const getPlanUsageSummary = (window) =>
  req(`${BASE}/summary?window=${encodeURIComponent(window)}`);
export const checkPlanUsageWithCodex = () => req(`${BASE}/codex/check`, { method: "POST" });
export const deletePlanUsageReading = (id) => req(`${BASE}/readings/${id}`, { method: "DELETE" });
