import { runIdentityKey } from "../runs/identity.ts";
const paths = {
  web: (id) => `/api/test-runs/${id}/alice`,
  api: (id) => `/api/api-test-runs/${id}/alice`,
  sast: (id) => `/api/sast-runs/${id}/alice`,
};

/** Returns the shared ALICE HTTP endpoints for an explicit run identity. */
export function aliceTransport({ runKind, runId }) {
  const base = paths[runKind]?.(runId);
  if (!base) throw new Error(`Unsupported ALICE run kind: ${runKind}`);
  return {
    streamUrl: (cursor, tabId) =>
      `${base}/stream?cursor=${cursor}` + (tabId ? `&tab_id=${encodeURIComponent(tabId)}` : ""),
    runUrl: `${base}/run`,
  };
}

export const aliceIdentityKey = runIdentityKey;
