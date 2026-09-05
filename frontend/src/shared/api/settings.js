import { req } from "./request.ts";

export const getLLMConfig = () => req("/api/settings/llm");

export const upsertLLMConfig = (b) => req("/api/settings/llm", { method: "PUT", body: b });

export const listLLMModels = () => req("/api/settings/llm/model-configs");

export const createLLMModel = (b) =>
  req("/api/settings/llm/model-configs", { method: "POST", body: b });

export const updateLLMModel = (id, b) =>
  req(`/api/settings/llm/model-configs/${id}`, { method: "PUT", body: b });

export const deleteLLMModel = (id) =>
  req(`/api/settings/llm/model-configs/${id}`, { method: "DELETE" });

export const listLLMProfiles = () => req("/api/settings/llm/profiles");

export const createLLMProfile = (b) =>
  req("/api/settings/llm/profiles", { method: "POST", body: b });

export const updateLLMProfile = (id, b) =>
  req(`/api/settings/llm/profiles/${id}`, { method: "PUT", body: b });

export const activateLLMProfile = (id) =>
  req(`/api/settings/llm/profiles/${id}/activate`, { method: "POST" });

export const deleteLLMProfile = (id) =>
  req(`/api/settings/llm/profiles/${id}`, { method: "DELETE" });

export const listLLMProviders = () => req("/api/settings/llm/providers");

export const createLLMProvider = (b) =>
  req("/api/settings/llm/providers", { method: "POST", body: b });

export const updateLLMProvider = (id, b) =>
  req(`/api/settings/llm/providers/${id}`, { method: "PUT", body: b });

export const deleteLLMProvider = (id) =>
  req(`/api/settings/llm/providers/${id}`, { method: "DELETE" });

export const exportLLMConfig = () => req("/api/settings/llm/export");

export const importLLMConfig = (b) => req("/api/settings/llm/import", { method: "POST", body: b });

export const getDefaultModels = () => req("/api/settings/llm/models");

export const discoverModels = (b) =>
  req("/api/settings/llm/discover-models", { method: "POST", body: b });

export const discoverModelOptions = (b) =>
  req("/api/settings/llm/discover-model-options", { method: "POST", body: b });

export const getCodexStatus = () => req("/api/settings/llm/codex/status");

export const saveCodexConfig = (b) =>
  req("/api/settings/llm/codex/config", { method: "PUT", body: b });

export const startCodexLogin = () => req("/api/settings/llm/codex/login", { method: "POST" });

export const cancelCodexLogin = (b) =>
  req("/api/settings/llm/codex/login/cancel", { method: "POST", body: b });

export const logoutCodex = () => req("/api/settings/llm/codex/logout", { method: "POST" });

export const listCopilotAccounts = () => req("/api/settings/llm/copilot/accounts");

export const startCopilotLogin = () => req("/api/settings/llm/copilot/login", { method: "POST" });

export const getCopilotLogin = (id) => req(`/api/settings/llm/copilot/login/${id}`);

export const cancelCopilotLogin = (id) =>
  req(`/api/settings/llm/copilot/login/${id}/cancel`, { method: "POST" });

export const getScannerPolicy = () => req("/api/settings/scanner-policy");

export const upsertScannerPolicy = (b) =>
  req("/api/settings/scanner-policy", { method: "PUT", body: b });

export const getCodeExecutionConfig = () => req("/api/settings/code-execution");

export const upsertCodeExecutionConfig = (b) =>
  req("/api/settings/code-execution", { method: "PUT", body: b });

export const getCodeExecutionStatus = () => req("/api/settings/code-execution/status");

export const getCrawlerConfig = () => req("/api/settings/crawler-config");

export const upsertCrawlerConfig = (b) =>
  req("/api/settings/crawler-config", { method: "PUT", body: b });

export const getComponentMapperConfig = () => req("/api/settings/component-mapper-config");

export const upsertComponentMapperConfig = (b) =>
  req("/api/settings/component-mapper-config", { method: "PUT", body: b });

export const getBurpRestApiConfig = () => req("/api/settings/burp-rest-api");

export const upsertBurpRestApiConfig = (b) =>
  req("/api/settings/burp-rest-api", { method: "PUT", body: b });

export const testBurpConnection = () =>
  req("/api/settings/burp-rest-api/test-connection", { method: "POST" });

export const getUpstreamProxy = () => req("/api/settings/upstream-proxy");

export const upsertUpstreamProxy = (b) =>
  req("/api/settings/upstream-proxy", { method: "PUT", body: b });

export const getSpecialistAgentConfig = () => req("/api/settings/specialist-agent-config");

export const upsertSpecialistAgentConfig = (b) =>
  req("/api/settings/specialist-agent-config", { method: "PUT", body: b });

export const getAdversarialValidatorConfig = () =>
  req("/api/settings/adversarial-validator-config");

export const upsertAdversarialValidatorConfig = (b) =>
  req("/api/settings/adversarial-validator-config", { method: "PUT", body: b });

export const getGlobalHttpHeader = () => req("/api/settings/global-http-header");

export const upsertGlobalHttpHeader = (b) =>
  req("/api/settings/global-http-header", { method: "PUT", body: b });

export const getReportingDebugConfig = () => req("/api/settings/reporting-debug");

export const upsertReportingDebugConfig = (b) =>
  req("/api/settings/reporting-debug", { method: "PUT", body: b });

export const getBrowserDebugConfig = () => req("/api/settings/browser-debug");

export const upsertBrowserDebugConfig = (b) =>
  req("/api/settings/browser-debug", { method: "PUT", body: b });

export const getCloudflareAccessConfig = () => req("/api/settings/cloudflare-access");

export const upsertCloudflareAccessConfig = (b) =>
  req("/api/settings/cloudflare-access", { method: "PUT", body: b });

export const getReportingDebugPrompt = (key) =>
  req(`/api/reporting-debug/prompt${key ? `?key=${encodeURIComponent(key)}` : ""}`);

export const listReportingDebugPrompts = () => req("/api/reporting-debug/prompts");

export const saveReportingDebugPrompt = (key, b) =>
  req(`/api/reporting-debug/prompt?key=${encodeURIComponent(key)}`, { method: "PUT", body: b });

export const resetReportingDebugPrompt = (key) =>
  req(`/api/reporting-debug/prompt/reset?key=${encodeURIComponent(key)}`, { method: "POST" });

export const listReportingPromptVersions = (key) =>
  req(`/api/reporting-debug/prompt-versions?key=${encodeURIComponent(key)}`);

export const createReportingPromptVersion = (b) =>
  req("/api/reporting-debug/prompt-versions", { method: "POST", body: b });

export const updateReportingPromptVersion = (id, b) =>
  req(`/api/reporting-debug/prompt-versions/${id}`, { method: "PUT", body: b });

export const deleteReportingPromptVersion = (id) =>
  req(`/api/reporting-debug/prompt-versions/${id}`, { method: "DELETE" });

export const listReportingCaptures = () => req("/api/reporting-debug/captures");

export const getReportingCapture = (id) => req(`/api/reporting-debug/captures/${id}`);

export const replayReportingCapture = (id, b = {}) =>
  req(`/api/reporting-debug/captures/${id}/replay`, { method: "POST", body: b });

export const getReportingReplay = (id) => req(`/api/reporting-debug/replays/${id}`);

export const listReportingReplays = () => req("/api/reporting-debug/replays");

export const getVersion = () => req("/api/version");
