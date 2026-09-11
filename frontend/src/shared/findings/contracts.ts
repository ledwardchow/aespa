/** Matches the editable fields in ScanFindingUpdateIn. */
export type FindingUpdate = {
  severity?: string | null;
  validation_status?: string | null;
  title?: string | null;
  description?: string | null;
  impact?: string | null;
  likelihood?: string | null;
  recommendation?: string | null;
  cvss_score?: number | null;
  cvss_vector?: string | null;
  affected_url?: string | null;
  owasp_category?: string | null;
  owasp_api_category?: string | null;
  evidence?: string | null;
  request_evidence?: string | null;
  response_evidence?: string | null;
  validation_note?: string | null;
};

/** The response can include provider-specific evidence and provenance objects. */
export type Finding = {
  id: number;
  reference: string;
  test_run_id: number | null;
  api_test_run_id: number | null;
  page_id: number | null;
  owasp_category: string;
  owasp_api_category: string | null;
  severity: string;
  validation_status: string;
  title: string;
  description: string;
  impact: string;
  likelihood: string;
  recommendation: string;
  cvss_score: number;
  cvss_vector: string;
  affected_url: string;
  evidence: string;
  request_evidence: string;
  response_evidence: string;
  evidence_json: string;
  evidence_items: Record<string, unknown>[];
  screenshot_b64: string | null;
  finding_source: string;
  validation_note: string | null;
  origin: Record<string, unknown> | null;
  validated_by: Record<string, unknown> | null;
  merged_instances: string;
  poc_command: string;
  poc_setup: string;
  created_at: string;
};
