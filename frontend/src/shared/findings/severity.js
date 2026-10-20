const SEVERITY_RANK = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };

export function normalizeSeverity(value, fallback = "info") {
  const severity = String(value || fallback)
    .trim()
    .toLowerCase();
  return severity === "informational" ? "info" : severity;
}

export function severityRank(value, fallback = "info") {
  return SEVERITY_RANK[normalizeSeverity(value, fallback)] ?? -1;
}
