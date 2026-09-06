import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import * as applicationsApi from "../../shared/api/applications.js";
import { useCampaign } from "./useCampaign.js";

vi.mock("../../shared/api/applications.js", () => ({
  getCampaign: vi.fn(),
  startCampaign: vi.fn(),
  stopCampaign: vi.fn(),
  resumeCampaign: vi.fn(),
  resumeCampaignSource: vi.fn(),
  resumeCampaignTarget: vi.fn(),
  rebuildCampaignConnections: vi.fn(),
  continueCampaign: vi.fn(),
}));

afterEach(() => {
  vi.useRealTimers();
});

test("refreshes an interrupted snapshot when the campaign resumes elsewhere", async () => {
  vi.useFakeTimers();
  applicationsApi.getCampaign
    .mockResolvedValueOnce({
      id: 218,
      application_id: 1,
      status: "interrupted",
      source_members: [{ id: 1, status: "completed", run_status: "completed" }],
      target_members: [],
    })
    .mockResolvedValue({
      id: 218,
      application_id: 1,
      status: "correlating",
      source_members: [{ id: 1, status: "completed", run_status: "completed" }],
      target_members: [],
    });

  const { result, unmount } = renderHook(() => useCampaign(1, 218));
  await act(async () => {});
  expect(result.current.campaign.status).toBe("interrupted");

  await act(async () => {
    await vi.advanceTimersByTimeAsync(4000);
  });
  expect(result.current.campaign.status).toBe("correlating");
  unmount();
});

test("clears a request error after a later refresh succeeds", async () => {
  applicationsApi.getCampaign
    .mockRejectedValueOnce(new Error("Scan interrupted"))
    .mockResolvedValue({
      id: 218,
      application_id: 1,
      status: "correlating",
      source_members: [],
      target_members: [],
    });

  const { result } = renderHook(() => useCampaign(1, 218));
  await waitFor(() => expect(result.current.error).toBe("Scan interrupted"));

  await act(async () => {
    await result.current.load();
  });
  expect(result.current.error).toBeNull();
  expect(result.current.campaign.status).toBe("correlating");
});
