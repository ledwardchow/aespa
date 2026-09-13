import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { ActivityAgents } from "./ActivityAgents.jsx";
import { WebRunActivityTab } from "./WebRunActivityTab.jsx";

vi.mock("./WebRunChat.jsx", () => ({
  useWebRunChat: () => ({
    collapsedAgentIds: new Set(["alice", "specialist"]),
    toggleAgentId: vi.fn(),
    aliceChats: [],
    activeAliceTabId: "default",
    setActiveAliceTabId: vi.fn(),
    deleteAliceTab: vi.fn(),
    createAliceTab: vi.fn(),
    aliceChatHeight: 300,
    aliceMessages: [],
    aliceExpandedThinkIds: new Set(),
    setAliceExpandedThinkIds: vi.fn(),
    aliceThinkingTabId: null,
    aliceIsThinking: false,
    startAliceResize: vi.fn(),
    aliceInputText: "",
    handleAliceSend: vi.fn(),
    setAliceInputText: vi.fn(),
    handleAliceStop: vi.fn(),
    submitAliceDirective: vi.fn(),
  }),
}));

const agents = [
  {
    id: "specialist-sqli-1",
    role: "Specialist",
    status: "complete",
    currentTask: "Checked the account query",
  },
  {
    id: "deep-worker-1-task-41",
    role: "IDOR on /accounts/{id}",
    status: "active",
    currentTask: "Testing account access",
    stepHistory: [
      {
        ts: "10:00:00",
        step: 7,
        description: "Compare the account response with another signed-in user.",
        tool_name: "http_request",
        method: "GET",
        url: "https://target.test/accounts/1",
        observation: "The first user received account details.",
      },
    ],
  },
  {
    id: "deep-worker-2-task-40",
    role: "Cross-origin policy review",
    status: "complete",
    currentTask: "Checked CORS policy",
  },
];

test("groups Deep tasks and shows only currently running worker status in Agents", () => {
  render(
    <ActivityAgents
      runId={1}
      agents={agents}
      run={{ coverage_mode: "deep", status: "complete" }}
      thinkingStatus={{ status: "running" }}
      activityLog={[]}
    />,
  );

  expect(screen.getAllByText("Deep Attack Workers")).toHaveLength(1);
  expect(screen.getByText("1 running, 1 complete")).toBeTruthy();
  expect(screen.getByText("IDOR on /accounts/{id}")).toBeTruthy();
  expect(screen.getByText("Testing account access")).toBeTruthy();
  expect(screen.queryByText("https://target.test/accounts/1")).toBeNull();
});

test("shows specialist and Deep task detail together in Workers", () => {
  render(
    <WebRunActivityTab
      activeTab="activity"
      runId={1}
      run={{ coverage_mode: "deep" }}
      thinkingStatus={{ status: "running" }}
      activityLog={[]}
      agents={agents}
      tokenUsage={null}
      sitePlanData={null}
      onClearLog={vi.fn()}
      onError={vi.fn()}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: /Workers/ }));

  expect(screen.getByText("Specialist sqli #1")).toBeTruthy();
  expect(screen.getByText("IDOR on /accounts/{id}")).toBeTruthy();
  expect(screen.getByText("Testing account access")).toBeTruthy();
  expect(
    screen.getByText("Step 7: Compare the account response with another signed-in user."),
  ).toBeTruthy();
  expect(screen.getByText(/Observed: The first user received account details/)).toBeTruthy();
});
