const paths = {
  web: id => `/api/test-runs/${id}/alice`,
  api: id => `/api/api-test-runs/${id}/alice`
};

/** Returns the shared ALICE HTTP endpoints for an explicit run identity. */
export function aliceTransport({ runKind, runId }) {
  const base = paths[runKind]?.(runId);
  if (!base) throw new Error(`Unsupported ALICE run kind: ${runKind}`);
  return {
    streamUrl: cursor => `${base}/stream?cursor=${cursor}`,
    runUrl: `${base}/run`
  };
}

export const aliceIdentityKey = ({ runKind, runId }) => `${runKind}:${runId}`;
