import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as settingsApi from "../../shared/api/settings.js";
import { CodeExecutionSettings } from "./CodeExecutionSettings.jsx";

vi.mock("../../shared/api/settings.js");

const config = {
  enabled: true,
  image_ref: "ledwardchow/aespa-python-executor:0.1",
  allowed_roles: ["alice", "specialist", "test_lead"],
  timeout_s: 30,
  memory_mb: 256,
  cpu_cores: 0.5,
  pids_limit: 32,
  workspace_mb: 16,
  output_limit_bytes: 65536,
  artifact_limit_bytes: 10485760,
  max_requests_per_execution: 20,
  max_concurrent_requests: 5,
  max_concurrent_executions: 2,
  retain_redacted_source: true,
};

beforeEach(() => {
  settingsApi.getCodeExecutionConfig.mockResolvedValue(config);
});

test("shows Docker service guidance without image build instructions", async () => {
  settingsApi.getCodeExecutionStatus.mockResolvedValue({
    available: false,
    docker_installed: true,
    docker_available: false,
    image_present: false,
    message:
      "Docker is installed, but its service is not running or cannot be reached. Start Docker and try again.",
  });

  render(<CodeExecutionSettings />);

  expect(await screen.findByText(/Docker is installed, but its service is not running/)).toBeTruthy();
  expect(screen.queryByText(/Build it with:/)).toBeNull();
});

test("shows image build instructions when Docker is available", async () => {
  settingsApi.getCodeExecutionStatus.mockResolvedValue({
    available: false,
    docker_installed: true,
    docker_available: true,
    image_present: false,
    message: "Sandbox image is not installed.",
  });

  render(<CodeExecutionSettings />);

  expect(await screen.findByText(/Sandbox image is not installed/)).toBeTruthy();
  expect(screen.getByText(/docker build -t/)).toBeTruthy();
});
