export const WP_STATUS_MARK = {
  not_started: "·",
  in_progress: "~",
  covered: "✓",
  finding: "⚠",
  skipped: "s",
};

export function workProgramToMarkdown(
  matrix,
  { cats, labels = {}, kind = "web", runName, generatedAt } = {},
) {
  const rows = kind === "api" ? matrix?.endpoints || [] : matrix?.pages || [];
  const totals = matrix?.totals || {};
  const totalCells = Object.values(totals).reduce((a, b) => a + b, 0);
  const coveredCount = (totals.covered || 0) + (totals.finding || 0) + (totals.skipped || 0);
  const pct = totalCells > 0 ? Math.round((coveredCount / totalCells) * 100) : 0;

  const lines = [
    `# OWASP Coverage${runName ? `: ${runName}` : ""} (${kind === "api" ? "API" : "Web"})`,
    "",
  ];
  if (generatedAt) lines.push(`- Exported: ${generatedAt.toLocaleString()}`);
  lines.push(`- Coverage: ${pct}% (${coveredCount}/${totalCells} cells)`);
  lines.push(
    "- Status counts: " +
      ["not_started", "in_progress", "covered", "finding", "skipped"]
        .map((s) => `${s} ${totals[s] || 0}`)
        .join(", "),
  );
  lines.push("");
  lines.push(
    "Legend: ✓ covered · ~ in progress · ⚠N finding(s) · s skipped · · not started · — n/a",
    "",
  );
  lines.push("Categories: " + cats.map((c) => `${c} ${labels[c] || ""}`.trim()).join(" · "), "");

  const header = [kind === "api" ? "Endpoint" : "Page", ...cats];
  lines.push("| " + header.join(" | ") + " |");
  lines.push("| " + header.map(() => "---").join(" | ") + " |");
  rows.forEach((row) => {
    const label = kind === "api" ? `\`${row.method} ${row.path}\`` : `\`${row.url}\``;
    const cells = cats.map((cat) => {
      const cell = row.cells?.[cat];
      if (!cell) return "—";
      if (cell.status === "finding") return `⚠${(cell.finding_ids || []).length || ""}`;
      return WP_STATUS_MARK[cell.status] || cell.status;
    });
    lines.push("| " + [label, ...cells].join(" | ") + " |");
  });
  lines.push("");

  const findingRows = [];
  rows.forEach((row) =>
    cats.forEach((cat) => {
      (row.cells?.[cat]?.findings || []).forEach((f) =>
        findingRows.push({ loc: kind === "api" ? `${row.method} ${row.path}` : row.url, cat, f }),
      );
    }),
  );
  if (findingRows.length) {
    lines.push("## Findings by cell", "");
    findingRows.forEach(({ loc, cat, f }) =>
      lines.push(
        `- **${cat}** \`${loc}\` — [${f.severity || "info"}] ${f.title} (${f.reference || `#${f.id}`}${f.validation_status ? `, ${f.validation_status}` : ""})`,
      ),
    );
    lines.push("");
  }

  return lines.join("\n");
}
