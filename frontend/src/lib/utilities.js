// ── Utilities ─────────────────────────────────────────────────────────────────

export function parseDate(val) {
  if (!val) return new Date(val);
  if (val instanceof Date) return val;
  let s = String(val).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(s) && !/[Zz]|[+-]\d{2}:?\d{2}$/.test(s)) {
    s = s.replace(" ", "T");
    if (!s.endsWith("Z")) {
      s += "Z";
    }
  }
  return new Date(s);
}

export function fmtDate(iso) {
  return iso ? parseDate(iso).toLocaleString(undefined, {dateStyle:"short",timeStyle:"short"}) : "—";
}

export function truncUrl(url, maxLen=40) {
  try {
    const u = new URL(url);
    const s = u.hostname + u.pathname + u.hash;
    return s.length > maxLen ? s.slice(0, maxLen-1) + "…" : s;
  } catch { return url.slice(0, maxLen); }
}

export function sourceLabel(source) {
  const labels = {
    alice: "A.L.I.C.E",
    dynamic_scan: "Dynamic",
    burp_active_scan: "Burp",
    burp_mcp: "Burp MCP",
    deterministic_probe: "Deterministic",
    manual_import: "Imported",
    debug_reporter: "Debug Reporter",
    unknown: "Unknown",
  };
  return labels[source] || String(source || "Unknown").replace(/_/g, " ");
}

export function apiTranscriptText(text) {
  if (!text) return "";
  const value = String(text).trim();
  return value.includes("REQUEST\n") && value.includes("RESPONSE\n") ? value : "";
}

export function markdownText(value) {
  if (value == null) return "";
  if (typeof value === "string") return value.trim();
  if (typeof value === "object") {
    // Flatten content-block shapes ({text}/[{text}]) the LLM sometimes returns
    // so they never render as the literal "[object Object]".
    if (Array.isArray(value)) return value.map(markdownText).filter(Boolean).join("\n").trim();
    if (typeof value.text === "string") return value.text.trim();
    try { return JSON.stringify(value); } catch  { return ""; }
  }
  return String(value).trim();
}

export function markdownListValue(value) {
  const text = markdownText(value);
  return text || "—";
}

export function markdownCodeBlock(value) {
  const text = markdownText(value);
  if (!text) return "—";
  const fence = text.includes("```") ? "````" : "```";
  return `${fence}\n${text}\n${fence}`;
}

export function slugForFilename(value) {
  return String(value || "issues")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "issues";
}

// ── SAST lead export ────────────────────────────────────────────────────────
// Client-side markdown export of leads, mirroring findingsToMarkdown. The
// embedded JSON comment keeps the file round-trippable for a future importer.

export function leadImportPayload(l) {
  return {
    title: l.title, severity: l.severity, category: l.category,
    confidence: l.confidence, location: l.location, description: l.description,
    evidence: l.evidence, status: l.status, note: l.note, source: l.source,
  };
}

export function leadsExportFilename(name, runId) {
  const base = slugForFilename(name || `sast-run-${runId || ""}`);
  return `${base}-leads-${new Date().toISOString().slice(0, 10)}.md`;
}

export function leadsToMarkdown(leads, meta = {}) {
  const sevOrder = {critical:0,high:1,medium:2,low:3,info:4};
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

export function markdownExportFilename(run, siteName) {
  const base = slugForFilename(run?.name || siteName || `run-${run?.id || "issues"}`);
  const date = new Date().toISOString().slice(0, 10);
  return `${base}-issues-${date}.md`;
}

export function downloadTextFile(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function findingsToMarkdown(findings, meta = {}) {
  const sevOrder = {critical:0,high:1,medium:2,low:3,info:4};
  const valOrder = {confirmed:0,validating:1,unvalidated:2,skipped:3,unconfirmed:4,false_positive:5,low_confidence:5};
  const sorted = [...(findings || [])].sort((a, b) => {
    const sev = (sevOrder[a.severity] ?? 99) - (sevOrder[b.severity] ?? 99);
    if (sev !== 0) return sev;
    const val = (valOrder[a.validation_status] ?? 99) - (valOrder[b.validation_status] ?? 99);
    if (val !== 0) return val;
    return String(a.title || "").localeCompare(String(b.title || ""));
  });
  const lines = [
    `# Issue Export${meta.runName ? `: ${meta.runName}` : ""}`,
    "",
  ];
  if (meta.siteName) lines.push(`- Site: ${meta.siteName}`);
  if (meta.generatedAt) lines.push(`- Exported: ${meta.generatedAt.toLocaleString()}`);
  lines.push(`- Total findings: ${sorted.length}`, "");
  lines.push(
    "<!-- aespa-findings-json",
    encodeURIComponent(JSON.stringify(sorted.map(findingImportPayload))),
    "-->",
    "",
  );

  sorted.forEach((f, idx) => {
    lines.push(
      `## ${idx + 1}. ${markdownListValue(f.title)}`,
      "",
      `- Severity: ${markdownListValue(f.severity)}`,
      `- OWASP: ${markdownListValue(f.owasp_category)}`,
      ...(f.owasp_api_category ? [`- OWASP API: ${markdownListValue(f.owasp_api_category)}`] : []),
      `- Source: ${markdownListValue(sourceLabel(f.finding_source))}`,

      `- Validation: ${markdownListValue(f.validation_status)}`,
      `- Affected URL: ${markdownListValue(f.affected_url)}`,
      `- CVSS: ${markdownListValue(f.cvss_score)}${f.cvss_vector ? ` (${f.cvss_vector})` : ""}`,
      "",
      "### Description",
      markdownListValue(f.description),
      "",
      "### Impact",
      markdownListValue(f.impact),
      "",
      "### Likelihood",
      markdownListValue(f.likelihood),
      "",
      "### Recommendation",
      markdownListValue(f.recommendation),
      "",
      "### Evidence",
      markdownCodeBlock(f.evidence || f.response_evidence || f.request_evidence),
      "",
    );
    if (f.request_evidence) {
      lines.push("### Request Evidence", markdownCodeBlock(f.request_evidence), "");
    }
    if (f.response_evidence) {
      lines.push("### Response Evidence", markdownCodeBlock(f.response_evidence), "");
    }
    if (f.validation_note) {
      lines.push("### Validation Note", markdownListValue(f.validation_note), "");
    }
    if (f.poc_command) {
      lines.push("### Validation Command", markdownCodeBlock(f.poc_command), "");
    }
    if (f.poc_setup) {
      lines.push("### Validation Setup", f.poc_setup, "");
    }
    const mergedInstances = (() => {
      try { return JSON.parse(f.merged_instances || "[]"); } catch  { return []; }
    })();
    if (mergedInstances.length > 0) {
      lines.push("### Additional Instances", "");
      mergedInstances.forEach((inst, idx) => {
        lines.push(`- **Instance ${idx + 2}:** \`${inst.url || "\u2014"}\``);
        const ev = inst.request_evidence || inst.evidence;
        if (ev) lines.push("", markdownCodeBlock(ev), "");
      });
      lines.push("");
    }
  });

  return lines.join("\n");
}

export const WP_STATUS_MARK = { not_started:"·", in_progress:"~", covered:"✓", finding:"⚠", skipped:"s" };

// Render a work-program coverage matrix (web pages or API endpoints) as Markdown.
export function workProgramToMarkdown(matrix, { cats, labels = {}, kind = "web", runName, generatedAt } = {}) {
  const rows = kind === "api" ? (matrix?.endpoints || []) : (matrix?.pages || []);
  const totals = matrix?.totals || {};
  const totalCells = Object.values(totals).reduce((a, b) => a + b, 0);
  const coveredCount = (totals.covered||0) + (totals.finding||0) + (totals.skipped||0);
  const pct = totalCells > 0 ? Math.round(coveredCount / totalCells * 100) : 0;

  const lines = [`# OWASP Coverage${runName ? `: ${runName}` : ""} (${kind === "api" ? "API" : "Web"})`, ""];
  if (generatedAt) lines.push(`- Exported: ${generatedAt.toLocaleString()}`);
  lines.push(`- Coverage: ${pct}% (${coveredCount}/${totalCells} cells)`);
  lines.push("- Status counts: " + ["not_started","in_progress","covered","finding","skipped"].map(s => `${s} ${totals[s]||0}`).join(", "));
  lines.push("");
  lines.push("Legend: ✓ covered · ~ in progress · ⚠N finding(s) · s skipped · · not started · — n/a", "");
  lines.push("Categories: " + cats.map(c => `${c} ${labels[c]||""}`.trim()).join(" · "), "");

  const header = [kind === "api" ? "Endpoint" : "Page", ...cats];
  lines.push("| " + header.join(" | ") + " |");
  lines.push("| " + header.map(() => "---").join(" | ") + " |");
  rows.forEach(row => {
    const label = kind === "api" ? `\`${row.method} ${row.path}\`` : `\`${row.url}\``;
    const cells = cats.map(cat => {
      const cell = row.cells?.[cat];
      if (!cell) return "—";
      if (cell.status === "finding") return `⚠${(cell.finding_ids||[]).length || ""}`;
      return WP_STATUS_MARK[cell.status] || cell.status;
    });
    lines.push("| " + [label, ...cells].join(" | ") + " |");
  });
  lines.push("");

  const findingRows = [];
  rows.forEach(row => cats.forEach(cat => {
    (row.cells?.[cat]?.findings || []).forEach(f =>
      findingRows.push({ loc: kind === "api" ? `${row.method} ${row.path}` : row.url, cat, f }));
  }));
  if (findingRows.length) {
    lines.push("## Findings by cell", "");
    findingRows.forEach(({ loc, cat, f }) =>
      lines.push(`- **${cat}** \`${loc}\` — [${f.severity||"info"}] ${f.title} (#${f.id}${f.validation_status ? `, ${f.validation_status}` : ""})`));
    lines.push("");
  }

  return lines.join("\n");
}

export function findingImportPayload(f) {
  return {
    owasp_category: f.owasp_category || "A00",
    severity: f.severity || "info",
    title: f.title || "Imported finding",
    description: f.description || "",
    impact: f.impact || "",
    likelihood: f.likelihood || "",
    recommendation: f.recommendation || "",
    cvss_score: Number(f.cvss_score) || 0,
    cvss_vector: f.cvss_vector || "",
    affected_url: f.affected_url || "",
    evidence: f.evidence || "",
    request_evidence: f.request_evidence || "",
    response_evidence: f.response_evidence || "",
    finding_source: f.finding_source || "manual_import",
    validation_status: f.validation_status || "unvalidated",
    validation_note: f.validation_note || null,
    merged_instances: f.merged_instances || "[]",
    poc_command: f.poc_command || "",
    poc_setup: f.poc_setup || "",
  };
}

export function parseFindingsMarkdown(markdown) {
  const text = String(markdown || "");
  const embedded = text.match(/<!--\s*aespa-findings-json\s+([\s\S]*?)\s+-->/);
  if (embedded) {
    const parsed = JSON.parse(decodeURIComponent(embedded[1].trim()));
    if (Array.isArray(parsed)) return parsed.map(findingImportPayload);
  }
  return parseFindingsMarkdownSections(text);
}

export function parseFindingsMarkdownSections(markdown) {
  const matches = [...markdown.matchAll(/^##\s+\d+\.\s+(.+)$/gm)];
  return matches.map((match, idx) => {
    const start = match.index + match[0].length;
    const end = idx + 1 < matches.length ? matches[idx + 1].index : markdown.length;
    const block = markdown.slice(start, end);
    const cvss = markdownBullet(block, "CVSS");
    const cvssMatch = cvss.match(/^([0-9.]+)(?:\s+\((.*)\))?$/);
    return findingImportPayload({
      title: match[1],
      severity: markdownBullet(block, "Severity"),
      owasp_category: markdownBullet(block, "OWASP"),
      finding_source: markdownBullet(block, "Source") || "manual_import",
      validation_status: markdownBullet(block, "Validation"),
      affected_url: markdownBullet(block, "Affected URL"),
      cvss_score: cvssMatch ? parseFloat(cvssMatch[1]) : 0,
      cvss_vector: cvssMatch?.[2] || "",
      description: markdownSection(block, "Description"),
      impact: markdownSection(block, "Impact"),
      likelihood: markdownSection(block, "Likelihood"),
      recommendation: markdownSection(block, "Recommendation"),
      evidence: stripMarkdownFence(markdownSection(block, "Evidence")),
      request_evidence: stripMarkdownFence(markdownSection(block, "Request Evidence")),
      response_evidence: stripMarkdownFence(markdownSection(block, "Response Evidence")),
      validation_note: markdownSection(block, "Validation Note") || null,
      poc_command: stripMarkdownFence(markdownSection(block, "Validation Command")),
      poc_setup: markdownSection(block, "Validation Setup"),
    });
  });
}

export function markdownBullet(block, label) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = block.match(new RegExp(`^- ${escaped}: (.*)$`, "m"));
  const value = match?.[1]?.trim() || "";
  return value === "—" ? "" : value;
}

export function markdownSection(block, title) {
  const escaped = title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = block.match(new RegExp(`### ${escaped}\\n([\\s\\S]*?)(?=\\n### |$)`));
  const value = match?.[1]?.trim() || "";
  return value === "—" ? "" : value;
}

export function stripMarkdownFence(value) {
  const text = markdownText(value);
  const match = text.match(/^(`{3,4})\n([\s\S]*)\n\1$/);
  return match ? match[2] : text;
}

