import { runHref } from "../navigation/links.ts";
import { useState } from "react";

function labelForOrigin(origin) {
  if (!origin) return null;
  return origin.label || origin.type || null;
}

/**
 * A compact public finding/lead reference with a keyboard-accessible preview.
 * The link remains a normal anchor so browser navigation and copy-link work.
 */
export function FindingReferenceLink({
  reference,
  title,
  description,
  severity,
  cvss_score,
  validation_status,
  validation_note,
  finding_source,
  origin,
  validated_by,
  runReference,
  href,
  className = "",
  kind = "Finding",
  onClick,
}) {
  const [active, setActive] = useState(false);
  const ref = reference || "—";
  const originLabel = labelForOrigin(origin);
  const validatedByLabel = labelForOrigin(validated_by);
  const originHref =
    origin?.type === "sast" && origin.run_id && origin.reference
      ? runHref({ runKind: "sast", runId: origin.run_id }, "candidates", { lead: origin.reference })
      : null;

  return (
    <span
      className={`finding-reference-anchor ${className}`.trim()}
      onMouseEnter={() => setActive(true)}
      onMouseLeave={() => setActive(false)}
      onFocus={() => setActive(true)}
      onBlur={() => setActive(false)}
    >
      {href ? (
        <a
          className="finding-reference-link"
          href={href}
          onClick={(event) => {
            event.stopPropagation();
            onClick?.(event);
          }}
          aria-label={`${kind} ${ref}${title ? `: ${title}` : ""}`}
        >
          {ref}
        </a>
      ) : (
        <button
          type="button"
          className="finding-reference-link finding-reference-button"
          onClick={(event) => {
            event.stopPropagation();
            onClick?.(event);
          }}
          aria-label={`${kind} ${ref}${title ? `: ${title}` : ""}`}
        >
          {ref}
        </button>
      )}
      {active && reference && (
        <span className="finding-reference-popover" role="tooltip">
          <span className="finding-reference-popover-title">{title || `${kind} ${ref}`}</span>
          <span className="finding-reference-popover-meta">
            {severity && <span className={`sev-badge sev-${severity}`}>{severity}</span>}
            {cvss_score != null && <span>CVSS {cvss_score}</span>}
            {validation_status && <span>{validation_status}</span>}
          </span>
          {description && (
            <span className="finding-reference-popover-description">{description}</span>
          )}
          {validation_note && (
            <span className="finding-reference-popover-note">Validation: {validation_note}</span>
          )}
          {finding_source && (
            <span className="finding-reference-popover-note">Source: {finding_source}</span>
          )}
          {originLabel && (
            <span className="finding-reference-popover-note">
              Origin: {originLabel}
              {origin.reference ? (
                <>
                  {" "}
                  · {originHref ? <a href={originHref}>{origin.reference}</a> : origin.reference}
                </>
              ) : (
                ""
              )}
            </span>
          )}
          {validatedByLabel && (
            <span className="finding-reference-popover-note">Validated by: {validatedByLabel}</span>
          )}
          {runReference && runReference !== reference && (
            <span className="finding-reference-popover-note">Run reference: {runReference}</span>
          )}
        </span>
      )}
    </span>
  );
}

export function LeadReferenceLink(props) {
  return <FindingReferenceLink {...props} kind="Lead" />;
}
