import { getFindings as readFindings, updateFinding as patchFinding } from "./findings.ts";
import { req } from "./request.ts";

export const getApiRun = (id) => req(`/api/api-test-runs/${id}`);

export const deleteApiRun = (id) => req(`/api/api-test-runs/${id}`, { method: "DELETE" });

export const getApiAliceSessions = (id) => req(`/api/api-test-runs/${id}/alice/sessions`);

export const saveApiAliceSessions = (id, b) =>
  req(`/api/api-test-runs/${id}/alice/sessions`, { method: "PUT", body: b });

export const getApiAliceStatus = (id) => req(`/api/api-test-runs/${id}/alice/status`);

export const startApiAliceRun = (id, b) =>
  req(`/api/api-test-runs/${id}/alice/run`, { method: "POST", body: b });

export const stopApiAliceRun = (id) =>
  req(`/api/api-test-runs/${id}/alice/run`, { method: "DELETE" });

export const steerApiAliceGoal = (id, b) =>
  req(`/api/api-test-runs/${id}/alice/goal/steer`, { method: "POST", body: b });

export const getApiAgentLog = (id) => req(`/api/api-test-runs/${id}/agent-log`);

export const getApiAgentLogPage = (id, { limit = 200, beforeId } = {}) => {
  const query = new URLSearchParams({ limit: String(Math.min(limit + 1, 1001)) });
  if (beforeId != null) query.set("before_id", String(beforeId));
  return req(`/api/api-test-runs/${id}/agent-log?${query.toString()}`).then((entries) => {
    const hasMore = entries.length > limit;
    return {
      entries: hasMore ? entries.slice(-limit) : entries,
      hasMore,
    };
  });
};

export const clearApiAgentLog = (id) =>
  req(`/api/api-test-runs/${id}/agent-log`, { method: "DELETE" });

export const startApiScan = (id, coverageMode) =>
  req(`/api/api-test-runs/${id}/scan/start`, {
    method: "POST",
    body: coverageMode ? { coverage_mode: coverageMode } : undefined,
  });

export const stopApiScan = (id) => req(`/api/api-test-runs/${id}/scan/stop`, { method: "POST" });

export const getApiScanStatus = (id) => req(`/api/api-test-runs/${id}/scan/status`);

export const getApiFindings = (id) => readFindings({ runKind: "api", runId: id });

export const clearApiFindings = (id) =>
  req(`/api/api-test-runs/${id}/findings`, { method: "DELETE" });

export const deleteApiFinding = (id, fid) =>
  req(`/api/api-test-runs/${id}/findings/${fid}`, { method: "DELETE" });

export const updateApiFinding = (id, fid, body) =>
  patchFinding({ runKind: "api", runId: id }, fid, body);

export const importApiFindings = (id, b) =>
  req(`/api/api-test-runs/${id}/findings/import`, { method: "POST", body: b });

export const getApiTraffic = (id, since) =>
  req(`/api/api-test-runs/${id}/traffic${since ? `?since_id=${since}` : ""}`);

export const getApiTrafficCount = (id) => req(`/api/api-test-runs/${id}/traffic/count`);

export const getApiCoverageMatrix = (id) => req(`/api/api-test-runs/${id}/coverage`);

export const getApiRunLeads = (id) => req(`/api/api-test-runs/${id}/leads`);

export const getApiRunAvailableSastRuns = (id) =>
  req(`/api/api-test-runs/${id}/sast-runs/available`);

export const importApiSastLeads = (id, b) =>
  req(`/api/api-test-runs/${id}/import-leads`, { method: "POST", body: b });

export const clearApiRunLeads = (id) => req(`/api/api-test-runs/${id}/leads`, { method: "DELETE" });

export const deleteApiRunLead = (id, lid) =>
  req(`/api/api-test-runs/${id}/leads/${lid}`, { method: "DELETE" });

export const getApiTokenUsage = (id) => req(`/api/api-test-runs/${id}/token-usage`);

export const resumeApiScan = (id) =>
  req(`/api/api-test-runs/${id}/scan/resume`, { method: "POST" });

export const getApiScannerSessions = (id, includeInactive = true) =>
  req(
    `/api/api-test-runs/${id}/scanner-sessions${includeInactive ? "?include_inactive=true" : ""}`,
  );

export const updateApiScannerSession = (runId, sessionId, b) =>
  req(`/api/api-test-runs/${runId}/scanner-sessions/${sessionId}`, { method: "PATCH", body: b });

export const validateApiScannerSessions = (id) =>
  req(`/api/api-test-runs/${id}/scanner-sessions/validate`, { method: "POST" });
