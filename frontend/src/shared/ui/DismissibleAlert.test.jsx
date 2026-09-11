import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { DismissibleAlert } from "./DismissibleAlert.jsx";

test("dismisses a notification from its close button", () => {
  const onDismiss = vi.fn();
  render(
    <DismissibleAlert variant="info" onDismiss={onDismiss}>
      Scan settings saved.
    </DismissibleAlert>,
  );

  fireEvent.click(screen.getByRole("button", { name: "Dismiss notification" }));

  expect(onDismiss).toHaveBeenCalledOnce();
});
