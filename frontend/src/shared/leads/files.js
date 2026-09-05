import {
  markdownListValue,
  markdownText,
  markdownCodeBlock,
  slugForFilename,
} from "../lib/markdown.js";

export function leadImportPayload(l) {
  return {
    title: l.title,
    severity: l.severity,
    category: l.category,
    confidence: l.confidence,
    location: l.location,
    description: l.description,
    evidence: l.evidence,
    status: l.status,
    note: l.note,
    source: l.source,
  };
}

export function leadsExportFilename(name, runId) {
  const base = slugForFilename(name || `sast-run-${runId || ""}`);
  return `${base}-leads-${new Date().toISOString().slice(0, 10)}.md`;
}

export function leadsToMarkdown(leads, meta = {}) {
  const sevOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
  const sorted = [...(leads || [])].sort((a, b) => {
    const sev = (sevOrder[a.severity] ?? 99) - (sevOrder[b.severity] ?? 99);
    if (sev !== 0) return sev;
    return (b.confidence || 0) - (a.confidence || 0);
  });
  const lines = [`# SAST Leads Export${meta.runName ? `: ${meta.runName}` : ""}`, ""];
  if (meta.generatedAt) lines.push(`- Exported: ${meta.generatedAt.toLocaleString()}`);
  lines.push(`- Total leads: ${sorted.length}`, "");
  lines.push(
    "<!-- aespa-sast-leads-json",
    encodeURIComponent(JSON.stringify(sorted.map(leadImportPayload))),
    "-->",
    "",
  );
  sorted.forEach((l, idx) => {
    lines.push(
      `## ${idx + 1}. ${markdownListValue(l.title)}`,
      "",
      `- Severity: ${markdownListValue(l.severity)}`,
      `- Category: ${markdownListValue(l.category)}`,
      `- Confidence: ${Math.round((l.confidence || 0) * 100)}%`,
      `- Status: ${markdownListValue(l.status)}`,
      `- Location: ${markdownListValue(l.location)}`,
      "",
      "### Description",
      markdownListValue(l.description),
      "",
      "### Code Evidence",
      markdownCodeBlock(l.evidence),
      "",
    );
    if (l.note) lines.push("### Investigation Note", markdownListValue(l.note), "");
  });
  return lines.join("\n");
}

export function markdownTableValue(value) {
  return markdownListValue(value).replace(/\|/g, "\\|").replace(/\r?\n/g, "<br>");
}

export function sastTraceValue(value, fallback) {
  let parsed = value;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value);
    } catch {
      parsed = value;
    }
  }
  const empty =
    parsed == null ||
    parsed === "" ||
    (Array.isArray(parsed) && parsed.length === 0) ||
    (typeof parsed === "object" && !Array.isArray(parsed) && Object.keys(parsed).length === 0);
  if (empty) return { text: fallback, recorded: false };
  return {
    text: typeof parsed === "string" ? parsed : JSON.stringify(parsed, null, 2),
    recorded: true,
  };
}

export function appendSastTrace(lines, label, value, fallback) {
  const trace = sastTraceValue(value, fallback);
  lines.push(`#### ${label}`, "");
  if (trace.recorded) lines.push(markdownCodeBlock(trace.text), "");
  else lines.push(trace.text, "");
}

export function sastReportFilename(name, runId) {
  const base = slugForFilename(name || `sast-run-${runId || ""}`);
  return `${base}-sast-report-${new Date().toISOString().slice(0, 10)}.md`;
}

export function sastCandidatesToMarkdown(leads, meta = {}) {
  const issues = [...(leads || [])];
  const lines = [`# SAST Report${meta.runName ? `: ${markdownText(meta.runName)}` : ""}`, ""];
  if (meta.generatedAt) lines.push(`- Exported: ${meta.generatedAt.toLocaleString()}`);
  lines.push(`- Total issues: ${issues.length}`, "", "## Issue Summary", "");
  lines.push("| # | Severity | Candidate | Confidence | Validation | Reportable | Location |");
  lines.push("|---:|---|---|---:|---|---|---|");
  issues.forEach((lead, index) => {
    lines.push(
      `| ${index + 1} | ${markdownTableValue((lead.severity || "medium").toUpperCase())} | ${markdownTableValue(lead.title || "Untitled candidate")} | ${Math.round((lead.confidence || 0) * 100)}% | ${markdownTableValue(lead.validation_status || "pending")} | ${lead.reportable ? "Yes" : "No"} | ${markdownTableValue(lead.location || "Location not provided")} |`,
    );
  });
  if (!issues.length) lines.push("| — | — | No issues | — | — | — | — |");
  lines.push("");

  issues.forEach((lead, index) => {
    const sourceTrace = sastTraceValue(lead.source_trace_json, "");
    lines.push(
      `## ${index + 1}. ${markdownListValue(lead.title || "Untitled candidate")}`,
      "",
      `- Lead reference: ${markdownListValue(lead.reference || "—")}`,
      ...(lead.origin_reference
        ? [`- Origin lead: ${markdownListValue(lead.origin_reference)}`]
        : []),
      `- Category: ${markdownListValue(lead.category || "Unclassified")}`,
      `- Severity: ${markdownListValue((lead.severity || "medium").toUpperCase())}`,
      `- Confidence: ${Math.round((lead.confidence || 0) * 100)}%`,
      `- Validation: ${markdownListValue(lead.validation_status || "pending")}`,
      `- Reportable: ${lead.reportable ? "Yes" : "No"}`,
      `- Location: ${markdownListValue(lead.location || "Location not provided")}`,
      `- Fingerprint: ${markdownListValue(lead.fingerprint)}`,
      "",
      "### Evidence Chain",
      "",
    );
    appendSastTrace(
      lines,
      "Source",
      sourceTrace.recorded ? lead.source_trace_json : lead.location,
      "Not recorded",
    );
    appendSastTrace(lines, "Controls encountered", lead.control_trace_json, "No controls recorded");
    appendSastTrace(lines, "Sink", lead.sink_trace_json, "Not recorded");
    appendSastTrace(
      lines,
      "Counterevidence",
      lead.counterevidence_json,
      "No counterevidence recorded",
    );
    appendSastTrace(lines, "Proof gaps", lead.proof_gaps_json, "No unresolved static proof gaps");
    appendSastTrace(
      lines,
      "Attack path",
      lead.attack_path_json,
      "Not available for this candidate",
    );
    if (lead.validation_reasoning)
      lines.push("#### Validator reasoning", "", markdownText(lead.validation_reasoning), "");
    if (lead.evidence) lines.push("#### Code evidence", "", markdownCodeBlock(lead.evidence), "");
  });
  return lines.join("\n");
}
