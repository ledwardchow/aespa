export type RunKind = "web" | "api" | "sast";
export type RunIdentity = { runKind: RunKind; runId: number };

/** IDs are allocated independently for each run kind. */
export function runIdentityKey({ runKind, runId }: RunIdentity): string {
  if (!["web", "api", "sast"].includes(runKind) || !Number.isSafeInteger(runId) || runId < 1) {
    throw new Error("A valid run kind and positive run ID are required");
  }
  return `${runKind}:${runId}`;
}
