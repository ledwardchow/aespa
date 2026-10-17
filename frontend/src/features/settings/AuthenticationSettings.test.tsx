import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { AuthenticationSettings } from "./AuthenticationSettings.tsx";
import { getAuthenticationKey } from "../../shared/auth/session.ts";

vi.mock("../../shared/auth/session.ts");
beforeEach(() => vi.mocked(getAuthenticationKey).mockResolvedValue("management-key"));

test("retrieves the key only when Show is pressed and can hide it again", async () => {
  vi.mocked(getAuthenticationKey).mockClear();
  render(<AuthenticationSettings />);
  expect(getAuthenticationKey).not.toHaveBeenCalled();
  const input = screen.getByLabelText("Authentication key") as HTMLInputElement;
  expect(input.type).toBe("password");
  fireEvent.click(screen.getByRole("button", { name: "Show" }));
  await waitFor(() => expect(input.value).toBe("management-key"));
  fireEvent.click(screen.getByRole("button", { name: "Hide" }));
  expect(input.type).toBe("password");
  expect(input.value).not.toContain("management-key");
});

test("copies without revealing the key", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  render(<AuthenticationSettings />);
  fireEvent.click(screen.getByRole("button", { name: "Copy" }));
  await screen.findByRole("status");
  expect(writeText).toHaveBeenCalledWith("management-key");
  expect((screen.getByLabelText("Authentication key") as HTMLInputElement).type).toBe("password");
});
