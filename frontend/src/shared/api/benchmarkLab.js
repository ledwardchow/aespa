import { req } from "./request.ts";

const BASE = "/extension/aespa.benchmarking";

export const listBenchmarkTargets = () => req(`${BASE}/targets`);
export const saveBenchmarkGroundTruth = (kind, id, datasetId) =>
  req(`${BASE}/ground-truth/${kind}/${id}`, { method: "PUT", body: { dataset_id: datasetId } });
export const listBenchmarkResults = () => req(`${BASE}/results`);
export const createBenchmarkResult = (body) => req(`${BASE}/results`, { method: "POST", body });
export const deleteBenchmarkResult = (id) => req(`${BASE}/results/${id}`, { method: "DELETE" });
export const reviewBenchmarkResult = (resultId, externalId, body) =>
  req(`${BASE}/results/${resultId}/review`, {
    method: "PUT",
    body: { external_id: externalId, ...body },
  });

export const listBenchmarkDatasets = () => req(`${BASE}/datasets`);
export const createBenchmarkDataset = (body) => req(`${BASE}/datasets`, { method: "POST", body });
export const getBenchmarkDataset = (id) => req(`${BASE}/datasets/${id}`);
export const updateBenchmarkDataset = (id, body) =>
  req(`${BASE}/datasets/${id}`, { method: "PUT", body });
export const deleteBenchmarkDataset = (id) => req(`${BASE}/datasets/${id}`, { method: "DELETE" });
export const listBenchmarkEvaluations = () => req(`${BASE}/evaluations`);
export const createBenchmarkEvaluation = (body) =>
  req(`${BASE}/evaluations`, { method: "POST", body });
export const getBenchmarkEvaluation = (id) => req(`${BASE}/evaluations/${id}`);
export const deleteBenchmarkEvaluation = (id) =>
  req(`${BASE}/evaluations/${id}`, { method: "DELETE" });
export const runBenchmarkEvaluation = (id) =>
  req(`${BASE}/evaluations/${id}/run`, { method: "POST" });
export const reviewBenchmarkMatch = (evaluationId, matchId, body) =>
  req(`${BASE}/evaluations/${evaluationId}/matches/${matchId}/review`, {
    method: "POST",
    body,
  });
export const getBenchmarkEvaluationExport = (id) => req(`${BASE}/evaluations/${id}/export`);
export const getBenchmarkEvaluationExportUrl = (id, format = "json") =>
  `${BASE}/evaluations/${id}/export?format=${encodeURIComponent(format)}`;
export const listBenchmarkComparisons = () => req(`${BASE}/comparisons`);
export const createBenchmarkComparison = (body) =>
  req(`${BASE}/comparisons`, { method: "POST", body });
export const getBenchmarkComparison = (id) => req(`${BASE}/comparisons/${id}`);
export const deleteBenchmarkComparison = (id) =>
  req(`${BASE}/comparisons/${id}`, { method: "DELETE" });
export const recalculateBenchmarkComparison = (id) =>
  req(`${BASE}/comparisons/${id}/recalculate`, { method: "POST" });
