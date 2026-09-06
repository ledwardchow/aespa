import * as applicationsApi from "../../shared/api/applications.js";
import { useState, useEffect, useCallback } from "react";
import { validationCasesFromResponse } from "./ValidationCases.jsx";

// Loads campaign mappings (now server-enriched with lead_title/description/
// severity/location/producer_run_type/producer_run_id and component_ids/
// component_names — see GET .../campaigns/{id}/mappings) plus target names
// for display. No more per-SAST-run lead fan-out: the mapping row itself is
// the authoritative source for every lead, including campaign-owned
// cross-repository leads.
export function useReviewLeads(applicationId, campaignId) {
  const [mappings, setMappings] = useState(null);
  const [targets, setTargets] = useState({});
  const [validationCases, setValidationCases] = useState([]);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [mapsResult, tgtsResult, casesResult] = await Promise.allSettled([
        applicationsApi.getCampaignMappings(applicationId, campaignId),
        applicationsApi.listAppTargets(applicationId),
        applicationsApi.getCampaignValidationCases(applicationId, campaignId),
      ]);
      if (mapsResult.status === "rejected") throw mapsResult.reason;
      if (tgtsResult.status === "rejected") throw tgtsResult.reason;
      setMappings(mapsResult.value);
      const targetMap = {};
      tgtsResult.value.forEach((t) => {
        targetMap[t.id] = t.name || `#${t.target_id}`;
      });
      setTargets(targetMap);
      setValidationCases(
        casesResult.status === "fulfilled" ? validationCasesFromResponse(casesResult.value) : [],
      );
    } catch (e) {
      setError(e.message);
    }
  }, [applicationId, campaignId]);

  useEffect(() => {
    load();
  }, [load]);

  const submitReview = useCallback(
    async (decisions) => {
      const result = await applicationsApi.reviewCampaignMappings(applicationId, campaignId, {
        decisions,
      });
      await load();
      return result;
    },
    [applicationId, campaignId, load],
  );

  return { mappings, targets, validationCases, error, setError, submitReview };
}
