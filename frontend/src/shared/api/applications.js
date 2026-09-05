import { req } from "./request.ts";

export const listApplications = () => req("/api/applications");

export const createApplication = (b) => req("/api/applications", { method: "POST", body: b });

export const getApplication = (id) => req(`/api/applications/${id}`);

export const updateApplication = (id, b) =>
  req(`/api/applications/${id}`, { method: "PATCH", body: b });

export const deleteApplication = (id) => req(`/api/applications/${id}`, { method: "DELETE" });

export const listAppComponents = (id) => req(`/api/applications/${id}/components`);

export const createAppComponent = (id, b) =>
  req(`/api/applications/${id}/components`, { method: "POST", body: b });

export const updateAppComponent = (id, cid, b) =>
  req(`/api/applications/${id}/components/${cid}`, { method: "PATCH", body: b });

export const deleteAppComponent = (id, cid) =>
  req(`/api/applications/${id}/components/${cid}`, { method: "DELETE" });

export const listComponentSnapshots = (id, cid) =>
  req(`/api/applications/${id}/components/${cid}/snapshots`);

export const uploadComponentSnapshot = (id, cid, file) => {
  const fd = new FormData();
  fd.append("file", file);
  return req(`/api/applications/${id}/components/${cid}/snapshots`, { method: "POST", body: fd });
};

export const deleteComponentSnapshot = (id, cid, sid) =>
  req(`/api/applications/${id}/components/${cid}/snapshots/${sid}`, { method: "DELETE" });

export const listAppTargets = (id) => req(`/api/applications/${id}/targets`);

export const attachAppTarget = (id, b) =>
  req(`/api/applications/${id}/targets`, { method: "POST", body: b });

export const updateAppTarget = (id, tid, b) =>
  req(`/api/applications/${id}/targets/${tid}`, { method: "PATCH", body: b });

export const detachAppTarget = (id, tid) =>
  req(`/api/applications/${id}/targets/${tid}`, { method: "DELETE" });

export const listAppHints = (id) => req(`/api/applications/${id}/hints`);

export const createAppHint = (id, b) =>
  req(`/api/applications/${id}/hints`, { method: "POST", body: b });

export const deleteAppHint = (id, hid) =>
  req(`/api/applications/${id}/hints/${hid}`, { method: "DELETE" });

export const listCampaigns = (id) => req(`/api/applications/${id}/campaigns`);

export const createCampaign = (id, b) =>
  req(`/api/applications/${id}/campaigns`, { method: "POST", body: b });

export const getCampaign = (id, cid) => req(`/api/applications/${id}/campaigns/${cid}`);

export const deleteCampaign = (id, cid) =>
  req(`/api/applications/${id}/campaigns/${cid}`, { method: "DELETE" });

export const startCampaign = (id, cid) =>
  req(`/api/applications/${id}/campaigns/${cid}/start`, { method: "POST" });

export const stopCampaign = (id, cid) =>
  req(`/api/applications/${id}/campaigns/${cid}/stop`, { method: "POST" });

export const resumeCampaign = (id, cid) =>
  req(`/api/applications/${id}/campaigns/${cid}/resume`, { method: "POST" });

export const retryCampaign = (id, cid) =>
  req(`/api/applications/${id}/campaigns/${cid}/retry`, { method: "POST" });

export const resumeCampaignSource = (id, cid, mid) =>
  req(`/api/applications/${id}/campaigns/${cid}/sources/${mid}/resume`, { method: "POST" });

export const resumeCampaignTarget = (id, cid, mid) =>
  req(`/api/applications/${id}/campaigns/${cid}/targets/${mid}/resume`, { method: "POST" });

export const getCampaignStatus = (id, cid) =>
  req(`/api/applications/${id}/campaigns/${cid}/status`);

export const getCampaignActivity = (id, cid) =>
  req(`/api/applications/${id}/campaigns/${cid}/activity`);

export const getCampaignActivityStreamUrl = (id, cid, cursor) =>
  `/api/applications/${id}/campaigns/${cid}/activity/stream${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`;

export const getCampaignConnections = (id, cid, scope = "cross_component") =>
  req(`/api/applications/${id}/campaigns/${cid}/connections${scope ? `?scope=${scope}` : ""}`);

export const rebuildCampaignConnections = (id, cid) =>
  req(`/api/applications/${id}/campaigns/${cid}/connections/rebuild`, { method: "POST" });

export const getCampaignMappings = (id, cid) =>
  req(`/api/applications/${id}/campaigns/${cid}/mappings`);

export const editCampaignMapping = (id, cid, mid, b) =>
  req(`/api/applications/${id}/campaigns/${cid}/mappings/${mid}`, { method: "PUT", body: b });

export const reviewCampaignMappings = (id, cid, b) =>
  req(`/api/applications/${id}/campaigns/${cid}/review`, { method: "POST", body: b });

export const supplementalValidateCampaignTarget = (id, cid, tid, b) =>
  req(`/api/applications/${id}/campaigns/${cid}/targets/${tid}/supplemental-validate`, {
    method: "POST",
    body: b,
  });

export const continueCampaign = (id, cid) =>
  req(`/api/applications/${id}/campaigns/${cid}/continue`, { method: "POST" });

export const getCampaignFindings = (id, cid) =>
  req(`/api/applications/${id}/campaigns/${cid}/findings`);
