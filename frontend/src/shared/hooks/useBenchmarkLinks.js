import { useCallback, useState } from "react";
import * as benchmarkApi from "../api/benchmarkLab.js";
import * as extensionsApi from "../api/extensions.js";
import { usePolling } from "./usePolling.js";

/** Saved benchmarks are keyed by scan type because run IDs can overlap. */
export function useBenchmarkLinks() {
  const [links, setLinks] = useState({});
  const load = useCallback(async (signal) => {
    try {
      const extensions = await extensionsApi.listExtensions();
      if (signal.aborted) return;
      if (
        !extensions.some(
          (item) => item.id === "aespa.benchmarking" && item.enabled && item.status === "loaded",
        )
      ) {
        setLinks({});
        return;
      }
      const [results, evaluations] = await Promise.all([
        benchmarkApi.listBenchmarkResults(),
        benchmarkApi.listBenchmarkEvaluations(),
      ]);
      if (signal.aborted) return;
      const next = {};
      for (const evaluation of evaluations) {
        if (evaluation.status === "completed")
          next[`sast:${evaluation.sast_run_id}`] = `#/benchmark-lab/evaluations/${evaluation.id}`;
      }
      for (const result of results)
        next[`${result.run_kind}:${result.run_id}`] = `#/benchmark-lab/results/${result.id}`;
      setLinks(next);
    } catch {
      if (!signal.aborted) setLinks({});
    }
  }, []);
  usePolling(load, { intervalMs: 15000 });
  return links;
}
