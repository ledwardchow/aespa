import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { expect, test, vi } from "vitest";
import { ProfilesList } from "./ProfilesList.jsx";

const initialProfiles = [
  {
    id: 1,
    name: "Current profile",
    default_model_name: "Provider/model-a",
    role_models: {},
    is_active: true,
  },
  {
    id: 2,
    name: "Other profile",
    default_model_name: "Provider/model-b",
    role_models: { crawler: 3 },
    is_active: false,
  },
];

function ProfilesListHarness({ onActivate }) {
  const [profiles, setProfiles] = useState(initialProfiles);
  const activate = (profile) => {
    onActivate(profile);
    setProfiles((items) => items.map((item) => ({ ...item, is_active: item.id === profile.id })));
  };

  return (
    <ProfilesList
      visible
      profiles={profiles}
      models={[{ id: 1 }]}
      busyId={null}
      onActivate={activate}
      onEdit={vi.fn()}
      onDelete={vi.fn()}
    />
  );
}

test("shows a default badge in place of a status column", async () => {
  const user = userEvent.setup();
  const onActivate = vi.fn();
  render(<ProfilesListHarness onActivate={onActivate} />);

  expect(screen.queryByText("Status")).toBeNull();
  expect(screen.getByText("default", { selector: ".badge" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: /currently default/i })).toBeNull();

  await user.click(screen.getByRole("button", { name: "Set as default" }));

  expect(onActivate).toHaveBeenCalledWith(initialProfiles[1]);
  expect(screen.getAllByText("default", { selector: ".badge" })).toHaveLength(1);
  expect(screen.getByRole("button", { name: "Set as default" })).toBeTruthy();
});
