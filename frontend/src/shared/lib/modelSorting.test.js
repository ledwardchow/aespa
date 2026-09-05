import assert from "node:assert/strict";
import { test } from "vitest";

import { sortModelConfigs, sortModelNames } from "./modelSorting.js";

test("provider model names sort alphabetically without mutating the source", () => {
  const source = ["zeta-2", "Alpha-10", "alpha-2"];

  assert.deepEqual(sortModelNames(source), ["alpha-2", "Alpha-10", "zeta-2"]);
  assert.deepEqual(source, ["zeta-2", "Alpha-10", "alpha-2"]);
});

test("configured models sort by their displayed dropdown labels", () => {
  const source = [
    { id: 2, name: "Zulu", model: "z" },
    { id: 1, name: "Alpha", model: "a" },
  ];

  assert.deepEqual(
    sortModelConfigs(source).map((model) => model.id),
    [1, 2],
  );
});
