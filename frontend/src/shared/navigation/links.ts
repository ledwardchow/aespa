import { runIdentityKey, type RunIdentity } from "../runs/identity";

const prefixes = { web: "runs", api: "api-runs", sast: "sast-runs" } as const;
export function runHref(
  identity: RunIdentity,
  tab?: string,
  references: { finding?: string; lead?: string } = {},
): string {
  runIdentityKey(identity);
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(references)) if (value) query.set(key, value);
  const suffix = query.size ? `?${query}` : "";
  return `#/${prefixes[identity.runKind]}/${identity.runId}${tab ? `/${encodeURIComponent(tab)}` : ""}${suffix}`;
}
