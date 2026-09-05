import { AGENT_ROLE_LABELS } from "./agentRoles.js";

export function scanProfileToForm(profile) {
  const rm = (profile && profile.role_models) || {};
  const role_models = {};
  for (const [role] of AGENT_ROLE_LABELS) role_models[role] = rm[role] ? String(rm[role]) : "";
  return {
    name: profile?.name || "",
    default_model_id: profile?.default_model_id ? String(profile.default_model_id) : "",
    role_models,
  };
}
