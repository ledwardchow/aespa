import { req } from "./request";

interface ImportedLead {
  producer_run_type: string;
  producer_run_id: number;
}

interface Usage {
  estimated_cost_available?: boolean;
  estimated_total_cost_usd?: number | null;
  by_model?: Record<string, { estimated_cost_available?: boolean }>;
}

export interface SastSourceCost {
  runId: number;
  name: string;
  cost: number | null;
}

export async function getSastSourceCosts(
  runId: number,
  signal: AbortSignal,
): Promise<SastSourceCost[]> {
  const leads = await req<ImportedLead[]>(`/api/test-runs/${runId}/leads`, { signal });
  const sourceIds = [
    ...new Set(
      (leads || [])
        .filter((lead) => lead.producer_run_type === "sast")
        .map((lead) => lead.producer_run_id),
    ),
  ].sort((a, b) => a - b);
  return Promise.all(
    sourceIds.map(async (sourceId) => {
      const [run, usage] = await Promise.all([
        req<{ name: string }>(`/api/sast-runs/${sourceId}`, { signal }).catch(() => null),
        req<Usage>(`/api/sast-runs/${sourceId}/token-usage`, { signal }).catch(() => null),
      ]);
      const estimate = usage?.estimated_total_cost_usd;
      // A partially priced run must not look like a complete cost estimate.
      const models = Object.values(usage?.by_model || {});
      const available =
        usage?.estimated_cost_available && models.every((model) => model.estimated_cost_available);
      return {
        runId: sourceId,
        name: run?.name || `SAST run #${sourceId}`,
        cost:
          available && typeof estimate === "number" && Number.isFinite(estimate) ? estimate : null,
      };
    }),
  );
}
