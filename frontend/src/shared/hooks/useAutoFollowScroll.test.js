import assert from "node:assert/strict";
import { test } from "vitest";

import { isNearScrollBottom } from "./useAutoFollowScroll.js";

test("treats a history viewport within the threshold as near the bottom", () => {
  assert.equal(isNearScrollBottom({ scrollHeight: 500, clientHeight: 200, scrollTop: 276 }), true);
});

test("treats a history viewport above the threshold as scrolled up", () => {
  assert.equal(isNearScrollBottom({ scrollHeight: 500, clientHeight: 200, scrollTop: 275 }), false);
});
