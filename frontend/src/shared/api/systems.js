import { req } from "./request.ts";

export const listSystems = () => req("/api/systems");

export const createSystem = (b) => req("/api/systems", { method: "POST", body: b });

export const getSystem = (id) => req(`/api/systems/${id}`);

export const updateSystem = (id, b) => req(`/api/systems/${id}`, { method: "PATCH", body: b });

export const deleteSystem = (id) => req(`/api/systems/${id}`, { method: "DELETE" });

export const listSystemComponents = (id) => req(`/api/systems/${id}/components`);

export const createSystemComponent = (id, b) =>
  req(`/api/systems/${id}/components`, { method: "POST", body: b });

export const updateSystemComponent = (id, cid, b) =>
  req(`/api/systems/${id}/components/${cid}`, { method: "PATCH", body: b });

export const deleteSystemComponent = (id, cid) =>
  req(`/api/systems/${id}/components/${cid}`, { method: "DELETE" });

export const listComponentSnapshots = (id, cid) =>
  req(`/api/systems/${id}/components/${cid}/snapshots`);

export const uploadComponentSnapshot = (id, cid, file) => {
  const fd = new FormData();
  fd.append("file", file);
  return req(`/api/systems/${id}/components/${cid}/snapshots`, { method: "POST", body: fd });
};

export const deleteComponentSnapshot = (id, cid, sid) =>
  req(`/api/systems/${id}/components/${cid}/snapshots/${sid}`, { method: "DELETE" });

export const listSystemTargets = (id) => req(`/api/systems/${id}/targets`);

export const attachSystemTarget = (id, b) =>
  req(`/api/systems/${id}/targets`, { method: "POST", body: b });

export const updateSystemTarget = (id, tid, b) =>
  req(`/api/systems/${id}/targets/${tid}`, { method: "PATCH", body: b });

export const detachSystemTarget = (id, tid) =>
  req(`/api/systems/${id}/targets/${tid}`, { method: "DELETE" });

export const listSystemHints = (id) => req(`/api/systems/${id}/hints`);

export const createSystemHint = (id, b) =>
  req(`/api/systems/${id}/hints`, { method: "POST", body: b });

export const deleteSystemHint = (id, hid) =>
  req(`/api/systems/${id}/hints/${hid}`, { method: "DELETE" });

export const listCampaigns = (id) => req(`/api/systems/${id}/campaigns`);

export const createCampaign = (id, b) =>
  req(`/api/systems/${id}/campaigns`, { method: "POST", body: b });

export const getCampaign = (id, cid) => req(`/api/systems/${id}/campaigns/${cid}`);

export const deleteCampaign = (id, cid) =>
  req(`/api/systems/${id}/campaigns/${cid}`, { method: "DELETE" });

export const startCampaign = (id, cid) =>
  req(`/api/systems/${id}/campaigns/${cid}/start`, { method: "POST" });

export const stopCampaign = (id, cid) =>
  req(`/api/systems/${id}/campaigns/${cid}/stop`, { method: "POST" });

export const resumeCampaign = (id, cid) =>
  req(`/api/systems/${id}/campaigns/${cid}/resume`, { method: "POST" });

export const retryCampaign = (id, cid) =>
  req(`/api/systems/${id}/campaigns/${cid}/retry`, { method: "POST" });

export const resumeCampaignSource = (id, cid, mid) =>
  req(`/api/systems/${id}/campaigns/${cid}/sources/${mid}/resume`, { method: "POST" });

export const resumeCampaignTarget = (id, cid, mid) =>
  req(`/api/systems/${id}/campaigns/${cid}/targets/${mid}/resume`, { method: "POST" });

export const getCampaignStatus = (id, cid) => req(`/api/systems/${id}/campaigns/${cid}/status`);

export const getCampaignActivity = (id, cid) => req(`/api/systems/${id}/campaigns/${cid}/activity`);

export const getCampaignActivityStreamUrl = (id, cid, cursor) =>
  `/api/systems/${id}/campaigns/${cid}/activity/stream${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`;

export const getCampaignConnections = (id, cid, scope = "cross_component") =>
  req(`/api/systems/${id}/campaigns/${cid}/connections${scope ? `?scope=${scope}` : ""}`);

export const rebuildCampaignConnections = (id, cid) =>
  req(`/api/systems/${id}/campaigns/${cid}/connections/rebuild`, { method: "POST" });

export const getCampaignMappings = (id, cid) => req(`/api/systems/${id}/campaigns/${cid}/mappings`);

export const editCampaignMapping = (id, cid, mid, b) =>
  req(`/api/systems/${id}/campaigns/${cid}/mappings/${mid}`, { method: "PUT", body: b });

export const reviewCampaignMappings = (id, cid, b) =>
  req(`/api/systems/${id}/campaigns/${cid}/review`, { method: "POST", body: b });

export const supplementalValidateCampaignTarget = (id, cid, tid, b) =>
  req(`/api/systems/${id}/campaigns/${cid}/targets/${tid}/supplemental-validate`, {
    method: "POST",
    body: b,
  });

export const continueCampaign = (id, cid) =>
  req(`/api/systems/${id}/campaigns/${cid}/continue`, { method: "POST" });

export const getCampaignFindings = (id, cid) => req(`/api/systems/${id}/campaigns/${cid}/findings`);

// Validation cases are the executable, readiness-gated units produced from
// reviewed campaign mappings. Older campaign endpoints may not expose this
// resource yet, so callers should treat a failed request as an empty case list
// when they need to keep legacy campaign pages readable.
export const getCampaignValidationCases = (id, cid) =>
  req(`/api/systems/${id}/campaigns/${cid}/validation-cases`);
