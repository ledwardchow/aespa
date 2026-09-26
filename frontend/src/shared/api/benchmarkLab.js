import { req } from "./request.ts";

const BASE = "/extension/aespa.sast-benchmarking";

export const listBenchmarkDatasets = () => req(`${BASE}/datasets`);
export const createBenchmarkDataset = (body) =>
  req(`${BASE}/datasets`, { method: "POST", body });
export const getBenchmarkDataset = (id) => req(`${BASE}/datasets/${id}`);
export const updateBenchmarkDataset = (id, body) =>
  req(`${BASE}/datasets/${id}`, { method: "PUT", body });
export const deleteBenchmarkDataset = (id) =>
  req(`${BASE}/datasets/${id}`, { method: "DELETE" });
export const listBenchmarkEvaluations = () => req(`${BASE}/evaluations`);
export const createBenchmarkEvaluation = (body) =>
  req(`${BASE}/evaluations`, { method: "POST", body });
export const getBenchmarkEvaluation = (id) => req(`${BASE}/evaluations/${id}`);
export const runBenchmarkEvaluation = (id) =>
  req(`${BASE}/evaluations/${id}/run`, { method: "POST" });
export const reviewBenchmarkMatch = (evaluationId, matchId, body) =>
  req(`${BASE}/evaluations/${evaluationId}/matches/${matchId}/review`, {
    method: "POST",
    body,
  });
export const getBenchmarkEvaluationExport = (id) =>
  req(`${BASE}/evaluations/${id}/export`);
export const getBenchmarkEvaluationExportUrl = (id, format = "json") =>
  `${BASE}/evaluations/${id}/export?format=${encodeURIComponent(format)}`;
export const listBenchmarkComparisons = () => req(`${BASE}/comparisons`);
export const createBenchmarkComparison = (body) =>
  req(`${BASE}/comparisons`, { method: "POST", body });
export const getBenchmarkComparison = (id) => req(`${BASE}/comparisons/${id}`);
export const recalculateBenchmarkComparison = (id) =>
  req(`${BASE}/comparisons/${id}/recalculate`, { method: "POST" });
