import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";
import { Tabs } from "./Tabs.tsx";

test("keyboard navigation changes selection and skips disabled tabs", async () => {
  const user = userEvent.setup();
  function Example() {
    const [value, setValue] = useState("one");
    return (
      <Tabs
        label="Example views"
        value={value}
        onChange={setValue}
        tabs={[
          { key: "one", label: "One" },
          { key: "two", label: "Two", disabled: true },
          { key: "three", label: "Three" },
        ]}
      />
    );
  }
  render(<Example />);
  await user.tab();
  await user.keyboard("{ArrowRight}");
  expect(screen.getByRole("tab", { name: "Three" }).getAttribute("aria-selected")).toBe("true");
  expect(document.activeElement).toBe(screen.getByRole("tab", { name: "Three" }));
  await user.keyboard("{Home}");
  expect(document.activeElement).toBe(screen.getByRole("tab", { name: "One" }));
});
