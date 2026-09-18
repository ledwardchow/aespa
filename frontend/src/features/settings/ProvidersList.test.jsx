import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { ProvidersList } from "./ProvidersList.jsx";

const providers = [
  {
    id: 1,
    name: "Many available models",
    api_format: "openai",
    models: ["available-a", "available-b", "available-c"],
  },
  {
    id: 2,
    name: "Two configured models",
    api_format: "openai",
    models: ["available-d"],
  },
];

const models = [
  { id: 10, provider_id: 1, model: "available-a" },
  { id: 20, provider_id: 2, model: "available-d" },
  { id: 21, provider_id: 2, model: "custom-model" },
];

test("shows and sorts the number of configured models for each provider", async () => {
  const user = userEvent.setup();
  const { container } = render(
    <ProvidersList
      visible
      providers={providers}
      models={models}
      busyId={null}
      onEdit={vi.fn()}
      onDeleteProvider={vi.fn()}
    />,
  );

  const rows = () => [...container.querySelectorAll(".settings-list-row")];
  expect(screen.getByText("Configured models")).toBeTruthy();
  expect(screen.queryByText("Limits")).toBeNull();
  expect(within(rows()[0]).getByText("1")).toBeTruthy();
  expect(within(rows()[1]).getByText("2")).toBeTruthy();
  expect(screen.queryByText("available-a")).toBeNull();

  await user.click(screen.getByText("Configured models"));
  expect(within(rows()[0]).getByText("1")).toBeTruthy();
  expect(within(rows()[1]).getByText("2")).toBeTruthy();

  await user.click(screen.getByText(/Configured models/));
  expect(within(rows()[0]).getByText("2")).toBeTruthy();
  expect(within(rows()[1]).getByText("1")).toBeTruthy();
});
