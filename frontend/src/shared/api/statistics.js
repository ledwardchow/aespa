import { req } from "./request.ts";

export const getLLMStatistics = (selection = {}) => {
  const params = new URLSearchParams(
    typeof selection === "string" ? { month: selection } : selection,
  );
  return req(`/api/statistics/llm${params.size ? `?${params}` : ""}`);
};

export const refreshLLMPrices = () => req("/api/statistics/llm/prices/refresh", { method: "POST" });

export const updateLLMPrices = (b) => req("/api/statistics/llm/prices", { method: "PUT", body: b });

export const resetLLMStatistics = () => req("/api/statistics/llm", { method: "DELETE" });
