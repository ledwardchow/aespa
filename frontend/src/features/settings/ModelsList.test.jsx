import { fireEvent, render } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ModelsList } from "./ModelsList.jsx";

test("reverses model name order within each provider when provider sort reverses", () => {
  const models = [
    { id: 1, name: "Alpha", provider_name: "Acme", provider_id: 1 },
    { id: 2, name: "Zeta", provider_name: "Acme", provider_id: 1 },
    { id: 3, name: "Beta", provider_name: "Other", provider_id: 2 },
  ];
  render(
    <ModelsList
      visible
      models={models}
      providers={[{ id: 1 }, { id: 2 }]}
      onEdit={vi.fn()}
      onDelete={vi.fn()}
    />,
  );
  const names = () =>
    [...document.querySelectorAll(".settings-list-row strong")].map((name) => name.textContent);
  expect(names()).toEqual(["Alpha", "Zeta", "Beta"]);

  fireEvent.click(document.querySelector(".settings-list-head .sortable:nth-child(2)"));
  expect(names()).toEqual(["Beta", "Zeta", "Alpha"]);
});
