import { DEFAULT_LLM_FORM } from "./providerMetadata.js";

import { sortModelNames } from "../../shared/lib/modelSorting.js";

export function llmProfileToForm(cfg, providers = []) {
  const providerId = cfg?.provider_id || providers[0]?.id || "";
  const provider = providers.find((p) => p.id === providerId) || providers[0];
  if (cfg) {
    const hasTemp = cfg.temperature !== null && cfg.temperature !== undefined;
    return {
      name: cfg.name ?? (provider?.name && cfg.model ? `${provider.name}/${cfg.model}` : "Default"),
      provider_id: providerId,
      model: cfg.model,
      max_tokens: cfg.max_tokens,
      max_context_tokens: cfg.max_context_tokens || 128000,
      max_context_auto: cfg.context_limit_source !== "manual",
      temperature: hasTemp ? cfg.temperature : 0.2,
      use_temperature: hasTemp,
      use_vision: cfg.use_vision ?? false,
      force_tool_choice: cfg.force_tool_choice ?? false,
      reasoning_effort: cfg.reasoning_effort || "",
    };
  }
  const defaultModel = sortModelNames(provider?.models)[0] || "";
  const defaultName =
    provider?.name && defaultModel ? `${provider.name}/${defaultModel}` : defaultModel;
  return {
    ...DEFAULT_LLM_FORM,
    name: defaultName,
    provider_id: provider?.id || "",
    model: defaultModel,
  };
}

export function llmPayload(form) {
  return {
    name: form.name.trim(),
    provider_id: Number(form.provider_id),
    model: form.model.trim(),
    max_tokens: Number(form.max_tokens),
    max_context_tokens: form.max_context_auto ? null : Number(form.max_context_tokens),
    temperature: form.use_temperature ? Number(form.temperature) : null,
    use_vision: form.use_vision,
    force_tool_choice: form.force_tool_choice,
    reasoning_effort: form.reasoning_effort || null,
  };
}
