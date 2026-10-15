import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent } from "react";
import { useColResize } from "../hooks/useColResize.js";
import { FindingReferenceLink } from "../ui/FindingReferenceLink.jsx";
import type { Finding } from "./contracts.ts";
import { FindingDetails } from "./FindingDetails.tsx";
import { FindingEditor } from "./FindingEditor.tsx";
import { FindingEvidence, RETRYABLE_VALIDATION } from "./FindingEvidence.tsx";
import { sourceLabel } from "./files.js";
import { findingGroupKeys, groupFindings, SECTION_KEYS } from "./findingGroups.ts";
import type { FindingGroup } from "./findingGroups.ts";
import type { FindingEditorState } from "./useFindingEditor.ts";

const COLUMN_COUNT = 6;

function cleanReference(value: string | null | undefined) {
  const reference = value?.trim();
  return reference ? reference.replace(/[.,;:!?]+$/, "") : "";
}

function ValidationBadge({ status }: { status: string }) {
  if (status === "confirmed") return <span className="val-badge val-confirmed">confirmed</span>;
  if (status === "unconfirmed")
    return <span className="val-badge val-unconfirmed">unconfirmed</span>;
  if (status === "skipped") return <span className="val-badge val-skipped">not validated</span>;
  if (status === "false_positive" || status === "low_confidence")
    return <span className="val-badge val-fp">low confidence</span>;
  if (status === "validating") return <span className="val-badge val-validating">…</span>;
  return null;
}

export type FindingsListProps = {
  findings: Finding[];
  runKind: "web" | "api";
  /** Link for a finding's reference, e.g. `#/runs/7/findings?finding=F-1`. */
  findingHref: (reference: string) => string;
  /** Owned by the tab so a draft survives collapsing a row or switching tabs. */
  editor: FindingEditorState;
  emptyMessage: string;
  initialFindingRef?: string | null;
  /** Collapse every row and group whenever this value changes. */
  collapseToken?: number;
  onDeleteFinding: (findingId: number) => Promise<unknown> | void;
  /** Resolve true when the group was deleted. Omit to hide group delete. */
  onDeleteGroup?: (title: string) => Promise<boolean>;
  /** Omit when the run type cannot validate a single finding. */
  onValidateFinding?: (event: MouseEvent, findingId: number) => void;
};

/** The findings table shared by web and API runs: grouped by title, with labelled sections. */
export function FindingsList({
  findings,
  runKind,
  findingHref,
  editor,
  emptyMessage,
  initialFindingRef,
  collapseToken,
  onDeleteFinding,
  onDeleteGroup,
  onValidateFinding,
}: FindingsListProps) {
  const [expandedFinding, setExpandedFinding] = useState<number | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    () => new Set([SECTION_KEYS.unconfirmed]),
  );
  const [columnWidths, startResize] = useColResize("colw:findings:v3", [
    120,
    140,
    null,
    96,
    52,
    96,
  ]) as [(number | null)[], (index: number, event: MouseEvent) => void];
  const { main, sections } = useMemo(() => groupFindings(findings), [findings]);

  const openGroups = (finding: Finding) =>
    setExpandedGroups((previous) => new Set([...previous, ...findingGroupKeys(finding)]));
  const toggleGroup = (key: string) =>
    setExpandedGroups((previous) => {
      const next = new Set(previous);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  // Open a deep-linked finding once, when it first appears.
  const linkedRef = useRef<string | null>(null);
  useEffect(() => {
    const wanted = cleanReference(initialFindingRef);
    if (!wanted || linkedRef.current === wanted) return;
    const match = findings.find((finding) => cleanReference(finding.reference) === wanted);
    if (!match) return;
    linkedRef.current = wanted;
    setExpandedFinding(match.id);
    setExpandedGroups((previous) => new Set([...previous, ...findingGroupKeys(match)]));
  }, [findings, initialFindingRef]);

  const lastCollapseToken = useRef(collapseToken);
  useEffect(() => {
    if (lastCollapseToken.current === collapseToken) return;
    lastCollapseToken.current = collapseToken;
    setExpandedFinding(null);
    setExpandedGroups(new Set());
  }, [collapseToken]);

  if (findings.length === 0)
    return (
      <div className="subtle" style={{ padding: 24, textAlign: "center" }}>
        {emptyMessage}
      </div>
    );

  const onEdit = (event: MouseEvent, finding: Finding) => {
    event.stopPropagation();
    setExpandedFinding(finding.id);
    openGroups(finding);
    editor.edit(finding);
  };
  const onDelete = async (event: MouseEvent, findingId: number) => {
    event.stopPropagation();
    await onDeleteFinding(findingId);
    setExpandedFinding((current) => (current === findingId ? null : current));
  };
  const onDeleteTitle = async (event: MouseEvent, title: string) => {
    event.stopPropagation();
    if (!onDeleteGroup || !(await onDeleteGroup(title))) return;
    setExpandedGroups((previous) => {
      const next = new Set(previous);
      next.delete(title);
      return next;
    });
  };

  const renderFinding = (finding: Finding) => {
    const open = expandedFinding === finding.id;
    const editing = editor.editingId === finding.id;
    return (
      <Fragment key={finding.id}>
        <tr
          className="finding-instance-row"
          onClick={() => {
            if (!editing) setExpandedFinding(open ? null : finding.id);
          }}
        >
          <td className="finding-reference-cell">
            <FindingReferenceLink
              reference={finding.reference}
              title={finding.title}
              description={finding.description}
              severity={finding.severity}
              cvss_score={finding.cvss_score}
              validation_status={finding.validation_status}
              validation_note={finding.validation_note}
              finding_source={finding.finding_source}
              origin={finding.origin}
              validated_by={finding.validated_by}
              href={findingHref(finding.reference || "")}
            />
            <ValidationBadge status={finding.validation_status} />
          </td>
          <td></td>
          <td colSpan={3}>
            <span className="instance-chevron">{open ? "▾" : "▸"}</span>
            <span className="finding-affected-label" style={{ marginRight: 6 }}>
              Affected URL
            </span>
            <span className="mono" style={{ fontSize: 11, wordBreak: "break-all" }}>
              {finding.affected_url || "—"}
            </span>
          </td>
          <td>
            <div className="row" style={{ gap: 4, justifyContent: "flex-end" }}>
              {onValidateFinding && RETRYABLE_VALIDATION.has(finding.validation_status) && (
                <button
                  className="btn ghost sm finding-del-btn"
                  title="Validate finding"
                  onClick={(event) => onValidateFinding(event, finding.id)}
                >
                  ✓
                </button>
              )}
              <button
                className="btn ghost sm finding-del-btn"
                title="Edit finding"
                onClick={(event) => onEdit(event, finding)}
              >
                ✎
              </button>
              <button
                className="btn ghost sm finding-del-btn"
                title="Delete finding"
                onClick={(event) => onDelete(event, finding.id)}
              >
                🗑
              </button>
            </div>
          </td>
        </tr>
        {open && editing && editor.draft && (
          <tr className="finding-evidence-row">
            <td colSpan={COLUMN_COUNT}>
              <FindingEditor editor={editor} runKind={runKind} />
            </td>
          </tr>
        )}
        {open && !editing && (
          <tr className="finding-evidence-row">
            <td colSpan={COLUMN_COUNT}>
              <FindingDetails finding={finding} />
              <FindingEvidence finding={finding} onValidate={onValidateFinding} />
            </td>
          </tr>
        )}
      </Fragment>
    );
  };

  const renderGroup = (group: FindingGroup, nested: boolean) => (
    <Fragment key={group.key}>
      <tr
        className={"finding-group-row" + (nested ? " finding-group-row--nested" : "")}
        onClick={() => toggleGroup(group.key)}
      >
        <td>
          <span className={"sev-badge sev-" + group.topSeverity}>{group.topSeverity}</span>
        </td>
        <td>
          <span className="source-badge">{sourceLabel(group.source)}</span>
        </td>
        <td className="finding-title">
          <span className="group-chevron">{expandedGroups.has(group.key) ? "▾" : "▸"}</span>
          {group.title}
        </td>
        <td>
          {group.category && <span className="finding-category-badge">{group.category}</span>}
        </td>
        <td>
          <span className="finding-count-badge">{group.items.length}</span>
        </td>
        <td>
          {!nested && onDeleteGroup && (
            <button
              className="btn ghost sm finding-del-btn"
              title="Delete group"
              onClick={(event) => onDeleteTitle(event, group.title)}
            >
              🗑
            </button>
          )}
        </td>
      </tr>
      {expandedGroups.has(group.key) && group.items.map(renderFinding)}
    </Fragment>
  );

  const header = (label: string, index: number) => (
    <th>
      {label}{" "}
      <div
        className="col-rh"
        onMouseDown={(event) => startResize(index, event)}
        onClick={(event) => event.stopPropagation()}
      />
    </th>
  );

  return (
    <div className="findings-table-wrap">
      <table className="findings-table">
        <colgroup>
          {columnWidths.map((width, index) => (
            <col key={index} style={{ width: width != null ? width + "px" : undefined }} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {header("Severity", 0)}
            {header("Source", 1)}
            {header("Title", 2)}
            {header("OWASP", 3)}
            {header("#", 4)}
            <th></th>
          </tr>
        </thead>
        <tbody>
          {main.map((group) => renderGroup(group, false))}
          {sections.map((section) => (
            <Fragment key={section.key}>
              <tr className="finding-section-row" onClick={() => toggleGroup(section.key)}>
                <td colSpan={COLUMN_COUNT}>
                  <span className="group-chevron">
                    {expandedGroups.has(section.key) ? "▾" : "▸"}
                  </span>
                  {section.label}
                  <span className="finding-count-badge">{section.count}</span>
                </td>
              </tr>
              {expandedGroups.has(section.key) &&
                section.groups.map((group) => renderGroup(group, true))}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
