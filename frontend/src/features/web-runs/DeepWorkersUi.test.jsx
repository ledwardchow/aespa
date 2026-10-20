import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { ActivityAgents } from "./ActivityAgents.jsx";
import { WebRunActivityTab } from "./WebRunActivityTab.jsx";
import * as webRunsApi from "../../shared/api/webRuns.js";

vi.mock("../../shared/api/webRuns.js", () => ({ getDeepQueue: vi.fn() }));

const chatState = vi.hoisted(() => ({
  aliceChats: [],
  collapseAgentId: vi.fn(),
}));

webRunsApi.getDeepQueue.mockResolvedValue({
  total: 1,
  counts: { running: 1 },
  planning: { total: 1, complete: 1 },
  tasks: [
    {
      id: 41,
      task_kind: "operation",
      status: "running",
      title: "Test GET /accounts/{id}",
      http_method: "GET",
      target_url: "https://target.test/accounts/{id}",
      route_template: "https://target.test/accounts/{id}",
      priority: 9,
      checks: [],
      inputs: ["id"],
      identities: ["user_a_vs_user_b"],
      variants: [
        {
          id: 9,
          kind: "planned",
          strategy: "idor",
          status: "running",
          worker_id: "deep-worker-1-task-41-variant-9",
          assigned_purpose: "Compare object access across two users.",
          current_purpose: "Confirm the ownership difference.",
          pivot_history: [{ at: "2026-09-13T10:00:00Z", to: "Confirm the ownership difference." }],
        },
      ],
    },
  ],
});

vi.mock("./WebRunChat.jsx", () => ({
  useWebRunChat: () => ({
    collapsedAgentIds: new Set(["alice", "specialist"]),
    toggleAgentId: vi.fn(),
    collapseAgentId: chatState.collapseAgentId,
    aliceChats: chatState.aliceChats,
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

beforeEach(() => {
  chatState.aliceChats = [];
  chatState.collapseAgentId.mockClear();
});

const agents = [
  {
    id: "specialist-sqli-1",
    role: "Specialist",
    status: "complete",
    currentTask: "Checked the account query",
  },
  {
    id: "deep-worker-1-task-41-variant-9",
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

test("shows Deep worker traces inside Work Queue without a separate Workers tab", async () => {
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

  expect(screen.queryByRole("button", { name: /Workers/ })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Work Queue" }));
  const taskToggle = await screen.findByRole("button", { expanded: false });
  fireEvent.click(taskToggle);

  expect(screen.getByText("Worker trace")).toBeTruthy();
  expect(screen.getByText("Testing account access")).toBeTruthy();
  expect(
    screen.getByText("Step 7: Compare the account response with another signed-in user."),
  ).toBeTruthy();
  expect(screen.getByText(/Observed: The first user received account details/)).toBeTruthy();
  expect(
    screen.getAllByText(/Pivoted to: Confirm the ownership difference\./).length,
  ).toBeGreaterThan(0);
});

test("opens refusal traces in the LLM Errors tab", async () => {
  render(
    <WebRunActivityTab
      activeTab="activity"
      runId={1}
      run={{ coverage_mode: "standard" }}
      thinkingStatus={{ status: "complete" }}
      activityLog={[
        {
          _id: 1,
          _ts: "10:00:00",
          phase: "llm_request",
          message: "Step 2: sending to LLM",
          status: "pending",
          data: { step: 2 },
        },
        {
          _id: 2,
          _ts: "10:00:01",
          phase: "llm_response",
          message: "Step 2: provider refused this request",
          status: "warning",
          data: { step: 2, error_type: "LLMRefusalError" },
        },
      ]}
      agents={[]}
      sitePlanData={null}
      onClearLog={vi.fn()}
      onError={vi.fn()}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Log" }));
  expect(document.querySelectorAll(".activity-refusal-trace")).toHaveLength(0);
  fireEvent.click(screen.getByRole("button", { name: "LLM Errors" }));
  expect(await screen.findByText("No outcome recorded")).toBeTruthy();
  expect(document.querySelectorAll(".activity-refusal-trace")).toHaveLength(1);
  expect(document.querySelector(".activity-count-label").textContent).toContain(
    "0 succeeded · 0 failed · 1 pending",
  );
  fireEvent.click(screen.getByRole("button", { name: "Display options" }));
  expect(screen.queryByText("Event type")).toBeNull();
});

test("hides the empty Burp row without scan activity", () => {
  render(
    <ActivityAgents
      runId={1}
      agents={[]}
      run={{ coverage_mode: "standard", status: "complete" }}
      thinkingStatus={{ status: "complete" }}
      activityLog={[]}
    />,
  );

  expect(screen.queryByText("Burp")).toBeNull();
});

test("keeps past Burp scan activity visible", () => {
  render(
    <ActivityAgents
      runId={1}
      agents={[
        {
          id: "burp-scan-1",
          role: "Burp",
          status: "complete",
          currentTask: "Burp scan complete",
        },
      ]}
      run={{ coverage_mode: "team", status: "complete" }}
      thinkingStatus={{ status: "complete" }}
      activityLog={[]}
    />,
  );

  expect(screen.getByText("Burp")).toBeTruthy();
  expect(screen.getByText("1 scan complete")).toBeTruthy();
});

test("minimizes an empty Alice chat while another agent is active", () => {
  render(
    <ActivityAgents
      runId={1}
      agents={[{ id: "scanner", role: "Test Lead", status: "active" }]}
      run={{ coverage_mode: "standard", status: "running" }}
      thinkingStatus={{ status: "running" }}
      activityLog={[]}
    />,
  );

  expect(chatState.collapseAgentId).toHaveBeenCalledWith("alice");
});

test("does not count the Alice welcome message as chat activity", () => {
  chatState.aliceChats = [
    {
      id: "default",
      messages: [{ id: "welcome", sender: "alice", text: "Hello! I am A.L.I.C.E." }],
    },
  ];

  render(
    <ActivityAgents
      runId={1}
      agents={[{ id: "scanner", role: "Test Lead", status: "active" }]}
      run={{ coverage_mode: "standard", status: "running" }}
      thinkingStatus={{ status: "running" }}
      activityLog={[]}
    />,
  );

  expect(chatState.collapseAgentId).toHaveBeenCalledWith("alice");
});

test("keeps Alice open when the chat already has activity", () => {
  chatState.aliceChats = [
    {
      id: "default",
      messages: [
        { id: "welcome", sender: "alice", text: "Hello! I am A.L.I.C.E." },
        { id: "user-1", sender: "user", text: "Check login" },
      ],
    },
  ];

  render(
    <ActivityAgents
      runId={1}
      agents={[{ id: "scanner", role: "Test Lead", status: "active" }]}
      run={{ coverage_mode: "team", status: "running" }}
      thinkingStatus={{ status: "running" }}
      activityLog={[]}
    />,
  );

  expect(chatState.collapseAgentId).not.toHaveBeenCalled();
});
