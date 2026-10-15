import type { Finding } from "./contracts.ts";

export const SECTION_KEYS = {
  unconfirmed: "__unconfirmed__",
  lowConfidence: "__low_confidence__",
  deterministic: "__deterministic__",
} as const;

export type SectionKey = (typeof SECTION_KEYS)[keyof typeof SECTION_KEYS];

export type FindingGroup = {
  /** Expansion key; nested groups are prefixed with their section key. */
  key: string;
  title: string;
  items: Finding[];
  topSeverity: string;
  source: string;
  category: string;
};

export type FindingSections = {
  main: FindingGroup[];
  sections: { key: SectionKey; label: string; groups: FindingGroup[]; count: number }[];
};

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};
const VALIDATION_ORDER: Record<string, number> = {
  confirmed: 0,
  validating: 1,
  unvalidated: 2,
  skipped: 3,
  unconfirmed: 4,
  false_positive: 5,
  low_confidence: 5,
};
const severityRank = (severity: string) => SEVERITY_ORDER[severity] ?? 99;

// The TLS/SSL posture finding is a deterministic probe by origin, but it is a
// first-class A02 finding and belongs in the main list rather than with the
// per-page probe echoes.
const isDeterministicCheck = (finding: Finding) =>
  finding.finding_source === "deterministic_probe" &&
  finding.title !== "TLS/SSL configuration weaknesses";

export function findingSectionKey(finding: Finding): SectionKey | null {
  if (isDeterministicCheck(finding)) return SECTION_KEYS.deterministic;
  if (
    finding.validation_status === "false_positive" ||
    finding.validation_status === "low_confidence"
  )
    return SECTION_KEYS.lowConfidence;
  if (finding.validation_status === "unconfirmed") return SECTION_KEYS.unconfirmed;
  return null;
}

/** Every expansion key that must be open for this finding's row to be visible. */
export function findingGroupKeys(finding: Finding): string[] {
  const section = findingSectionKey(finding);
  return section ? [section, `${section}:${finding.title}`] : [finding.title];
}

export function findingSource(finding: Finding): string {
  const label = finding.origin?.label;
  return (typeof label === "string" && label) || finding.finding_source || "unknown";
}

export function findingCategory(finding: Finding): string {
  return finding.owasp_api_category || finding.owasp_category || "";
}

function makeGroups(findings: Finding[], keyPrefix = ""): FindingGroup[] {
  const byTitle = new Map<string, Finding[]>();
  for (const finding of findings) {
    const items = byTitle.get(finding.title) || [];
    items.push(finding);
    byTitle.set(finding.title, items);
  }
  return [...byTitle.entries()]
    .map(([title, items]) => {
      const sorted = [...items].sort((a, b) => {
        const byValidation =
          (VALIDATION_ORDER[a.validation_status] ?? 2) -
          (VALIDATION_ORDER[b.validation_status] ?? 2);
        return byValidation || severityRank(a.severity) - severityRank(b.severity);
      });
      const topSeverity = items.reduce(
        (top, finding) =>
          severityRank(finding.severity) < severityRank(top) ? finding.severity : top,
        items[0].severity,
      );
      return {
        key: keyPrefix ? `${keyPrefix}:${title}` : title,
        title,
        items: sorted,
        topSeverity,
        source: findingSource(items[0]),
        category: findingCategory(items[0]),
      };
    })
    .sort((a, b) => severityRank(a.topSeverity) - severityRank(b.topSeverity));
}

const SECTION_LABELS: [SectionKey, string][] = [
  [SECTION_KEYS.unconfirmed, "Unconfirmed"],
  [SECTION_KEYS.lowConfidence, "Low confidence"],
  [SECTION_KEYS.deterministic, "Deterministic checks"],
];

/** Groups findings by title: main findings first, then the labelled sections. */
export function groupFindings(findings: Finding[]): FindingSections {
  const main: Finding[] = [];
  const bySection = new Map<SectionKey, Finding[]>();
  for (const finding of findings) {
    const section = findingSectionKey(finding);
    if (!section) main.push(finding);
    else bySection.set(section, [...(bySection.get(section) || []), finding]);
  }
  return {
    main: makeGroups(main),
    sections: SECTION_LABELS.filter(([key]) => bySection.has(key)).map(([key, label]) => {
      const items = bySection.get(key) || [];
      return { key, label, groups: makeGroups(items, key), count: items.length };
    }),
  };
}
