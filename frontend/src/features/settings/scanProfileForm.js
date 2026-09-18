import { AGENT_ROLE_LABELS } from "./agentRoles.js";

const providerIdForModel = (models, modelId) => {
  const model = (models || []).find((item) => item.id === Number(modelId));
  return model?.provider_id ? String(model.provider_id) : "";
};

export function scanProfileToForm(profile, models = []) {
  const rm = (profile && profile.role_models) || {};
  const role_models = {};
  const role_providers = {};
  for (const [role] of AGENT_ROLE_LABELS) {
    role_models[role] = rm[role] ? String(rm[role]) : "";
    role_providers[role] = providerIdForModel(models, rm[role]);
  }
  return {
    name: profile?.name || "",
    default_model_id: profile?.default_model_id ? String(profile.default_model_id) : "",
    default_provider_id: providerIdForModel(models, profile?.default_model_id),
    role_models,
    role_providers,
  };
}
