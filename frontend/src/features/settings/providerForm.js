import { PROVIDER_MODEL_PLACEHOLDERS, DEFAULT_PROVIDER_FORM } from "./providerMetadata.js";

import {
  bedrockBaseUrl,
  bedrockRegionFromBaseUrl,
  isBedrockProvider,
} from "../../shared/lib/bedrock.js";

export function providerToForm(provider) {
  return provider
    ? {
        name: provider.name || "",
        api_format: provider.api_format || "anthropic",
        base_url: provider.base_url || "",
        region: isBedrockProvider(provider.api_format)
          ? bedrockRegionFromBaseUrl(provider.api_format, provider.base_url)
          : "",
        username: provider.username || "",
        project_id: provider.project_id || "",
        location: provider.location || "",
        models: (provider.models || []).join("\n"),
        model_capabilities: provider.model_capabilities || {},
        api_key: "",
        has_api_key: provider.has_api_key ?? false,
        clear_api_key: false,
      }
    : {
        ...DEFAULT_PROVIDER_FORM,
        has_api_key: false,
        clear_api_key: false,
      };
}

export function providerPayload(form) {
  const usesCliCredentials = [
    "factory_droid",
    "openai_codex",
    "google_antigravity",
    "google_vertex",
  ].includes(form.api_format);
  let apiKeyPayload = null;
  if (usesCliCredentials) {
    apiKeyPayload = "";
  } else if (form.clear_api_key) {
    apiKeyPayload = "";
  } else if (form.api_key.trim()) {
    apiKeyPayload = form.api_key.trim();
  } else {
    apiKeyPayload = null;
  }
  const modelText =
    form.models.trim() ||
    (form.api_format === "openai_compatible"
      ? ""
      : PROVIDER_MODEL_PLACEHOLDERS[form.api_format] || "");
  const baseUrl = isBedrockProvider(form.api_format)
    ? bedrockBaseUrl(form.api_format, form.region)
    : form.base_url.trim() || null;
  return {
    name: form.name.trim(),
    api_format: form.api_format,
    base_url: usesCliCredentials ? null : baseUrl,
    username: form.api_format === "github_copilot" ? form.username.trim() || null : null,
    project_id: ["bedrock_mantle", "google_vertex"].includes(form.api_format)
      ? form.project_id.trim() || null
      : null,
    location: form.api_format === "google_vertex" ? form.location.trim() || "global" : null,
    models: modelText
      .split(/\r?\n|,/)
      .map((m) => m.trim())
      .filter(Boolean),
    api_key: apiKeyPayload,
    model_capabilities: form.model_capabilities || {},
  };
}
