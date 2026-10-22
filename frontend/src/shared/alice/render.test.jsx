import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { renderAliceTraceBox } from "./render.jsx";

test("SAST tool activity opens its saved call and result", () => {
  const { container } = render(
    renderAliceTraceBox(
      "trace-1",
      "Used tool: read_file\n",
      {
        1: {
          tools: [
            {
              tool: "read_file",
              input: { path: "src/orders.py" },
              result: "def load_order(order_id): ...",
            },
          ],
        },
      },
      true,
      () => {},
    ),
  );
  const details = container.querySelector("details");
  expect(details).not.toBeNull();
  fireEvent.click(details.querySelector("summary"));
  expect(details.open).toBe(true);
  expect(screen.getByText(/src\/orders.py/)).toBeTruthy();
  expect(screen.getByText("def load_order(order_id): ...")).toBeTruthy();
});
