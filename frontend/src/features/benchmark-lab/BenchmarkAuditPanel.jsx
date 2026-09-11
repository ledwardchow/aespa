function checkStatus(value) {
  if (value && typeof value === "object") return checkStatus(value.status);
  if (value === true || value === "valid" || value === "pass" || value === "passed") return "pass";
  if (value === false || value === "contaminated" || value === "fail" || value === "failed")
    return "fail";
  return "warning";
}

export function BenchmarkAuditPanel({ evaluation }) {
  const rawChecks = evaluation?.blindness_checks_json || evaluation?.blindness_checks || {};
  const checks = parseJson(rawChecks);
  const entries = Array.isArray(checks)
    ? checks
    : Object.entries(checks).map(([name, value]) => ({ name, value }));
  const status = evaluation?.blindness_status || evaluation?.status;
  return (
    <div className="benchmark-audit-layout">
      <div className={`benchmark-blindness ${status || "warning"}`}>
        <strong>{status || "pending"}</strong>
        <span>Blindness and provenance status</span>
      </div>
      <div className="benchmark-audit-list">
        {entries.length ? (
          entries.map((check) => {
            const value = check.value ?? check.status;
            return (
              <div className="benchmark-audit-row" key={check.name || check.key}>
                <span className={`audit-check ${checkStatus(value)}`}>
                  {checkStatus(value) === "pass" ? "✓" : checkStatus(value) === "fail" ? "!" : "•"}
                </span>
                <span>{check.name || check.key}</span>
                <small>
                  {typeof value === "object"
                    ? value.reason || value.status || "Needs review"
                    : typeof value === "string"
                      ? value
                      : value
                        ? "Passed"
                        : "Needs review"}
                </small>
              </div>
            );
          })
        ) : (
          <div className="subtle">No audit checks recorded yet.</div>
        )}
      </div>
      <dl className="benchmark-provenance">
        <dt>Source digest</dt>
        <dd>
          {parseJson(evaluation?.run_provenance_json)?.source_archive_digest ||
            evaluation?.source_digest ||
            "—"}
        </dd>
        <dt>Matching version</dt>
        <dd>{evaluation?.matching_version || "—"}</dd>
        <dt>Created</dt>
        <dd>{evaluation?.created_at ? new Date(evaluation.created_at).toLocaleString() : "—"}</dd>
      </dl>
    </div>
  );
}

function parseJson(value) {
  if (value && typeof value === "object") return value;
  try {
    return JSON.parse(value || "{}");
  } catch {
    return {};
  }
}
