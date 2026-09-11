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
  | "affected_url"
  | "evidence"
>;
const webSections = [
  ["description", "Description"],
  ["impact", "Impact"],
  ["likelihood", "Likelihood"],
  ["recommendation", "Recommendation"],
] as const;

export function FindingDetails({ finding, runKind }: { finding: Detail; runKind: "web" | "api" }) {
  if (runKind === "web")
    return (
      <div className="finding-description">
        {webSections.map(([field, title], index) => (
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
  return (
    <>
      {finding.affected_url && (
        <div style={{ marginBottom: 8 }}>
          <b>URL:</b> <code style={{ fontSize: 12 }}>{finding.affected_url}</code>
        </div>
      )}
      {finding.description && (
        <div style={{ marginBottom: 8 }}>
          <b>Description:</b>
          <div style={{ marginTop: 4 }}>{renderMarkdown(finding.description)}</div>
        </div>
      )}
      {(
        [
          ["impact", "Impact"],
          ["recommendation", "Recommendation"],
        ] as const
      ).map(([field, title]) =>
        finding[field] ? (
          <div key={field} style={{ marginBottom: 8 }}>
            <b>{title}:</b> {finding[field]}
          </div>
        ) : null,
      )}
      {finding.evidence && (
        <div style={{ marginBottom: 8 }}>
          <b>Evidence:</b>
          <pre
            style={{
              fontSize: 11,
              background: "var(--code-bg,#1e1e2e)",
              color: "var(--code-fg,#cdd6f4)",
              padding: 8,
              borderRadius: 4,
              overflow: "auto",
              maxHeight: 200,
              whiteSpace: "pre-wrap",
            }}
          >
            {finding.evidence}
          </pre>
        </div>
      )}
    </>
  );
}
