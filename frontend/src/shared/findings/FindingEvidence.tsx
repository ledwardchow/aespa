import type { MouseEvent } from "react";
import type { Finding } from "./contracts.ts";

type EvidenceItem = { type?: string; label?: string; value?: string };
type Instance = {
  url?: string;
  evidence?: string;
  request_evidence?: string;
  response_evidence?: string;
};

export const RETRYABLE_VALIDATION = new Set([
  "unvalidated",
  "skipped",
  "unconfirmed",
  "false_positive",
  "low_confidence",
]);

function evidenceItems(finding: Finding): EvidenceItem[] {
  let items: unknown = finding.evidence_items;
  if (!Array.isArray(items)) {
    try {
      items = JSON.parse(finding.evidence_json || "[]");
    } catch {
      items = [];
    }
  }
  if (!Array.isArray(items)) return [];
  // The verdict and reasoning are already shown in the validation note.
  return (items as EvidenceItem[]).filter(
    (item) => item && item.type !== "validation_verdict" && item.type !== "validation_reasoning",
  );
}

function mergedInstances(finding: Finding): Instance[] {
  try {
    const parsed: unknown = JSON.parse(finding.merged_instances || "[]");
    return Array.isArray(parsed) ? (parsed as Instance[]) : [];
  } catch {
    return [];
  }
}

function RawEvidence({ item }: { item: Instance | Finding }) {
  if (item.request_evidence || item.response_evidence)
    return (
      <>
        {item.request_evidence && (
          <pre className="finding-evidence">
            {"REQUEST:\n"}
            {item.request_evidence}
          </pre>
        )}
        {item.response_evidence && (
          <pre className="finding-evidence">
            {"RESPONSE:\n"}
            {item.response_evidence}
          </pre>
        )}
      </>
    );
  return item.evidence ? <pre className="finding-evidence">{item.evidence}</pre> : null;
}

/** Validation notes, proof commands, evidence, screenshots and merged instances. */
export function FindingEvidence({
  finding,
  onValidate,
}: {
  finding: Finding;
  onValidate?: (event: MouseEvent, findingId: number) => void;
}) {
  const items = evidenceItems(finding);
  const instances = mergedInstances(finding);
  // Skip the raw request/response dump when structured evidence already shows it.
  const hasStructuredHttp = items.some(
    (item) => item.type === "http_request" || item.type === "http_response",
  );
  return (
    <>
      {finding.validation_note && (
        <div className={"finding-validation-note val-note-" + finding.validation_status}>
          <strong>Validation ({finding.validation_status}):</strong> {finding.validation_note}
        </div>
      )}
      {onValidate && RETRYABLE_VALIDATION.has(finding.validation_status) && (
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn secondary sm" onClick={(e) => onValidate(e, finding.id)}>
            Retry validation
          </button>
        </div>
      )}
      {finding.poc_command && (
        <div className="finding-poc" style={{ marginTop: 12 }}>
          <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
            <strong>Validation Command (verified)</strong>
            <button
              className="btn ghost sm"
              title="Copy command"
              onClick={(e) => {
                e.stopPropagation();
                navigator.clipboard?.writeText(finding.poc_command);
              }}
            >
              Copy
            </button>
          </div>
          <pre className="finding-evidence">{finding.poc_command}</pre>
          {finding.poc_setup && (
            <details style={{ marginTop: 4 }}>
              <summary className="finding-affected-label" style={{ cursor: "pointer" }}>
                Setup (capture an authenticated session)
              </summary>
              <pre className="finding-evidence" style={{ whiteSpace: "pre-wrap" }}>
                {finding.poc_setup}
              </pre>
            </details>
          )}
        </div>
      )}
      {items.length > 0 && (
        <div className="structured-evidence">
          {items.map((item, index) => (
            <div
              key={index}
              className={"structured-evidence-item evidence-type-" + (item.type || "note")}
            >
              <div className="structured-evidence-label">
                <span>{item.label || item.type || "Evidence"}</span>
              </div>
              <pre className="structured-evidence-value">{item.value}</pre>
            </div>
          ))}
        </div>
      )}
      {!hasStructuredHttp && <RawEvidence item={finding} />}
      {finding.screenshot_b64 && (
        <div className="finding-screenshot-wrap">
          <div className="finding-affected-label">Screenshot</div>
          <img
            src={"data:image/png;base64," + finding.screenshot_b64}
            className="finding-screenshot"
            alt="proof screenshot"
          />
        </div>
      )}
      {instances.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <strong>Additional Affected Instances ({instances.length})</strong>
          {instances.map((instance, index) => (
            <div
              key={index}
              style={{
                marginTop: 8,
                paddingLeft: 12,
                borderLeft: "2px solid var(--border,#ccc)",
              }}
            >
              <div className="finding-affected-label">Instance {index + 2}</div>
              <span className="mono" style={{ fontSize: 11, wordBreak: "break-all" }}>
                {instance.url || "—"}
              </span>
              <RawEvidence item={instance} />
            </div>
          ))}
        </div>
      )}
    </>
  );
}
