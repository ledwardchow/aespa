import { req } from "./request.ts";

export type BenchmarkCategory = "site" | "api" | "sast";
export type BulkBenchmarkOutcome = {
  completed: number[];
  skipped: number[];
  failures: { run_id: number; error: string }[];
};
export const benchmarkUnbenchmarked = (body: {
  run_kind: BenchmarkCategory;
  dataset_id: number;
  evaluation_model_id?: number;
}) =>
  req<BulkBenchmarkOutcome>("/extension/aespa.benchmarking/results/benchmark-unbenchmarked", {
    method: "POST",
    body,
  });
