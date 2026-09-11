import { req } from "./request.ts";

export const getLLMStatistics = (month) =>
  req(`/api/statistics/llm${month ? `?month=${encodeURIComponent(month)}` : ""}`);

export const refreshLLMPrices = () => req("/api/statistics/llm/prices/refresh", { method: "POST" });

export const updateLLMPrices = (b) => req("/api/statistics/llm/prices", { method: "PUT", body: b });

export const resetLLMStatistics = () => req("/api/statistics/llm", { method: "DELETE" });
