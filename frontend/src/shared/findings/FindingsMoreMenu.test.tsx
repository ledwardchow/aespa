import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { FindingsMoreMenu } from "./FindingsMoreMenu.tsx";

const openMenu = () =>
  fireEvent.click(screen.getByRole("button", { name: "More finding actions" }));

test("groups export, import, and clear in one menu", () => {
  const onExport = vi.fn();
  const onClear = vi.fn();
  render(<FindingsMoreMenu hasFindings onExport={onExport} onImport={vi.fn()} onClear={onClear} />);

  expect(screen.queryByRole("menu")).toBeNull();
  openMenu();
  expect(screen.getAllByRole("menuitem").map((item) => item.textContent)).toEqual([
    "Export findings",
    "Import findings",
    "Clear all findings",
  ]);

  fireEvent.click(screen.getByRole("menuitem", { name: "Export findings" }));
  expect(onExport).toHaveBeenCalledOnce();
  expect(screen.queryByRole("menu")).toBeNull();

  openMenu();
  fireEvent.click(screen.getByRole("menuitem", { name: "Clear all findings" }));
  expect(onClear).toHaveBeenCalledOnce();
});

test("only offers import when there are no findings", () => {
  render(
    <FindingsMoreMenu
      hasFindings={false}
      onExport={vi.fn()}
      onImport={vi.fn()}
      onClear={vi.fn()}
    />,
  );
  openMenu();
  expect(screen.getAllByRole("menuitem").map((item) => item.textContent)).toEqual([
    "Import findings",
  ]);
});

test("closes on Escape and shows clearing state", () => {
  render(
    <FindingsMoreMenu
      hasFindings
      onExport={vi.fn()}
      onImport={vi.fn()}
      onClear={vi.fn()}
      clearBusy
    />,
  );
  openMenu();
  expect(screen.getByRole("menuitem", { name: "Clearing…" })).toHaveProperty("disabled", true);
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("menu")).toBeNull();
});
