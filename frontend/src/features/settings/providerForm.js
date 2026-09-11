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
        models: (provider.models || []).join("\n"),
        model_capabilities: provider.model_capabilities || {},
        api_key: "",
        has_api_key: provider.has_api_key ?? false,
        clear_api_key: false,
        max_tpm: provider.max_tpm != null ? provider.max_tpm : "",
        max_rpm: provider.max_rpm != null ? provider.max_rpm : "",
      }
    : {
        ...DEFAULT_PROVIDER_FORM,
        has_api_key: false,
        clear_api_key: false,
      };
}

export function providerPayload(form) {
  const usesCliCredentials = ["factory_droid", "openai_codex", "google_antigravity"].includes(
    form.api_format,
  );
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
    project_id: form.api_format === "bedrock_mantle" ? form.project_id.trim() || null : null,
    models: modelText
      .split(/\r?\n|,/)
      .map((m) => m.trim())
      .filter(Boolean),
    api_key: apiKeyPayload,
    max_tpm: form.max_tpm !== "" ? Number(form.max_tpm) : null,
    max_rpm: form.max_rpm !== "" ? Number(form.max_rpm) : null,
    model_capabilities: form.model_capabilities || {},
  };
}
