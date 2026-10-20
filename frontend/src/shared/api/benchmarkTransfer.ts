import { importJson } from "./request";

export interface BenchmarkImportReport {
  imported: number;
  skipped: number;
  datasets_added: number;
  conflicts: { kind: string; key: string; name: string }[];
}

export const benchmarkExportUrl = "/extension/aespa.benchmarking/export";
export const importBenchmarkData = (text: string) =>
  importJson<BenchmarkImportReport>("/extension/aespa.benchmarking/import", text);
