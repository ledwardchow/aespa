import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { nav } from "../navigation/router.js";
import { NavigationRow } from "./NavigationRow.jsx";

vi.mock("../navigation/router.js", () => ({ nav: vi.fn() }));

function ExampleRow() {
  return (
    <table>
      <tbody>
        <NavigationRow href="#/runs/7" label="Open Example run">
          <td>Example run</td>
          <td>
            <a href="#/runs/7">Open</a>
            <button type="button">Delete</button>
          </td>
        </NavigationRow>
      </tbody>
    </table>
  );
}

beforeEach(() => vi.clearAllMocks());

test("opens the destination when the non-interactive part of the row is clicked", () => {
  render(<ExampleRow />);

  fireEvent.click(screen.getByText("Example run"));

  expect(nav).toHaveBeenCalledWith("#/runs/7");
});

test("does not override links or buttons inside the row", () => {
  render(<ExampleRow />);

  fireEvent.click(screen.getByRole("link", { name: "Open" }));
  fireEvent.click(screen.getByRole("button", { name: "Delete" }));

  expect(nav).not.toHaveBeenCalled();
});

test("opens the destination from the focused row with Enter or Space", () => {
  render(<ExampleRow />);
  const row = screen.getByRole("row", { name: "Open Example run" });

  fireEvent.keyDown(row, { key: "Enter" });
  fireEvent.keyDown(row, { key: " " });

  expect(nav).toHaveBeenNthCalledWith(1, "#/runs/7");
  expect(nav).toHaveBeenNthCalledWith(2, "#/runs/7");
});
