import { req } from "./request.ts";

export type SastImportSource = {
  id: number;
  name: string;
  source_filename: string;
  completed_at: string | null;
  leads_count: number;
  imported_count?: number;
  new_count?: number;
};
export type SastImportPage = {
  items: SastImportSource[];
  total: number;
  page: number;
  page_size: number;
};
export type DynamicRunKind = "web" | "api";
const base = (kind: DynamicRunKind, id: number) =>
  `/api/${kind === "api" ? "api-test-runs" : "test-runs"}/${id}`;

export async function searchSastImportSources(
  kind: DynamicRunKind,
  id: number,
  query: string,
  page: number,
  signal: AbortSignal,
): Promise<SastImportPage> {
  const pageSize = 10;
  const params = new URLSearchParams({ q: query, page: String(page), page_size: String(pageSize) });
  const response = await req<SastImportPage | SastImportSource[]>(
    `${base(kind, id)}/sast-runs/available?${params}`,
    { signal },
  );
  // An already-running older backend ignores the paging parameters. Keep its
  // existing import endpoint usable until the user can safely restart it.
  if (Array.isArray(response)) {
    const term = query.trim().toLowerCase();
    const matches = response.filter(
      (scan) =>
        scan.name.toLowerCase().includes(term) ||
        (scan.source_filename || "").toLowerCase().includes(term) ||
        String(scan.id) === term,
    );
    return {
      items: matches.slice((page - 1) * pageSize, page * pageSize),
      total: matches.length,
      page,
      page_size: pageSize,
    };
  }
  if (!response) throw new Error("The server returned no SAST scans.");
  return response;
}

export async function importSastSource(kind: DynamicRunKind, id: number, sourceId: number) {
  const result = await req<{ imported: number }>(`${base(kind, id)}/import-leads`, {
    method: "POST",
    body: { sast_run_id: sourceId },
  });
  if (!result) throw new Error("The server returned no import result.");
  return result;
}

export type ReportPreview = {
  format: "SARIF" | "Markdown" | "AI-reviewed report";
  prepared?: string;
  filename: string;
  total: number;
  new_count: number;
  already_imported: number;
  skipped: number;
  imported: number;
  preview_limit: number;
  warnings: string[];
  items: Array<{
    title: string;
    description: string;
    severity: string;
    category: string;
    location: string;
    evidence: string;
    source_quote: string;
    scanner: string;
    rule_id: string;
    suggested_endpoint: string;
    confidence: number | null;
    already_imported: boolean;
  }>;
};

export async function importLeadReport(
  kind: DynamicRunKind,
  id: number,
  file: File,
  preview: boolean,
  prepared?: string,
): Promise<ReportPreview> {
  const body = new FormData();
  body.append("file", file);
  body.append("preview", String(preview));
  if (prepared) body.append("prepared", prepared);
  const result = await req<ReportPreview>(`${base(kind, id)}/import-report`, {
    method: "POST",
    body,
  });
  if (!result) throw new Error("The server returned no report preview.");
  return result;
}
