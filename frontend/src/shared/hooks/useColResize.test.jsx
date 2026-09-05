import { act, renderHook } from "@testing-library/react";
import { expect, test } from "vitest";
import { useColResize } from "./useColResize.js";

test("column resizing persists widths and stops tracking after unmount", () => {
  localStorage.setItem("test-columns", "invalid JSON");
  const { result, unmount } = renderHook(() => useColResize("test-columns", [100, null]));
  const cell = document.createElement("th");
  const event = { clientX: 10, currentTarget: cell, preventDefault() {}, stopPropagation() {} };
  act(() => result.current[1](0, event));
  act(() => document.dispatchEvent(new MouseEvent("mousemove", { clientX: 70 })));
  expect(result.current[0][0]).toBe(160);
  act(() => document.dispatchEvent(new MouseEvent("mouseup")));
  expect(JSON.parse(localStorage.getItem("test-columns"))).toEqual([160, null]);
  act(() => result.current[1](0, event));
  unmount();
  document.dispatchEvent(new MouseEvent("mousemove", { clientX: 200 }));
  document.dispatchEvent(new MouseEvent("mouseup"));
  expect(JSON.parse(localStorage.getItem("test-columns"))).toEqual([160, null]);
});
