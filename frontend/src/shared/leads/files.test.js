import { expect, test } from "vitest";
import { leadConfidenceLabel, leadsToMarkdown } from "./files.js";

test("Markdown lead exports retain external scanner and rule identity for re-import", () => {
  const text = leadsToMarkdown([
    {
      title: "SQL injection",
      source: "Example scanner",
      severity: "high",
      location: "query.py:42",
      producer_run_type: "external",
      suggested_endpoint: "GET /query",
      source_trace_json: JSON.stringify({
        external_report: { scanner: "Example scanner", rule_id: "sql-001" },
      }),
    },
  ]);
  const payload = JSON.parse(decodeURIComponent(text.match(/aespa-sast-leads-json\n([^\n]+)/)[1]));
  expect(payload[0]).toMatchObject({
    scanner: "Example scanner",
    rule_id: "sql-001",
    suggested_endpoint: "GET /query",
  });
});

test("an imported lead without a confidence score stays unknown in the table and export", () => {
  const lead = {
    title: "Unchecked account lookup",
    producer_run_type: "external",
    confidence: 0,
    source_trace_json: JSON.stringify({ confidence_unknown: true }),
  };
  expect(leadConfidenceLabel(lead)).toBe("Unknown");
  const markdown = leadsToMarkdown([lead]);
  expect(markdown).not.toContain("Confidence: 0%");
  const payload = JSON.parse(
    decodeURIComponent(markdown.match(/aespa-sast-leads-json\n([^\n]+)/)[1]),
  );
  expect(payload[0].confidence).toBeNull();
});
