import { importJson } from "./request.ts";
import { req } from "./request.ts";

export const listAllSastRuns = () => req(`/api/sast-runs`);

export const getSastScanLog = (id) => req(`/api/sast-runs/${id}/scan-log`);

export const getSastRun = (id) => req(`/api/sast-runs/${id}`);

export const importSastRun = (text) => importJson("/api/sast-runs/import", text);

export const updateSastRun = (id, b) => req(`/api/sast-runs/${id}`, { method: "PATCH", body: b });

export const getSastAnalysis = (id) => req(`/api/sast-runs/${id}/analysis`);

export const getSastHandoffTargets = (id) => req(`/api/sast-runs/${id}/handoff-targets`);

export const handoffSastLead = (id, lid, b) =>
  req(`/api/sast-runs/${id}/leads/${lid}/handoff`, { method: "POST", body: b });

export const deleteSastRun = (id) => req(`/api/sast-runs/${id}`, { method: "DELETE" });

export const startSastScan = (id) => req(`/api/sast-runs/${id}/scan/start`, { method: "POST" });

export const pauseSastScan = (id) => req(`/api/sast-runs/${id}/scan/pause`, { method: "POST" });

export const stopSastScan = (id) => req(`/api/sast-runs/${id}/scan/stop`, { method: "POST" });

export const resumeSastScan = (id) => req(`/api/sast-runs/${id}/scan/resume`, { method: "POST" });

export const getSastScanStatus = (id) => req(`/api/sast-runs/${id}/scan/status`);

export const getSastAgentLog = (id) => req(`/api/sast-runs/${id}/agent-log`);

export const getSastLeads = (id) => req(`/api/sast-runs/${id}/leads`);

export const getSastTokenUsage = (id) => req(`/api/sast-runs/${id}/token-usage`);

export const createStandaloneSastRun = (file, name, llm_profile_id) => {
  const fd = new FormData();
  fd.append("file", file);
  if (name) fd.append("name", name);
  if (llm_profile_id) fd.append("llm_profile_id", llm_profile_id);
  return req(`/api/sast-runs`, { method: "POST", body: fd });
};
