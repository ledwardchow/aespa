import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { req } from "../../shared/api/request.ts";
import { BenchmarkPublishing } from "./BenchmarkPublishing.jsx";

vi.mock("../../shared/api/request.ts", () => ({ req: vi.fn() }));
const BASE = "/extension/aespa.benchmarking";
beforeEach(() => {
  vi.clearAllMocks();
  req.mockImplementation(async (url) =>
    url.endsWith("/token")
      ? { service_token: "fixture-secret" }
      : { site_url: "https://example.chatgpt.site", token_saved: true, upload_token_saved: true },
  );
});

test("extension settings reveals the saved token only when requested and can hide it", async () => {
  const user = userEvent.setup();
  render(<BenchmarkPublishing mode="settings" />);
  const show = await screen.findByRole("button", { name: "Show saved token" });
  expect(req).toHaveBeenCalledTimes(1);
  expect(screen.queryByDisplayValue("fixture-secret")).toBeNull();
  await user.click(show);
  expect(req).toHaveBeenCalledWith(`${BASE}/publishing/token`, { method: "POST" });
  expect(await screen.findByLabelText("Saved service token")).toHaveProperty(
    "value",
    "fixture-secret",
  );
  await user.click(screen.getByRole("button", { name: "Hide saved token" }));
  expect(screen.queryByDisplayValue("fixture-secret")).toBeNull();
});

test("saving settings preserves the existing token when its field is blank", async () => {
  const user = userEvent.setup();
  render(<BenchmarkPublishing mode="settings" />);
  await screen.findByRole("button", { name: "Show saved token" });
  await user.click(screen.getByRole("button", { name: "Save connection" }));
  await waitFor(() =>
    expect(req).toHaveBeenCalledWith(`${BASE}/publishing`, {
      method: "PUT",
      body: { site_url: "https://example.chatgpt.site" },
    }),
  );
  expect(screen.queryByRole("button", { name: "Publish results" })).toBeNull();
});

test("benchmark lab provides publishing and links to extension settings", async () => {
  render(<BenchmarkPublishing />);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Publish results" }).disabled).toBe(false),
  );
  expect(screen.getByRole("link", { name: "Connection settings" }).getAttribute("href")).toBe(
    "#/extensions/aespa.benchmarking/settings",
  );
  expect(screen.queryByLabelText("Private Sites service token")).toBeNull();
});

test("publishing stays disabled until an upload token has been saved", async () => {
  req.mockResolvedValue({
    site_url: "https://example.chatgpt.site",
    token_saved: true,
    upload_token_saved: false,
  });
  render(<BenchmarkPublishing />);
  await screen.findByRole("link", { name: "Connection settings" });
  await waitFor(() => expect(req).toHaveBeenCalled());
  expect(screen.getByRole("button", { name: "Publish results" }).disabled).toBe(true);
});

test("settings save both credentials and keep them out of the fields after saving", async () => {
  const user = userEvent.setup();
  render(<BenchmarkPublishing mode="settings" />);
  await screen.findByRole("button", { name: "Show saved token" });
  await user.type(screen.getByLabelText("Private Sites service token"), "new-service");
  await user.type(screen.getByLabelText("Upload token"), "aespa_upload_" + "a".repeat(64));
  await user.click(screen.getByRole("button", { name: "Save connection" }));
  await waitFor(() =>
    expect(req).toHaveBeenCalledWith(`${BASE}/publishing`, {
      method: "PUT",
      body: {
        site_url: "https://example.chatgpt.site",
        service_token: "new-service",
        upload_token: "aespa_upload_" + "a".repeat(64),
      },
    }),
  );
  expect(screen.getByLabelText("Upload token").value).toBe("");
  expect(screen.getByLabelText("Private Sites service token").value).toBe("");
});
