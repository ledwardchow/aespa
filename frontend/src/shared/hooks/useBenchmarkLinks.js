import { useCallback, useState } from "react";
import * as benchmarkApi from "../api/benchmarkLab.js";
import { usePolling } from "./usePolling.js";

/** Saved benchmarks are keyed by scan type because run IDs can overlap. */
export function useBenchmarkLinks(enabled = true) {
  const [links, setLinks] = useState({});
  const load = useCallback(async (signal) => {
    try {
      const { results, evaluations } = await benchmarkApi.listBenchmarkLinks();
      if (signal.aborted) return;
      const next = {};
      for (const evaluation of evaluations)
        next[`sast:${evaluation.sast_run_id}`] = `#/benchmark-lab/evaluations/${evaluation.id}`;
      for (const result of results)
        next[`${result.run_kind}:${result.run_id}`] = `#/benchmark-lab/results/${result.id}`;
      setLinks(next);
    } catch {
      if (!signal.aborted) setLinks({});
    }
  }, []);
  usePolling(load, { enabled, immediate: enabled, intervalMs: 15000 });
  return links;
}
