import { req } from "./request.ts";

export const getWebCoverageMatrix = (id) => req(`/api/test-runs/${id}/coverage`);

export const seedWebWorkprogram = (id) =>
  req(`/api/test-runs/${id}/coverage/seed`, { method: "POST" });

export const getRunAvailableSastRuns = (id) => req(`/api/test-runs/${id}/sast-runs/available`);

export const importSastLeads = (id, b) =>
  req(`/api/test-runs/${id}/import-leads`, { method: "POST", body: b });

export const getRunLeads = (id) => req(`/api/test-runs/${id}/leads`);

export const clearRunLeads = (id) => req(`/api/test-runs/${id}/leads`, { method: "DELETE" });

export const deleteRunLead = (id, lid) =>
  req(`/api/test-runs/${id}/leads/${lid}`, { method: "DELETE" });

export const resumeWebScan = (id) =>
  req(`/api/test-runs/${id}/thinking-scan/resume`, { method: "POST" });

export const resumeWebCrawl = (id) => req(`/api/test-runs/${id}/crawl/resume`, { method: "POST" });

export const listActiveJobs = () => req("/api/test-runs/active");

export const getRun = (id) => req(`/api/test-runs/${id}`);

export const getCrawlStatus = (id) => req(`/api/test-runs/${id}/crawl/status`);

export const deleteRun = (id) => req(`/api/test-runs/${id}`, { method: "DELETE" });

export const startRun = (id, body) =>
  req(`/api/test-runs/${id}/start`, { method: "POST", body: body || undefined });

export const stopRun = (id) => req(`/api/test-runs/${id}/stop`, { method: "POST" });

export const restartRun = (id) => req(`/api/test-runs/${id}/restart`, { method: "POST" });

export const clearCrawl = (id) => req(`/api/test-runs/${id}/crawl/clear`, { method: "POST" });

export const exportCrawl = (id) => {
  window.location.href = `/api/test-runs/${id}/crawl/export`;
};

export const importCrawl = (id, file) => {
  const fd = new FormData();
  fd.append("file", file);
  return req(`/api/test-runs/${id}/crawl/import`, { method: "POST", body: fd });
};

export const getGraph = (id) => req(`/api/test-runs/${id}/graph`);

export const listPages = (id) => req(`/api/test-runs/${id}/pages`);

export const getPage = (runId, pgId) => req(`/api/test-runs/${runId}/pages/${pgId}`);

export const getPageViews = (runId, pgId) => req(`/api/test-runs/${runId}/pages/${pgId}/views`);

export const testPageState = (runId, pgId, b = {}) =>
  req(`/api/test-runs/${runId}/pages/${pgId}/test`, { method: "POST", body: b });

export const getTargetIntelligence = (id, kind = "") =>
  req(`/api/test-runs/${id}/target-intelligence${kind ? `?kind=${encodeURIComponent(kind)}` : ""}`);

export const getScannerSessions = (id, includeInactive = true) =>
  req(`/api/test-runs/${id}/scanner-sessions${includeInactive ? "?include_inactive=true" : ""}`);

export const updateScannerSession = (runId, sessionId, b) =>
  req(`/api/test-runs/${runId}/scanner-sessions/${sessionId}`, { method: "PATCH", body: b });

export const validateScannerSessions = (id) =>
  req(`/api/test-runs/${id}/scanner-sessions/validate`, { method: "POST" });

export const getReconSummary = (id) => req(`/api/test-runs/${id}/recon-summary`);

export const setPageScope = (runId, pgId, b) =>
  req(`/api/test-runs/${runId}/pages/${pgId}/scope`, { method: "PATCH", body: b });

export const deletePage = (runId, pgId, cascade) =>
  req(`/api/test-runs/${runId}/pages/${pgId}?cascade=${cascade}`, { method: "DELETE" });

export const updateRun = (id, b) => req(`/api/test-runs/${id}`, { method: "PATCH", body: b });

export const startThinkingScan = (id, coverageMode) =>
  req(`/api/test-runs/${id}/thinking-scan/start`, {
    method: "POST",
    body: coverageMode ? { coverage_mode: coverageMode } : undefined,
  });

export const resumeThinkingScan = (id) =>
  req(`/api/test-runs/${id}/thinking-scan/resume`, { method: "POST" });

export const stopThinkingScan = (id) =>
  req(`/api/test-runs/${id}/thinking-scan/stop`, { method: "POST" });

export const getThinkingStatus = (id) => req(`/api/test-runs/${id}/thinking-scan/status`);

export const getCheckpointStatus = (id) => req(`/api/test-runs/${id}/thinking-scan/checkpoint`);

export const getScanLog = (id) => req(`/api/test-runs/${id}/scan-log`);

export const getAgentLog = (id) => req(`/api/test-runs/${id}/agent-log`);

export const getTokenUsage = (id) => req(`/api/test-runs/${id}/token-usage`);

export const getAliceSessions = (id) => req(`/api/test-runs/${id}/alice/sessions`);

export const saveAliceSessions = (id, b) =>
  req(`/api/test-runs/${id}/alice/sessions`, { method: "PUT", body: b });

export const getAliceStatus = (id) => req(`/api/test-runs/${id}/alice/status`);

export const startAliceRun = (id, b) =>
  req(`/api/test-runs/${id}/alice/run`, { method: "POST", body: b });

export const stopAliceRun = (id) => req(`/api/test-runs/${id}/alice/run`, { method: "DELETE" });

export const steerAliceGoal = (id, b) =>
  req(`/api/test-runs/${id}/alice/goal/steer`, { method: "POST", body: b });

export const getFindings = (id) => req(`/api/test-runs/${id}/findings`);

export const deleteFinding = (id, fid) =>
  req(`/api/test-runs/${id}/findings/${fid}`, { method: "DELETE" });

export const updateFinding = (id, fid, b) =>
  req(`/api/test-runs/${id}/findings/${fid}`, { method: "PATCH", body: b });

export const deleteFindingGroup = (id, title) =>
  req(`/api/test-runs/${id}/findings?title=${encodeURIComponent(title)}`, { method: "DELETE" });

export const importFindings = (id, b) =>
  req(`/api/test-runs/${id}/findings/import`, { method: "POST", body: b });

export const validateAllFindings = (id) => req(`/api/test-runs/${id}/validate`, { method: "POST" });

export const validateFinding = (id, fid) =>
  req(`/api/test-runs/${id}/findings/${fid}/validate`, { method: "POST" });

export const stopValidation = (id) => req(`/api/test-runs/${id}/validate/stop`, { method: "POST" });

export const getValidateStatus = (id) => req(`/api/test-runs/${id}/validate/status`);

export const getTraffic = (id, since) => req(`/api/test-runs/${id}/traffic?since_id=${since || 0}`);

export const getTrafficCount = (id) => req(`/api/test-runs/${id}/traffic/count`);

export const clearTraffic = (id) => req(`/api/test-runs/${id}/traffic`, { method: "DELETE" });

export const clearFindings = (id) => req(`/api/test-runs/${id}/findings`, { method: "DELETE" });

export const clearScanLog = (id) => req(`/api/test-runs/${id}/scan-log`, { method: "DELETE" });

export const clearTargetIntel = (id) =>
  req(`/api/test-runs/${id}/target-intelligence`, { method: "DELETE" });
