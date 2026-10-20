import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import * as extensionsApi from "../../shared/api/extensions.js";
import * as integrationApi from "../../shared/api/integrationApi.js";
import { ApiDefinition, typeLabel } from "./ApiDefinition.jsx";
import { ApiTokens } from "./ApiTokens.jsx";
import { ExtensionSettingsPage } from "./ExtensionSettingsPage.jsx";

vi.mock("../../shared/api/extensions.js");
vi.mock("../../shared/api/integrationApi.js");

const definition = {
  openapi: "3.1.0",
  info: { title: "AESPA API", version: "1.0.0", description: "Use a token." },
  servers: [{ url: "/extension/aespa.api" }],
  paths: {
    "/v1/web/scans": {
      post: {
        tags: ["Web scans"],
        summary: "Create and start a web scan",
        operationId: "createWebScan",
        "x-aespa-scopes": ["web"],
        parameters: [
          {
            name: "Idempotency-Key",
            in: "header",
            required: false,
            schema: { anyOf: [{ type: "string" }, { type: "null" }] },
            description: "Any unique value.",
          },
        ],
        requestBody: {
          content: {
            "application/json": { schema: { $ref: "#/components/schemas/WebScanCreate" } },
          },
        },
        responses: {
          201: {
            description: "Created",
            content: {
              "application/json": { schema: { $ref: "#/components/schemas/ScanStatus" } },
            },
          },
        },
      },
    },
  },
  webhooks: {
    "scan.completed": {
      post: { summary: "scan.completed", description: "The scan finished.", responses: {} },
    },
  },
  components: {
    schemas: {
      WebScanCreate: {
        type: "object",
        required: ["site_id"],
        properties: {
          site_id: { type: "integer", description: "An existing Site." },
          password: { type: "string", writeOnly: true },
          site: {
            anyOf: [{ $ref: "#/components/schemas/SiteIn" }, { type: "null" }],
            description: "A Site to create.",
          },
        },
      },
      SiteIn: {
        type: "object",
        description: "Everything AESPA needs to test a web site.",
        properties: {
          base_url: { type: "string", description: "Where the site starts." },
          credentials: {
            type: "array",
            items: { $ref: "#/components/schemas/CredentialCreate" },
          },
        },
      },
      CredentialCreate: {
        type: "object",
        properties: {
          username: { type: "string", description: "Account name." },
          totp_seed: { type: "string", writeOnly: true },
        },
      },
      ScanStatus: { type: "object", properties: {} },
    },
  },
};

const apiExtension = {
  id: "aespa.api",
  name: "API",
  version: "1.0.0",
  capabilities: ["api.routes", "core.sast_runs", "core.web_runs"],
  enabled: true,
  status: "loaded",
  settings: {},
  settings_fields: [{ key: "send_callbacks", label: "Send callbacks", type: "boolean" }],
  openapi_url: "/api/extensions/aespa.api/openapi.json",
};

beforeEach(() => {
  vi.clearAllMocks();
  integrationApi.getApiDefinition.mockResolvedValue(definition);
  integrationApi.listApiTokens.mockResolvedValue([]);
  integrationApi.listFailedDeliveries.mockResolvedValue([]);
});

test("labels schema types plainly", () => {
  expect(typeLabel({ anyOf: [{ type: "string" }, { type: "null" }] })).toBe("string");
  expect(typeLabel({ type: "array", items: { $ref: "#/components/schemas/Finding" } })).toBe(
    "Finding[]",
  );
  expect(typeLabel({ type: "string", format: "binary" })).toBe("file");
});

test("shows the base URL, endpoints, fields, and callbacks", async () => {
  const user = userEvent.setup();
  render(<ApiDefinition extension={apiExtension} />);

  expect(await screen.findByDisplayValue(/\/extension\/aespa\.api$/)).toBeTruthy();
  expect(integrationApi.getApiDefinition).toHaveBeenCalledWith(apiExtension.openapi_url);
  expect(screen.getByRole("button", { name: "Download OpenAPI file" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "Open file" }).getAttribute("href")).toBe(
    apiExtension.openapi_url,
  );
  expect(screen.getByText("Web scans")).toBeTruthy();
  expect(screen.getByText("Permission: Web scans")).toBeTruthy();
  expect(screen.getByText("Callback events")).toBeTruthy();

  await user.click(screen.getByText("Create and start a web scan"));
  const details = screen.getByText("Create and start a web scan").closest("details");
  expect(within(details).getByText("Idempotency-Key")).toBeTruthy();
  expect(within(details).getByText("An existing Site.")).toBeTruthy();
  expect(within(details).getByText(/never returned/)).toBeTruthy();
  expect(within(details).getByText("ScanStatus")).toBeTruthy();
});

test("settings page shows the definition only for extensions that publish one", async () => {
  extensionsApi.listExtensions.mockResolvedValue([
    apiExtension,
    { ...apiExtension, id: "other", name: "Other", openapi_url: null, settings_fields: [] },
  ]);
  const { unmount } = render(<ExtensionSettingsPage extensionId="aespa.api" />);
  expect(await screen.findByText("API definition")).toBeTruthy();
  expect(await screen.findByText("API tokens")).toBeTruthy();
  unmount();

  render(<ExtensionSettingsPage extensionId="other" />);
  expect(await screen.findByText("Other settings")).toBeTruthy();
  expect(screen.queryByText("API definition")).toBeNull();
  expect(screen.queryByText("API tokens")).toBeNull();
});

test("a new token is created from the New token form and shown in its card", async () => {
  const user = userEvent.setup();
  integrationApi.createApiToken.mockResolvedValue({
    id: 1,
    name: "CI",
    token: "aespa_example",
    webhook_secret: null,
  });
  render(<ApiTokens />);
  expect(await screen.findByText(/No tokens yet/)).toBeTruthy();

  integrationApi.listApiTokens.mockResolvedValue([{ ...savedToken, id: 1, can_show_token: true }]);
  await user.click(screen.getByRole("button", { name: "New token" }));
  await user.type(screen.getByLabelText("Name"), "CI");
  await user.click(screen.getByLabelText("Web scans"));
  await user.click(screen.getByLabelText("All scans in AESPA"));
  await user.click(screen.getByRole("button", { name: "Create token" }));

  expect(integrationApi.createApiToken).toHaveBeenCalledWith({
    name: "CI",
    scopes: ["sast", "web"],
    scan_access: "all",
    webhook_url: null,
  });
  expect(await screen.findByDisplayValue("aespa_example")).toBeTruthy();
  expect(screen.getByText(/You can show the token again later/)).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Create token" })).toBeNull();
  expect(integrationApi.listApiTokens).toHaveBeenCalledTimes(2);
});

const savedToken = {
  id: 7,
  name: "CI",
  prefix: "aespa_abc123",
  scopes: ["sast"],
  scan_access: "own",
  active: true,
  can_show_token: true,
  webhook_url: null,
  has_webhook_secret: false,
  last_used_at: null,
};

test("a saved token can be shown and edited", async () => {
  const user = userEvent.setup();
  integrationApi.listApiTokens.mockResolvedValue([savedToken]);
  integrationApi.showApiToken.mockResolvedValue({ token: "aespa_saved" });
  integrationApi.updateApiToken.mockResolvedValue({ ...savedToken, webhook_secret: null });
  render(<ApiTokens />);
  const card = await screen.findByRole("article", { name: "CI" });
  expect(within(card).getByText("Only scans it creates")).toBeTruthy();

  await user.click(within(card).getByRole("button", { name: "Show token" }));
  expect(await within(card).findByDisplayValue("aespa_saved")).toBeTruthy();
  expect(integrationApi.showApiToken).toHaveBeenCalledWith(7);

  await user.click(within(card).getByRole("button", { name: "Edit" }));
  const name = within(card).getByLabelText("Name");
  await user.clear(name);
  await user.type(name, "CI pipeline");
  await user.click(within(card).getByLabelText("Web scans"));
  await user.click(within(card).getByLabelText("All scans in AESPA"));
  await user.click(within(card).getByRole("button", { name: "Save" }));
  expect(integrationApi.updateApiToken).toHaveBeenCalledWith(7, {
    name: "CI pipeline",
    scopes: ["sast", "web"],
    scan_access: "all",
    webhook_url: "",
  });
});

test("a token can be turned off and on", async () => {
  const user = userEvent.setup();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  integrationApi.listApiTokens.mockResolvedValue([savedToken]);
  integrationApi.deactivateApiToken.mockResolvedValue({ ...savedToken, active: false });
  render(<ApiTokens />);
  const card = await screen.findByRole("article", { name: "CI" });

  integrationApi.listApiTokens.mockResolvedValue([{ ...savedToken, active: false }]);
  await user.click(within(card).getByRole("button", { name: "Edit" }));
  await user.click(within(card).getByRole("button", { name: "Turn off" }));
  expect(integrationApi.deactivateApiToken).toHaveBeenCalledWith(7);
  expect(await within(card).findByText("Off")).toBeTruthy();

  await user.click(within(card).getByRole("button", { name: "Turn on" }));
  expect(integrationApi.reactivateApiToken).toHaveBeenCalledWith(7);
});

test("a token saved before tokens were kept can be given a new value", async () => {
  const user = userEvent.setup();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  integrationApi.listApiTokens.mockResolvedValue([{ ...savedToken, can_show_token: false }]);
  integrationApi.newApiTokenValue.mockResolvedValue({ ...savedToken, token: "aespa_fresh" });
  render(<ApiTokens />);
  const card = await screen.findByRole("article", { name: "CI" });
  expect(within(card).queryByRole("button", { name: "Show token" })).toBeNull();
  expect(within(card).getByText(/created before AESPA kept tokens/)).toBeTruthy();

  await user.click(within(card).getByRole("button", { name: "Edit" }));
  await user.click(within(card).getByRole("button", { name: "New token value" }));
  expect(integrationApi.newApiTokenValue).toHaveBeenCalledWith(7);
  expect(await within(card).findByDisplayValue("aespa_fresh")).toBeTruthy();
});

test("nested objects open in place and link to their Data objects entry", async () => {
  const user = userEvent.setup();
  window.Element.prototype.scrollIntoView = vi.fn();
  render(<ApiDefinition extension={apiExtension} />);
  await screen.findByText("Create and start a web scan");
  await user.click(screen.getByText("Create and start a web scan"));
  const operation = screen.getByText("Create and start a web scan").closest("details");

  const siteRow = within(operation).getByText("site").closest("tr");
  await user.click(within(siteRow).getByRole("button", { name: "Show fields" }));
  expect(within(operation).getByText("Where the site starts.")).toBeTruthy();

  const credentialsRow = within(operation).getByText("credentials").closest("tr");
  expect(credentialsRow.textContent).toContain("CredentialCreate[]");
  await user.click(within(credentialsRow).getByRole("button", { name: "Show fields" }));
  expect(within(operation).getByText("Account name.")).toBeTruthy();

  const entry = document.getElementById("api-object-CredentialCreate");
  expect(entry.open).toBe(false);
  await user.click(within(credentialsRow).getByRole("button", { name: "CredentialCreate" }));
  expect(entry.open).toBe(true);
  expect(entry.scrollIntoView).toHaveBeenCalled();
  expect(within(entry).getByText("totp_seed")).toBeTruthy();

  expect(screen.getByText("Data objects")).toBeTruthy();
  expect(document.getElementById("api-object-SiteIn")).toBeTruthy();
  expect(document.getElementById("api-object-WebScanCreate")).toBeTruthy();
});
