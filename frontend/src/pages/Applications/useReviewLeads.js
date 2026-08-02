import { useState, useEffect, useCallback } from "react";
import { api } from "../../lib/api";

// Loads campaign mappings (now server-enriched with lead_title/description/
// severity/location/producer_run_type/producer_run_id and component_ids/
// component_names — see GET .../campaigns/{id}/mappings) plus target names
// for display. No more per-SAST-run lead fan-out: the mapping row itself is
// the authoritative source for every lead, including campaign-owned
// cross-repository leads.
export function useReviewLeads(applicationId, campaignId) {
  const [mappings, setMappings] = useState(null);
  const [targets, setTargets] = useState({});
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [maps, tgts] = await Promise.all([
        api.getCampaignMappings(applicationId, campaignId),
        api.listAppTargets(applicationId)
      ]);
      setMappings(maps);
      const targetMap = {}; tgts.forEach(t => { targetMap[t.id] = t.name || `#${t.target_id}`; });
      setTargets(targetMap);
    } catch (e) {
      setError(e.message);
    }
  }, [applicationId, campaignId]);

  useEffect(() => { load(); }, [load]);

  const submitReview = useCallback(async decisions => {
    const result = await api.reviewCampaignMappings(applicationId, campaignId, { decisions });
    await load();
    return result;
  }, [applicationId, campaignId, load]);

  return { mappings, targets, error, setError, submitReview };
}
