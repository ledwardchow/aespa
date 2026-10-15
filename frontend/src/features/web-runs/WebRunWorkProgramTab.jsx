import * as webRunsApi from "../../shared/api/webRuns.js";
import { useState, useEffect, useCallback } from "react";
import { OWASP_WEB_LABELS } from "./coverageLabels.js";
import { OWASP_WEB_SHORT } from "../../shared/runs/coverage.js";
import { OWASP_WEB_CATEGORIES } from "../../shared/runs/webCoverage.js";

import { workProgramToMarkdown } from "../../shared/runs/coverageExport.js";
import { slugForFilename } from "../../shared/lib/markdown.js";
import { downloadTextFile } from "../../shared/lib/download.js";
import { usePolling } from "../../shared/hooks/usePolling.js";
import { useEventStream } from "../../shared/hooks/useEventStream.js";
import { LoadingState } from "../../shared/ui/LoadingState.jsx";
import { CoverageStatusBadges } from "../../shared/ui/CoverageStatusBadges.jsx";
import { FindingReferenceLink } from "../../shared/ui/FindingReferenceLink.jsx";
import { nav } from "../../shared/navigation/router.js";
import { runHref } from "../../shared/navigation/links.ts";

export function WebRunWorkProgramTab({
  runId,
  run,
  scanRunning,
  reloadKey = 0,
  pagesProgress = null,
}) {
  const [coverageTab, setCoverageTab] = useState("pages");
  const [matrix, setMatrix] = useState(null);
  const [workflowCoverage, setWorkflowCoverage] = useState(null);
  const [workflowError, setWorkflowError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [selectedCell, setSelectedCell] = useState(null);
  const [seedMsg, setSeedMsg] = useState(null);
  const [enforce, setEnforce] = useState(null); // latest enforce_progress event
  const loadMatrix = useCallback(
    () =>
      webRunsApi
        .getWebCoverageMatrix(runId)
        .then((m) => {
          setMatrix(m);
          setLoading(false);
        })
        .catch(() => setLoading(false)),
    [runId],
  );
  const loadWorkflowCoverage = useCallback(
    () =>
      webRunsApi
        .getWorkflowCoverage(runId)
        .then((result) => {
          setWorkflowCoverage(result);
          setWorkflowError(null);
        })
        .catch((error) => setWorkflowError(error.message)),
    [runId],
  );
  usePolling(loadMatrix, { enabled: scanRunning, intervalMs: 5000 });
  usePolling(loadWorkflowCoverage, { enabled: scanRunning, intervalMs: 5000 });
  useEffect(() => {
    if (reloadKey > 0) {
      loadMatrix();
      loadWorkflowCoverage();
    }
  }, [reloadKey, loadMatrix, loadWorkflowCoverage]);

  // SSE live updates — mirrors ApiRunWorkProgramTab.
  useEventStream(
    `/api/test-runs/${runId}/events`,
    {
      onMessage: (ev) => {
        try {
          const d = JSON.parse(ev.data);
          if (d.type === "coverage_update") {
            setMatrix((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                pages: prev.pages.map((pg) => {
                  if (!pg.page_ids.includes(d.page_id) && pg.page_id !== d.page_id) return pg;
                  const cells = {
                    ...pg.cells,
                  };
                  const existing = cells[d.owasp_category] || {
                    status: "not_started",
                    finding_ids: [],
                  };
                  const fids = [...(existing.finding_ids || [])];
                  if (d.finding_id && !fids.includes(d.finding_id)) fids.push(d.finding_id);
                  cells[d.owasp_category] = {
                    ...existing,
                    status: d.status,
                    finding_ids: fids,
                    test_classes: d.test_class
                      ? {
                          ...(existing.test_classes || {}),
                          [d.test_class]: {
                            ...(existing.test_classes?.[d.test_class] || {}),
                            status: d.status,
                          },
                        }
                      : existing.test_classes,
                  };
                  if (d.owasp_category === "A03" && d.test_class) {
                    const classKey = `A03:${d.test_class}`;
                    const classCell = cells[classKey] || {
                      status: "not_started",
                      finding_ids: [],
                    };
                    const classFids = [...(classCell.finding_ids || [])];
                    if (d.finding_id && !classFids.includes(d.finding_id))
                      classFids.push(d.finding_id);
                    cells[classKey] = {
                      ...classCell,
                      status: d.status,
                      finding_ids: classFids,
                    };
                  }
                  return {
                    ...pg,
                    cells,
                  };
                }),
              };
            });
          } else if (d.type === "enforce_progress") {
            setEnforce(d);
            if (d.phase === "complete") {
              loadMatrix();
              loadWorkflowCoverage();
            }
          }
        } catch {}
      },
    },
    { enabled: scanRunning },
  );
  const onSeed = async () => {
    setSeeding(true);
    setSeedMsg(null);
    try {
      const r = await webRunsApi.seedWebWorkprogram(runId);
      setSeedMsg(
        r.created > 0
          ? `Added ${r.created} new cell${r.created !== 1 ? "s" : ""}.`
          : "No new cells — OWASP Coverage is up to date.",
      );
      await loadMatrix();
    } catch (e) {
      setSeedMsg("Error: " + e.message);
    } finally {
      setSeeding(false);
    }
  };
  const onExportMarkdown = () => {
    const exportColumns =
      matrix?.columns || OWASP_WEB_CATEGORIES.map((key) => ({ key, label: OWASP_WEB_LABELS[key] }));
    const md = workProgramToMarkdown(
      {
        ...matrix,
        totals: matrix?.column_totals || matrix?.totals,
      },
      {
        cats: exportColumns.map((column) => column.key),
        labels: Object.fromEntries(exportColumns.map((column) => [column.key, column.label])),
        kind: "web",
        runName: run?.name,
        generatedAt: new Date(),
      },
    );
    downloadTextFile(
      `${slugForFilename(run?.name || `web-run-${runId}`)}-owasp-coverage-${new Date().toISOString().slice(0, 10)}.md`,
      md,
      "text/markdown;charset=utf-8",
    );
  };

  const columns =
    matrix?.columns ||
    OWASP_WEB_CATEGORIES.map((key) => ({
      key,
      category: key,
      test_class: null,
      label: OWASP_WEB_LABELS[key],
    }));
  const totals = matrix?.column_totals || matrix?.totals || {};
  const totalCells = Object.values(totals).reduce((a, b) => a + b, 0);
  const coveredCount = (totals.covered || 0) + (totals.finding || 0) + (totals.skipped || 0);
  const pct = totalCells > 0 ? Math.round((coveredCount / totalCells) * 100) : 0;
  const effectiveCoverageMode = matrix?.coverage_mode || run?.coverage_mode || "track";
  return (
    <div
      className="run-work-program-tab"
      style={{
        padding: 16,
      }}
    >
      <div className="coverage-view-switch" role="tablist" aria-label="OWASP coverage views">
        <button
          className={"coverage-view-btn" + (coverageTab === "pages" ? " active" : "")}
          role="tab"
          aria-selected={coverageTab === "pages"}
          onClick={() => setCoverageTab("pages")}
        >
          Pages
        </button>
        <button
          className={"coverage-view-btn" + (coverageTab === "workflows" ? " active" : "")}
          role="tab"
          aria-selected={coverageTab === "workflows"}
          onClick={() => {
            setCoverageTab("workflows");
            loadWorkflowCoverage();
          }}
        >
          Workflows
        </button>
      </div>
      {coverageTab === "pages" && pagesProgress}
      {coverageTab === "pages" &&
        (loading ? (
          <LoadingState label="Loading page coverage…" />
        ) : (
          <div className="page-coverage-panel" role="tabpanel" aria-label="Page coverage">
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                marginBottom: 12,
                flexWrap: "wrap",
              }}
            >
              <h3
                style={{
                  margin: 0,
                }}
              >
                Page coverage
              </h3>
              <CoverageStatusBadges
                mode={effectiveCoverageMode}
                percent={pct}
                covered={coveredCount}
                total={totalCells}
                live={scanRunning}
                enforce={enforce}
              />
              {matrix?.pages?.length > 0 && (
                <button className="btn sm" onClick={onExportMarkdown}>
                  Export Markdown
                </button>
              )}
              <button className="btn sm" disabled={seeding} onClick={onSeed}>
                {seeding ? "Populating…" : "Populate from Site Map"}
              </button>
            </div>
            {seedMsg && (
              <div
                className={"alert " + (seedMsg.startsWith("Error") ? "error" : "success")}
                style={{
                  marginBottom: 10,
                  padding: "6px 12px",
                  fontSize: 12,
                }}
              >
                {seedMsg}
              </div>
            )}

            {!matrix?.seeded && (
              <div
                className="subtle"
                style={{
                  padding: 24,
                  textAlign: "center",
                }}
              >
                No OWASP Coverage data yet. Click <b>Populate from Site Map</b> to seed the matrix
                from crawl data.
              </div>
            )}

            {matrix?.seeded && !matrix?.pages?.length && (
              <div
                className="subtle"
                style={{
                  padding: 24,
                  textAlign: "center",
                }}
              >
                No applicable pages found. Run a crawl first so OWASP categories can be classified.
              </div>
            )}

            {matrix?.seeded && matrix?.pages?.length > 0 && (
              <>
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    marginBottom: 10,
                    flexWrap: "wrap",
                    fontSize: 11,
                  }}
                >
                  {[
                    ["not_started", "cov-not-started", "Not started"],
                    ["in_progress", "cov-in-progress", "In progress"],
                    ["covered", "cov-covered", "Covered"],
                    ["finding", "cov-finding", "Finding"],
                    ["skipped", "cov-skipped", "Skipped"],
                  ].map(([s, cls, label]) => (
                    <span
                      key={s}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      <span className={"cov-cell coverage-legend-cell " + cls}></span>
                      {label} ({totals[s] || 0})
                    </span>
                  ))}
                </div>
                <div
                  className="run-work-program-table-wrap"
                  style={{
                    overflowX: "auto",
                  }}
                >
                  <table
                    className="coverage-matrix"
                    style={{
                      borderCollapse: "collapse",
                      fontSize: 11,
                      minWidth: 700,
                    }}
                  >
                    <thead>
                      <tr>
                        <th
                          style={{
                            textAlign: "left",
                            padding: "4px 8px",
                            minWidth: 300,
                            width: "35%",
                          }}
                        >
                          Page
                        </th>
                        {columns.map((column) => (
                          <th
                            key={column.key}
                            style={{
                              padding: "4px 4px",
                              textAlign: "center",
                              minWidth: 70,
                            }}
                            title={column.category + ": " + column.label}
                          >
                            <div
                              style={{
                                fontWeight: 600,
                              }}
                            >
                              {column.category}
                            </div>
                            <div
                              style={{
                                color: "var(--muted)",
                                fontWeight: 400,
                                fontSize: 10,
                                lineHeight: 1.2,
                                whiteSpace: "pre-line",
                              }}
                            >
                              {(column.test_class
                                ? column.label
                                : OWASP_WEB_SHORT[column.key] || column.label || ""
                              ).replace(/ /g, "\n")}
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {matrix.pages.map((pg) => (
                        <tr
                          key={pg.page_id}
                          style={{
                            borderBottom: "1px solid var(--border)",
                          }}
                        >
                          <td
                            style={{
                              padding: "4px 8px",
                            }}
                          >
                            {pg.state_kind === "interactive" && pg.state_label && (
                              <div
                                style={{
                                  fontWeight: 600,
                                }}
                              >
                                {pg.state_label}
                              </div>
                            )}
                            <div
                              className="mono"
                              style={{
                                fontSize: 11,
                                wordBreak: "break-all",
                              }}
                              title={pg.url}
                            >
                              {pg.url}
                            </div>
                            {pg.title && pg.title !== pg.state_label && (
                              <div
                                style={{
                                  fontSize: 10,
                                  color: "var(--muted)",
                                }}
                              >
                                {pg.title}
                              </div>
                            )}
                          </td>
                          {columns.map((column) => {
                            const cat = column.key;
                            const cell = pg.cells?.[cat];
                            if (!cell)
                              return (
                                <td
                                  key={cat}
                                  style={{
                                    textAlign: "center",
                                    padding: "2px 4px",
                                  }}
                                >
                                  <span className="cov-cell cov-na" title="N/A">
                                    —
                                  </span>
                                </td>
                              );
                            const fids = cell.finding_ids || [];
                            const classEntries = Object.entries(cell.test_classes || {});
                            const classSummary = classEntries
                              .map(([name, state]) => `${name}: ${state.status || "not_started"}`)
                              .join("\n");
                            const isSelected =
                              selectedCell?.page_id === pg.page_id && selectedCell?.cat === cat;
                            return (
                              <td
                                key={cat}
                                className="coverage-traffic-cell"
                                style={{
                                  textAlign: "center",
                                  padding: "2px 4px",
                                  cursor: "pointer",
                                }}
                                title={`Show traffic for ${cat} on ${pg.url}`}
                                onClick={() =>
                                  nav(
                                    runHref({ runKind: "web", runId }, "traffic", {
                                      coverage_cells: (cell.cell_ids || []).join(","),
                                      coverage_category: column.category,
                                      test_class: column.test_class || undefined,
                                    }),
                                  )
                                }
                              >
                                <span
                                  className={
                                    "cov-cell cov-" +
                                    cell.status.replace("_", "-") +
                                    (isSelected ? " selected" : "") +
                                    (fids.length ? " has-findings" : "")
                                  }
                                  title={
                                    cat +
                                    ": " +
                                    cell.status +
                                    (fids.length
                                      ? " (" +
                                        fids.length +
                                        " finding" +
                                        (fids.length > 1 ? "s" : "") +
                                        ""
                                      : "") +
                                    ")\n" +
                                    pg.url +
                                    (classSummary ? "\n\nTest classes:\n" + classSummary : "")
                                  }
                                  style={{
                                    cursor:
                                      fids.length || classEntries.length ? "pointer" : "default",
                                  }}
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    if (fids.length || classEntries.length)
                                      setSelectedCell(
                                        isSelected
                                          ? null
                                          : {
                                              page_id: pg.page_id,
                                              cat,
                                              label: column.label,
                                              url: pg.url,
                                              fids,
                                              findings: cell.findings,
                                              testClasses: cell.test_classes || {},
                                            },
                                      );
                                  }}
                                >
                                  {fids.length > 0 ? fids.length : ""}
                                </span>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {selectedCell && (
                  <div
                    style={{
                      marginTop: 12,
                      padding: 12,
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: 8,
                      }}
                    >
                      <b
                        style={{
                          fontSize: 13,
                        }}
                      >
                        {selectedCell.cat}{" "}
                        {selectedCell.label || OWASP_WEB_LABELS[selectedCell.cat] || ""} —{" "}
                        {selectedCell.url}
                      </b>
                      <button className="btn ghost sm" onClick={() => setSelectedCell(null)}>
                        ✕
                      </button>
                    </div>
                    {Object.keys(selectedCell.testClasses || {}).length > 0 && (
                      <div className="surface-chip-list" style={{ marginBottom: 8 }}>
                        {Object.entries(selectedCell.testClasses).map(([name, state]) => (
                          <span
                            key={name}
                            className={`surface-status status-${state.status || "not_started"}`}
                          >
                            {name.replace(/_/g, " ")}:{" "}
                            {(state.status || "not_started").replace(/_/g, " ")}
                          </span>
                        ))}
                      </div>
                    )}
                    {selectedCell.findings && selectedCell.findings.length ? (
                      selectedCell.findings.map((f) => (
                        <div
                          key={f.id}
                          style={{
                            padding: "6px 0",
                            borderTop: "1px solid var(--border)",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 6,
                              marginBottom: 2,
                            }}
                          >
                            <span className={"sev-badge sev-" + (f.severity || "info")}>
                              {f.severity || "info"}
                            </span>
                            <b
                              style={{
                                fontSize: 12,
                              }}
                            >
                              {f.title}
                            </b>
                            {f.validation_status && f.validation_status !== "unvalidated" ? (
                              <span
                                style={{
                                  fontSize: 11,
                                  color: "var(--muted)",
                                }}
                              >
                                ({f.validation_status})
                              </span>
                            ) : (
                              ""
                            )}
                          </div>
                          {f.description ? (
                            <div
                              style={{
                                fontSize: 12,
                                color: "var(--muted)",
                                whiteSpace: "pre-wrap",
                              }}
                            >
                              {f.description}
                            </div>
                          ) : (
                            ""
                          )}
                          <div
                            style={{
                              fontSize: 11,
                              color: "var(--muted)",
                              marginTop: 2,
                            }}
                          >
                            <FindingReferenceLink
                              reference={f.reference}
                              title={f.title}
                              description={f.description}
                              severity={f.severity}
                              validation_status={f.validation_status}
                              href={`#/runs/${runId}/findings?finding=${encodeURIComponent(f.reference || "")}`}
                            />{" "}
                            — view in the Findings tab.
                          </div>
                        </div>
                      ))
                    ) : (
                      <div
                        style={{
                          fontSize: 12,
                        }}
                      >
                        Finding references:{" "}
                        {selectedCell.findings
                          ?.map((f) => f.reference)
                          .filter(Boolean)
                          .join(", ") || selectedCell.fids.map((id) => `#${id}`).join(", ")}{" "}
                        — view in the Findings tab.
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      {coverageTab === "workflows" && (
        <WorkflowCoverageTable coverage={workflowCoverage} error={workflowError} />
      )}
    </div>
  );
}

const WORKFLOW_STATUS_LABELS = {
  not_started: "Not started",
  in_progress: "In progress",
  passed: "Passed",
  inconclusive: "Inconclusive",
  finding: "Finding",
  blocked: "Blocked",
  skipped: "Skipped",
};

const WORKFLOW_TEST_LABELS = {
  sequence: "Step order",
  access: "Access",
  replay: "Replay",
  tampering: "Tampering",
  csrf: "CSRF",
  reauth: "Re-login",
};

function workflowTestLabel(kind) {
  return WORKFLOW_TEST_LABELS[kind] || (kind || "check").replace(/_/g, " ");
}

// Workflow check statuses mapped onto the page table's cell styles.
const WORKFLOW_CELL_STATUS = {
  not_started: "not_started",
  in_progress: "in_progress",
  passed: "covered",
  finding: "finding",
  inconclusive: "skipped",
  blocked: "skipped",
  skipped: "skipped",
};

const COVERAGE_LEGEND = [
  ["not_started", "cov-not-started", "Not started"],
  ["in_progress", "cov-in-progress", "In progress"],
  ["covered", "cov-covered", "Covered"],
  ["finding", "cov-finding", "Finding"],
  ["skipped", "cov-skipped", "Skipped or blocked"],
];

function workflowCellStatus(checks) {
  const statuses = checks.map((check) => WORKFLOW_CELL_STATUS[check.status] || "not_started");
  for (const status of ["finding", "in_progress", "not_started", "covered"]) {
    if (statuses.includes(status)) return status;
  }
  return "skipped";
}

function groupWorkflowChecks(items) {
  const rows = new Map();
  for (const item of items) {
    const key = item.root_note_id ?? `check-${item.id}`;
    if (!rows.has(key)) {
      rows.set(key, {
        key,
        name: item.name || item.goal || `Workflow ${item.id}`,
        goal: item.goal && item.goal !== item.name ? item.goal : "",
        url: item.reached_page_url || "",
        cells: {},
      });
    }
    const row = rows.get(key);
    const category = item.owasp_category || "Other";
    (row.cells[category] ||= []).push(item);
  }
  return [...rows.values()];
}

function workflowStatusLabel(status) {
  return WORKFLOW_STATUS_LABELS[status] || (status || "not_started").replace(/_/g, " ");
}

function WorkflowCoverageTable({ coverage, error }) {
  const [selected, setSelected] = useState(null);

  if (!coverage) {
    return (
      <div className="workflow-coverage-panel" role="tabpanel" aria-label="Workflow coverage">
        {error ? (
          <div className="alert error" role="alert">
            Could not load workflow coverage: {error}
          </div>
        ) : (
          <LoadingState label="Loading workflow coverage…" />
        )}
      </div>
    );
  }

  const items = coverage.items || [];
  const covered = items.filter(
    (item) => item.status === "passed" || item.status === "finding",
  ).length;
  const blocked = items.filter((item) => item.status === "blocked").length;
  const rows = groupWorkflowChecks(items);
  const categories = [...new Set(items.map((item) => item.owasp_category || "Other"))].sort();
  const legendTotals = {};
  for (const item of items) {
    const status = WORKFLOW_CELL_STATUS[item.status] || "not_started";
    legendTotals[status] = (legendTotals[status] || 0) + 1;
  }
  const selectedRow = selected && rows.find((row) => row.key === selected.rowKey);
  const selectedChecks = selectedRow?.cells[selected.category] || [];

  return (
    <div role="tabpanel" aria-label="Workflow coverage" className="workflow-coverage-panel">
      <div className="workflow-coverage-header">
        <h3>Workflow coverage</h3>
        <span className="subtle">
          {covered} of {items.length} checks covered{blocked ? `, ${blocked} blocked` : ""}.
        </span>
      </div>
      {error && (
        <div className="alert error" role="alert">
          Could not refresh workflow coverage: {error}
        </div>
      )}
      {items.length === 0 ? (
        <div className="subtle workflow-coverage-empty">
          No workflow checks yet. Crawl a workflow to add checks.
        </div>
      ) : (
        <>
          <div className="workflow-coverage-legend">
            {COVERAGE_LEGEND.map(([status, cls, label]) => (
              <span key={status}>
                <span className={"cov-cell coverage-legend-cell " + cls}></span>
                {label} ({legendTotals[status] || 0})
              </span>
            ))}
          </div>
          <div className="run-work-program-table-wrap">
            <table className="coverage-matrix workflow-coverage-table">
              <thead>
                <tr>
                  <th scope="col" className="workflow-coverage-name-col">
                    Workflow
                  </th>
                  {categories.map((category) => (
                    <th
                      key={category}
                      scope="col"
                      className="workflow-coverage-cat-col"
                      title={`${category}: ${OWASP_WEB_LABELS[category] || category}`}
                    >
                      <div className="workflow-coverage-cat">{category}</div>
                      <div className="workflow-coverage-cat-label">
                        {OWASP_WEB_SHORT[category] || ""}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.key}>
                    <td className="workflow-coverage-name">
                      <div className="workflow-coverage-title">{row.name}</div>
                      {row.goal && (
                        <div className="workflow-coverage-goal" title={row.goal}>
                          {row.goal}
                        </div>
                      )}
                      {row.url && (
                        <div className="mono workflow-coverage-url" title={row.url}>
                          {row.url}
                        </div>
                      )}
                    </td>
                    {categories.map((category) => {
                      const checks = row.cells[category];
                      if (!checks) {
                        return (
                          <td key={category} className="workflow-coverage-cell">
                            <span className="cov-cell cov-na" title="Not applicable">
                              —
                            </span>
                          </td>
                        );
                      }
                      const status = workflowCellStatus(checks);
                      const findingCount = checks.reduce(
                        (count, check) => count + (check.finding_ids || []).length,
                        0,
                      );
                      const isSelected =
                        selected?.rowKey === row.key && selected?.category === category;
                      const summary = checks
                        .map(
                          (check) =>
                            `${workflowTestLabel(check.test_kind)}: ${workflowStatusLabel(check.status)}`,
                        )
                        .join("\n");
                      return (
                        <td key={category} className="workflow-coverage-cell">
                          <button
                            type="button"
                            className={
                              "cov-cell workflow-coverage-btn cov-" +
                              status.replace("_", "-") +
                              (isSelected ? " selected" : "") +
                              (findingCount ? " has-findings" : "")
                            }
                            title={`${category} on ${row.name}\n${summary}`}
                            aria-label={`${category} ${row.name}: ${workflowStatusLabel(
                              checks.length === 1 ? checks[0].status : status,
                            )}`}
                            aria-pressed={isSelected}
                            onClick={() =>
                              setSelected(isSelected ? null : { rowKey: row.key, category })
                            }
                          >
                            {findingCount > 0 ? findingCount : ""}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selectedRow && (
            <div className="workflow-coverage-detail">
              <div className="workflow-coverage-detail-head">
                <b>
                  {selected.category} {OWASP_WEB_LABELS[selected.category] || ""} —{" "}
                  {selectedRow.name}
                </b>
                <button
                  className="btn ghost sm"
                  aria-label="Close details"
                  onClick={() => setSelected(null)}
                >
                  ✕
                </button>
              </div>
              {selectedChecks.map((check) => (
                <div key={check.id} className="workflow-coverage-check">
                  <div className="workflow-coverage-check-head">
                    <span className={`surface-status status-${check.status || "not_started"}`}>
                      {workflowStatusLabel(check.status)}
                    </span>
                    <b>{workflowTestLabel(check.test_kind)}</b>
                  </div>
                  {check.test_guidance && <div className="subtle">{check.test_guidance}</div>}
                  {check.reason && <div>{check.reason}</div>}
                  {check.expected_behavior && (
                    <div>
                      <span className="subtle">Expected: </span>
                      {check.expected_behavior}
                    </div>
                  )}
                  {check.evidence_summary && (
                    <div>
                      <span className="subtle">Observed: </span>
                      {check.evidence_summary}
                    </div>
                  )}
                  {(check.finding_ids || []).length > 0 && (
                    <div>
                      <span className="subtle">Findings: </span>
                      {check.finding_ids.map((id) => `#${id}`).join(", ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
