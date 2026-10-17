import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { AuthenticationGate } from "./AuthenticationGate.tsx";
import * as session from "../shared/auth/session.ts";

vi.mock("../shared/auth/session.ts");

beforeEach(() => {
  vi.mocked(session.getAuthState).mockReturnValue({ status: "signed-out" });
  vi.mocked(session.subscribeAuth).mockReturnValue(() => {});
  vi.mocked(session.initializeAuth).mockResolvedValue();
});

test("keeps management content hidden until authenticated", () => {
  render(
    <AuthenticationGate>
      <div>Private settings</div>
    </AuthenticationGate>,
  );
  expect(screen.queryByText("Private settings")).toBeNull();
  expect(screen.getByLabelText("Authentication key")).toBeTruthy();
  expect(screen.getByText(/shown in the AESPA console/)).toBeTruthy();
});

test("allows another attempt after an incorrect key", async () => {
  vi.mocked(session.signIn).mockRejectedValueOnce(new Error("Invalid authentication key."));
  render(
    <AuthenticationGate>
      <div>Private settings</div>
    </AuthenticationGate>,
  );
  const input = screen.getByLabelText("Authentication key");
  fireEvent.change(input, { target: { value: "wrong" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Invalid authentication key.",
  );
  fireEvent.change(input, { target: { value: "correct" } });
  vi.mocked(session.signIn).mockResolvedValueOnce();
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  await waitFor(() => expect(session.signIn).toHaveBeenLastCalledWith("correct"));
});

test("shows the app for an authenticated session", () => {
  vi.mocked(session.getAuthState).mockReturnValue({ status: "signed-in", csrfToken: "csrf" });
  render(
    <AuthenticationGate>
      <div>Private settings</div>
    </AuthenticationGate>,
  );
  expect(screen.getByText("Private settings")).toBeTruthy();
  expect(screen.queryByLabelText("Authentication key")).toBeNull();
});
