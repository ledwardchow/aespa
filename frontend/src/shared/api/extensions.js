import { req } from "./request.ts";

export const listExtensions = () => req("/api/extensions");

export const listSourceProviders = () => req("/api/extensions/source-providers");

export const setExtensionEnabled = (extensionId, enabled) =>
  req(`/api/extensions/${encodeURIComponent(extensionId)}/enabled`, {
    method: "PUT",
    body: { enabled },
  });

export const updateExtensionSettings = (extensionId, settings) =>
  req(`/api/extensions/${encodeURIComponent(extensionId)}/settings`, {
    method: "PATCH",
    body: { settings },
  });

export const checkExtension = (extensionId) =>
  req(`/api/extensions/${encodeURIComponent(extensionId)}/check`, { method: "POST" });
