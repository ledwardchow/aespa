export function CoverageStatusBadges({
  mode = "track",
  percent,
  covered,
  total,
  live,
  enforce,
  unitLabel = "cells",
}) {
  const modeLabel =
    mode === "enforce"
      ? "Full"
      : mode === "standard"
        ? "Standard"
        : mode === "deep"
          ? "Deep"
          : mode === "team"
            ? "Team"
            : mode === "sast_validate"
              ? "SAST Validate"
              : "Quick";
  return (
    <>
      <span className={"badge " + (mode === "enforce" ? "warning" : "neutral")}>
        {modeLabel} mode
      </span>
      <span className="badge neutral">
        {percent == null
          ? "Coverage unavailable"
          : `${percent}% coverage (${covered}/${total} ${unitLabel})`}
      </span>
      {live && <span className="badge warning">● Live</span>}
      {enforce && enforce.phase !== "complete" && (
        <span className="badge warning" title="Full mode is resolving remaining coverage cells">
          Completing full coverage…{" "}
          {enforce.resolved != null
            ? `${enforce.resolved}/${enforce.total}`
            : `${enforce.remaining} left`}
        </span>
      )}
      {enforce?.phase === "complete" && (
        <span className="badge success" title={enforce.message || ""}>
          Full coverage done · {enforce.covered || 0} covered, {enforce.skipped || 0} skipped
          {enforce.budget_exhausted ? " (budget hit)" : ""}
        </span>
      )}
    </>
  );
}
