import { expect, test } from "vitest";
import { runIdentityKey } from "./identity";
import { aliceIdentityKey } from "../alice/transport.js";

test("colliding numeric run IDs stay isolated in chat and other UI state", () => {
  const keys = ["web", "api", "sast"].map((runKind) =>
    runIdentityKey({ runKind: runKind as "web" | "api" | "sast", runId: 1 }),
  );
  expect(new Set(keys).size).toBe(3);
  expect(aliceIdentityKey({ runKind: "api", runId: 1 })).toBe("api:1");
});
