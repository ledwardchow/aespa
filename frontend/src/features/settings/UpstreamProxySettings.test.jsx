import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import { UpstreamProxySettings } from "./UpstreamProxySettings.jsx";

vi.mock("../../shared/api/settings.js");

const config = {
  scanner_proxy_url: "http://scanner-proxy.local:8080",
  llm_proxy_url: "http://llm-proxy.local:8081",
  scanner_ca_bundle_path: null,
  llm_ca_bundle_path: null,
  proxy_scanner: true,
  proxy_llm: true,
};

beforeEach(() => {
  settingsApi.getUpstreamProxy.mockResolvedValue(config);
  settingsApi.upsertUpstreamProxy.mockImplementation(async (payload) => payload);
});

test("saves independent proxy URLs for testing and LLM traffic", async () => {
  render(<UpstreamProxySettings />);

  const scannerUrl = await screen.findByLabelText("Testing traffic proxy URL");
  const llmUrl = screen.getByLabelText("LLM traffic proxy URL");
  fireEvent.change(scannerUrl, { target: { value: "http://testing.local:9000" } });
  fireEvent.change(llmUrl, { target: { value: "http://models.local:9001" } });
  fireEvent.click(screen.getByRole("button", { name: "Save" }));

  await waitFor(() =>
    expect(settingsApi.upsertUpstreamProxy).toHaveBeenCalledWith({
      scanner_proxy_url: "http://testing.local:9000",
      llm_proxy_url: "http://models.local:9001",
      scanner_ca_bundle_path: null,
      llm_ca_bundle_path: null,
      proxy_scanner: true,
      proxy_llm: true,
    }),
  );
});

test("keeps a configured URL when its traffic toggle is disabled", async () => {
  render(<UpstreamProxySettings />);

  const scannerToggle = await screen.findByRole("checkbox", {
    name: "Send target requests through an upstream proxy",
  });
  fireEvent.click(scannerToggle);
  fireEvent.click(screen.getByRole("button", { name: "Save" }));

  await waitFor(() =>
    expect(settingsApi.upsertUpstreamProxy).toHaveBeenCalledWith({
      ...config,
      proxy_scanner: false,
    }),
  );
});

test("saves separate CA bundle paths", async () => {
  render(<UpstreamProxySettings />);
  const scannerPath = await screen.findByLabelText("Testing traffic CA bundle path");
  const llmPath = screen.getByLabelText("Application traffic CA bundle path");
  fireEvent.change(scannerPath, { target: { value: " /etc/ssl/scanner.pem " } });
  fireEvent.change(llmPath, { target: { value: "/etc/ssl/llm.pem" } });
  fireEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() =>
    expect(settingsApi.upsertUpstreamProxy).toHaveBeenCalledWith({
      ...config,
      scanner_ca_bundle_path: "/etc/ssl/scanner.pem",
      llm_ca_bundle_path: "/etc/ssl/llm.pem",
    }),
  );
});
