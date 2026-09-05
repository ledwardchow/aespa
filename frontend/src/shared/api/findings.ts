import { req } from "./request.ts";
import type { Finding, FindingUpdate } from "../findings/contracts.ts";
import type { RunIdentity } from "../runs/identity.ts";

type FindingRun = RunIdentity & { runKind: "web" | "api" };
function findingsPath({ runKind, runId }: FindingRun): string {
  return `/api/${runKind === "web" ? "test-runs" : "api-test-runs"}/${runId}/findings`;
}
export function getFindings(run: FindingRun, signal?: AbortSignal) {
  return req<Finding[]>(findingsPath(run), { signal });
}
export function updateFinding(run: FindingRun, findingId: number, body: FindingUpdate) {
  return req<Finding>(`${findingsPath(run)}/${findingId}`, { method: "PATCH", body });
}
