import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test } from "vitest";

import { useHashTab } from "./useHashTab.js";

function TabView() {
  const [tab, setTab] = useHashTab("subtab", ["agents", "log"], "agents");
  return (
    <>
      <span>{tab}</span>
      <button onClick={() => setTab("log")}>Show log</button>
    </>
  );
}

beforeEach(() => {
  window.location.hash = "#/api-runs/7/status?finding=F-12";
});

test("keeps the selected subtab in the URL and restores it after remounting", async () => {
  const user = userEvent.setup();
  const view = render(<TabView />);
  await user.click(screen.getByRole("button", { name: "Show log" }));
  await waitFor(() => expect(screen.getByText("log")).toBeTruthy());
  expect(window.location.hash).toBe("#/api-runs/7/status?finding=F-12&subtab=log");

  view.unmount();
  render(<TabView />);
  expect(screen.getByText("log")).toBeTruthy();

  window.location.hash = "#/api-runs/7/status?finding=F-12&subtab=agents";
  await waitFor(() => expect(screen.getByText("agents")).toBeTruthy());
});

test("uses the default subtab for an unknown URL value", () => {
  window.location.hash = "#/api-runs/7/status?subtab=missing";
  render(<TabView />);
  expect(screen.getByText("agents")).toBeTruthy();
});
