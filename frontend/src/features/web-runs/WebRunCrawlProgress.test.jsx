import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { WebRunUserCrawlProgress } from "./WebRunCrawlProgress.jsx";

test("shows anonymous crawl progress with account progress", () => {
  render(
    <WebRunUserCrawlProgress
      run={{
        credentials: [{ username: "alice", label: "Alice" }],
        per_user_progress: {
          unauthenticated: { pages_visited: 3, current_url: "https://shop.example/deals" },
          alice: { pages_visited: 2, done: true, login_status: "success" },
        },
      }}
      crawlerActive
    />,
  );

  expect(screen.getByText("2 users · 5 pages · 1 done")).toBeTruthy();
  expect(screen.getByText("Unauthenticated")).toBeTruthy();
  expect(screen.getByText("Alice")).toBeTruthy();
  expect(screen.queryByText("No login")).toBeNull();
  expect(screen.getByText("Login successful")).toBeTruthy();
  expect(document.querySelector(".crawl-user-pages")).toBeNull();
  expect(
    screen.getByRole("button", { name: /User crawl progress/ }).getAttribute("aria-expanded"),
  ).toBe("true");
});

test("shows failed login from the saved activity log", () => {
  render(
    <WebRunUserCrawlProgress
      run={{ credentials: [{ username: "alice" }], per_user_progress: { alice: {} } }}
      activityLog={[{ phase: "auth", status: "error", message: "Could not log in as alice" }]}
      crawlerActive={false}
    />,
  );

  expect(screen.getByText("Login failed")).toBeTruthy();
});
