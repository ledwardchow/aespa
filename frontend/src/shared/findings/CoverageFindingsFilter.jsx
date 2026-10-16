import { runHref } from "../navigation/links.ts";

export function filterCoverageFindings(findings, findingIds) {
  if (!findingIds?.length) return findings;
  const ids = new Set(findingIds);
  return findings.filter((finding) => ids.has(finding.id));
}

export function CoverageFindingsFilter({
  runKind,
  runId,
  findingIds,
  coverageReturn,
  visibleCount,
}) {
  if (!findingIds?.length) return null;
  const coverageHref =
    runHref({ runKind, runId }, runKind === "api" ? "workprogram" : "attack") +
    (runKind === "api"
      ? ""
      : coverageReturn === "workflows"
        ? "?subtab=owasp&coverage=workflows"
        : "?subtab=owasp");
  return (
    <div className="coverage-findings-filter" role="status">
      <span>
        Showing {visibleCount} finding{visibleCount === 1 ? "" : "s"} for this coverage cell.
      </span>
      <a href={coverageHref}>Back to coverage</a>
      <a href={runHref({ runKind, runId }, "findings")}>Show all findings</a>
    </div>
  );
}
