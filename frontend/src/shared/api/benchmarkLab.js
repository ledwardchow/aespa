import { req } from "./request.ts";

export const listBenchmarkDatasets = () => req("/api/benchmark-lab/datasets");
export const createBenchmarkDataset = (body) =>
  req("/api/benchmark-lab/datasets", { method: "POST", body });
export const getBenchmarkDataset = (id) => req(`/api/benchmark-lab/datasets/${id}`);
export const updateBenchmarkDataset = (id, body) =>
  req(`/api/benchmark-lab/datasets/${id}`, { method: "PUT", body });
export const deleteBenchmarkDataset = (id) =>
  req(`/api/benchmark-lab/datasets/${id}`, { method: "DELETE" });
export const listBenchmarkEvaluations = () => req("/api/benchmark-lab/evaluations");
export const createBenchmarkEvaluation = (body) =>
  req("/api/benchmark-lab/evaluations", { method: "POST", body });
export const getBenchmarkEvaluation = (id) => req(`/api/benchmark-lab/evaluations/${id}`);
export const runBenchmarkEvaluation = (id) =>
  req(`/api/benchmark-lab/evaluations/${id}/run`, { method: "POST" });
export const reviewBenchmarkMatch = (evaluationId, matchId, body) =>
  req(`/api/benchmark-lab/evaluations/${evaluationId}/matches/${matchId}/review`, {
    method: "POST",
    body,
  });
export const getBenchmarkEvaluationExport = (id) =>
  req(`/api/benchmark-lab/evaluations/${id}/export`);
export const getBenchmarkEvaluationExportUrl = (id, format = "json") =>
  `/api/benchmark-lab/evaluations/${id}/export?format=${encodeURIComponent(format)}`;
export const listBenchmarkComparisons = () => req("/api/benchmark-lab/comparisons");
export const createBenchmarkComparison = (body) =>
  req("/api/benchmark-lab/comparisons", { method: "POST", body });
export const getBenchmarkComparison = (id) => req(`/api/benchmark-lab/comparisons/${id}`);
export const recalculateBenchmarkComparison = (id) =>
  req(`/api/benchmark-lab/comparisons/${id}/recalculate`, { method: "POST" });
