import { Fragment } from "react";
import { renderMarkdown } from "../alice/markdown.jsx";
import type { Finding } from "./contracts.ts";

type Detail = Pick<
  Finding,
  | "description"
  | "impact"
  | "likelihood"
  | "recommendation"
  | "cvss_score"
  | "cvss_vector"
  | "severity"
>;
const sections = [
  ["description", "Description"],
  ["impact", "Impact"],
  ["likelihood", "Likelihood"],
  ["recommendation", "Recommendation"],
] as const;

export function FindingDetails({ finding }: { finding: Detail }) {
  return (
    <div className="finding-description">
      {sections.map(([field, title], index) => (
        <Fragment key={field}>
          <div style={index ? { marginTop: 8 } : undefined}>
            <strong>{title}</strong>
          </div>
          <div>{renderMarkdown(finding[field]) || "-"}</div>
        </Fragment>
      ))}
      <div style={{ marginTop: 8 }}>
        <strong>CVSS 3.1</strong>
      </div>
      <div>
        {finding.cvss_score !== undefined && finding.cvss_score !== null
          ? `${Number(finding.cvss_score).toFixed(1)} (${finding.severity})`
          : "-"}
        {finding.cvss_vector ? (
          <span className="mono" style={{ marginLeft: 8, fontSize: 11 }}>
            {finding.cvss_vector}
          </span>
        ) : (
          ""
        )}
      </div>
    </div>
  );
}
