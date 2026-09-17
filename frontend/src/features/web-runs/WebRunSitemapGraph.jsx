import { matchesSitemapSearch } from "./sitemapSearch.js";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { useEffect, useMemo, useState } from "react";

import { apiTranscriptText } from "../../shared/lib/transcript.js";
import { parseExcludedExtensions } from "../../shared/lib/urlExtensions.js";
import { OWASP_WEB_LABELS } from "./coverageLabels.js";
import {
  SCOPE_IN_COLOR,
  SCOPE_OUT_COLOR,
  USER_ALL_COLOR,
  USER_ANONYMOUS_COLOR,
  USER_MULTIPLE_COLOR,
  USER_PALETTE,
} from "../../shared/runs/presentation.jsx";
import { useSelectedSitemapPage } from "./useSelectedSitemapPage.js";
import { useSitemapGraph } from "./useSitemapGraph.js";
import { WebRunUserCrawlProgress } from "./WebRunCrawlProgress.jsx";
import { WebRunSitemapTab } from "./WebRunSitemapTab.jsx";
import { buildSitemapDisplayGraph } from "./sitemapGraph.js";

/** The interactive sitemap canvas and its selected-page inspector. */
export function WebRunSitemapGraph({
  site,
  runId,
  run,
  crawlerActive,
  graph,
  active,
  graphView,
  onGraphChange,
  onStart,
  onStartThinkingScan,
  hasCheckpoint,
  onResumeThinkingScan,
  checkpointStatus,
  onError,
}) {
  const { selectedNode, setSelectedNode, pageDetail, pageViews } = useSelectedSitemapPage(runId);
  const [cascade, setCascade] = useState(false);
  const [scopeBusy, setScopeBusy] = useState(false);
  const [testStateBusy, setTestStateBusy] = useState(false);
  const [testStateMessage, setTestStateMessage] = useState("");
  const [scannerSessions, setScannerSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [excludedExtensionsInput, setExcludedExtensionsInput] = useState(".svg, .js");
  const [pageDisplay, setPageDisplay] = useState("grouped");
  const [apiDisplay, setApiDisplay] = useState("grouped");
  const [displaySettingsOpen, setDisplaySettingsOpen] = useState(false);
  const excludedExtensions = useMemo(
    () => parseExcludedExtensions(excludedExtensionsInput),
    [excludedExtensionsInput],
  );
  const filteredGraph = useMemo(
    () => buildSitemapDisplayGraph(graph, excludedExtensions, apiDisplay, pageDisplay),
    [apiDisplay, excludedExtensions, graph, pageDisplay],
  );
  const displayStats = filteredGraph?.displayStats;
  const [searchTerm, setSearchTerm] = useState("");
  const searchMatches = useMemo(
    () =>
      new Set(
        (filteredGraph?.nodes || [])
          .filter((node) => matchesSitemapSearch(node, searchTerm))
          .map((node) => node.id),
      ),
    [filteredGraph, searchTerm],
  );

  useEffect(() => {
    if (
      selectedNode &&
      filteredGraph &&
      !filteredGraph.nodes.some((node) => node.id === selectedNode.id)
    ) {
      setSelectedNode(null);
    }
  }, [filteredGraph, selectedNode, setSelectedNode]);
  useEffect(() => {
    let cancelled = false;
    webRunsApi
      .getScannerSessions(runId, true)
      .then((result) => {
        if (!cancelled) setScannerSessions(result?.sessions || result?.items || []);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [runId]);
  const { svgRef } = useSitemapGraph({
    searchMatches,
    site,
    graph: filteredGraph,
    activeTab: active ? "sitemap" : "hidden",
    graphView,
    credentials: run?.credentials,
    currentUrl: run?.current_url,
    selectedNodeId: selectedNode?.id,
    onSelectNode: setSelectedNode,
  });

  const refreshGraph = async () => onGraphChange(await webRunsApi.getGraph(runId));
  const toggleScope = async () => {
    if (!selectedNode || scopeBusy) return;
    setScopeBusy(true);
    try {
      await webRunsApi.setPageScope(runId, selectedNode.id, {
        in_scope: selectedNode.in_scope === false,
        cascade,
      });
      const nextGraph = await webRunsApi.getGraph(runId);
      onGraphChange(nextGraph);
      setSelectedNode(nextGraph.nodes.find((node) => node.id === selectedNode.id) || null);
    } catch (error) {
      onError(error.message);
    } finally {
      setScopeBusy(false);
    }
  };
  const deleteNode = async () => {
    if (!selectedNode || scopeBusy) return;
    setScopeBusy(true);
    try {
      await webRunsApi.deletePage(runId, selectedNode.id, cascade);
      await refreshGraph();
      setSelectedNode(null);
    } catch (error) {
      onError(error.message);
    } finally {
      setScopeBusy(false);
    }
  };
  const testState = async () => {
    if (!selectedNode || !pageDetail || testStateBusy) return;
    setTestStateBusy(true);
    setTestStateMessage("");
    try {
      const result = await webRunsApi.testPageState(
        runId,
        selectedNode.id,
        selectedSession ? { use_session: selectedSession } : {},
      );
      setTestStateMessage(
        result.status === "queued" ? "Queued for the current Test Lead." : "Focused scan started.",
      );
    } catch (error) {
      onError(error.message);
    } finally {
      setTestStateBusy(false);
    }
  };

  return (
    <div className="graph-layout" style={{ display: active ? "flex" : "none" }}>
      <div className="sitemap-graph-main">
        <div className="sitemap-filter-panel">
          <WebRunUserCrawlProgress run={run} crawlerActive={crawlerActive} />
          <div className="sitemap-filter-summary">
            <button
              className="btn ghost sm sitemap-filter-toggle"
              type="button"
              aria-expanded={displaySettingsOpen}
              aria-controls="sitemap-display-settings"
              onClick={() => setDisplaySettingsOpen((open) => !open)}
            >
              <span aria-hidden="true">{displaySettingsOpen ? "▾" : "▸"}</span>
              Display settings
            </button>
            <SitemapDisplaySummary
              filteredGraph={filteredGraph}
              pageDisplay={pageDisplay}
              apiDisplay={apiDisplay}
              displayStats={displayStats}
            />
          </div>
          <div
            id="sitemap-display-settings"
            className="sitemap-filter-controls"
            hidden={!displaySettingsOpen}
          >
            <label className="traffic-filter-ext">
              <span>Exclude extensions</span>
              <input
                className="traffic-filter"
                type="text"
                aria-label="Exclude site map extensions"
                placeholder=".svg, .png, .woff2"
                value={excludedExtensionsInput}
                onInput={(event) => setExcludedExtensionsInput(event.target.value)}
              />
            </label>
            <label className="traffic-filter-ext sitemap-api-display">
              <span>Page display</span>
              <select
                aria-label="Page display"
                value={pageDisplay}
                onChange={(event) => setPageDisplay(event.target.value)}
              >
                <option value="grouped">Grouped routes</option>
                <option value="individual">Individual pages</option>
              </select>
            </label>
            <label className="traffic-filter-ext sitemap-api-display">
              <span>API display</span>
              <select
                aria-label="API display"
                value={apiDisplay}
                onChange={(event) => setApiDisplay(event.target.value)}
              >
                <option value="grouped">Grouped endpoints</option>
                <option value="individual">Individual requests</option>
                <option value="hidden">Hidden</option>
              </select>
            </label>
          </div>
        </div>
        <div className="graph-canvas-wrap">
          <div className="sitemap-search">
            <input
              type="search"
              aria-label="Search site map nodes"
              placeholder="Search nodes…"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Escape") setSearchTerm("");
              }}
            />
            {searchTerm && (
              <button
                type="button"
                className="btn ghost sm"
                aria-label="Clear node search"
                onClick={() => setSearchTerm("")}
              >
                ×
              </button>
            )}
            <span role="status" aria-live="polite">
              {searchTerm.trim()
                ? `${searchMatches.size} ${searchMatches.size === 1 ? "match" : "matches"}`
                : ""}
            </span>
          </div>
          {graph && graph.nodes.length === 0 && (
            <div className="graph-empty">
              <WebRunSitemapTab
                activeTab="sitemap"
                run={run}
                onStart={onStart}
                onStartThinkingScan={onStartThinkingScan}
                hasCheckpoint={hasCheckpoint}
                onResumeThinkingScan={onResumeThinkingScan}
                checkpointStatus={checkpointStatus}
              />
            </div>
          )}
          {graph && graph.nodes.length > 0 && filteredGraph.nodes.length === 0 && (
            <div className="graph-empty">All site map pages are hidden by the current filters.</div>
          )}
          <svg
            ref={svgRef}
            className="graph-svg"
            width="100%"
            height="100%"
            style={{
              pointerEvents: !filteredGraph || filteredGraph.nodes.length === 0 ? "none" : "all",
            }}
          />
          {filteredGraph && filteredGraph.nodes.length > 0 && (
            <div className="graph-legend">
              {graphView === "user" && run?.credentials?.length > 1 ? (
                <>
                  {(run.credentials || []).map((credential, index) => (
                    <div key={credential.id} className="legend-item">
                      <span
                        className="legend-dot"
                        style={{ background: USER_PALETTE[index % USER_PALETTE.length] }}
                      />
                      {credential.label || credential.username}
                    </div>
                  ))}
                  <div className="legend-item">
                    <span className="legend-dot" style={{ background: USER_ANONYMOUS_COLOR }} />
                    Unauthenticated
                  </div>
                  <div className="legend-item">
                    <span className="legend-dot" style={{ background: USER_MULTIPLE_COLOR }} />
                    Multiple users
                  </div>
                  <div className="legend-item">
                    <span className="legend-dot" style={{ background: USER_ALL_COLOR }} />
                    All users
                  </div>
                </>
              ) : (
                <>
                  <div className="legend-item">
                    <span className="legend-dot" style={{ background: SCOPE_IN_COLOR }} />
                    In Scope
                  </div>
                  <div className="legend-item">
                    <span className="legend-dot" style={{ background: SCOPE_OUT_COLOR }} />
                    Out of Scope
                  </div>
                  <div className="legend-item">
                    <span
                      className="legend-dot"
                      style={{ background: "var(--bg)", border: "2px solid #fbbf24" }}
                    />
                    Failed
                  </div>
                </>
              )}
              <div className="legend-item">
                <span
                  className="pulse-legend-dot"
                  style={{ border: "2px solid #f59e0b", background: "transparent" }}
                />
                Pending LLM Analysis
              </div>
            </div>
          )}
        </div>
      </div>
      {selectedNode?.isDiscoveryGroup ? (
        <SitemapDiscoveryInspector node={selectedNode} onClose={() => setSelectedNode(null)} />
      ) : selectedNode?.isPageGroup ? (
        <SitemapPageGroupInspector
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
          onExpand={() => {
            setPageDisplay("individual");
            setSelectedNode(selectedNode.memberNodes[0] || null);
          }}
        />
      ) : selectedNode?.isApiGroup ? (
        <SitemapApiGroupInspector
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
          onExpand={() => {
            setApiDisplay("individual");
            setSelectedNode(selectedNode.memberNodes[0] || null);
          }}
        />
      ) : selectedNode ? (
        <SitemapPageInspector
          node={selectedNode}
          detail={pageDetail}
          views={pageViews}
          cascade={cascade}
          scopeBusy={scopeBusy}
          testStateBusy={testStateBusy}
          testStateMessage={testStateMessage}
          scannerSessions={scannerSessions}
          selectedSession={selectedSession}
          onSessionChange={setSelectedSession}
          onCascade={setCascade}
          onClose={() => setSelectedNode(null)}
          onToggleScope={toggleScope}
          onDelete={deleteNode}
          onTestState={testState}
        />
      ) : null}
    </div>
  );
}

function SitemapDiscoveryInspector({ node, onClose }) {
  return (
    <div className="graph-panel page-group-panel">
      <div className="graph-panel-header">
        <div>
          <div className="api-group-method">DYNAMIC SCAN</div>
          <div className="graph-panel-url">Direct scan discoveries</div>
        </div>
        <button className="btn ghost sm" onClick={onClose} aria-label="Close discovery details">
          ✕
        </button>
      </div>
      <div className="graph-panel-body">
        <div className="api-group-summary">
          <div>
            <strong>{node.discoveryCount}</strong>
            <span>Unattributed {node.discoveryCount === 1 ? "route" : "routes"}</span>
          </div>
        </div>
        <div className="graph-panel-context">
          These routes were observed by the Dynamic Scan, but the saved traffic does not identify
          another page as their source. They are grouped here instead of being shown as unrelated
          nodes.
        </div>
      </div>
    </div>
  );
}

function SitemapDisplaySummary({ filteredGraph, pageDisplay, apiDisplay, displayStats }) {
  return (
    <span className="traffic-count-label">
      {filteredGraph?.nodes.length || 0} shown
      {pageDisplay === "grouped" && displayStats?.pageGroupCount > 0
        ? ` · ${displayStats.groupedPageVariantCount} pages in ${displayStats.pageGroupCount} routes`
        : ""}
      {apiDisplay === "grouped" && displayStats?.apiNodeCount > 0
        ? ` · ${displayStats.apiNodeCount} API requests in ${displayStats.apiGroupCount} endpoints`
        : ""}
      {apiDisplay === "hidden" && displayStats?.apiNodeCount > 0
        ? ` · ${displayStats.apiNodeCount} APIs hidden`
        : ""}
      {displayStats?.excludedCount > 0 ? ` · ${displayStats.excludedCount} files hidden` : ""}
    </span>
  );
}

function SitemapPageGroupInspector({ node, onClose, onExpand }) {
  return (
    <div className="graph-panel page-group-panel">
      <div className="graph-panel-header">
        <div>
          <div className="api-group-method">PAGE ROUTE</div>
          <div className="graph-panel-url">{node.routeOrigin + node.routePath}</div>
        </div>
        <button className="btn ghost sm" onClick={onClose} aria-label="Close page route details">
          ✕
        </button>
      </div>
      <div className="graph-panel-body">
        <div className="api-group-summary">
          <div>
            <strong>{node.variantCount}</strong>
            <span>Page {node.variantCount === 1 ? "variant" : "variants"}</span>
          </div>
          <div>
            <strong>{node.parameters.length}</strong>
            <span>Parameters</span>
          </div>
          <div>
            <strong>{node.connections.length}</strong>
            <span>Connections</span>
          </div>
        </div>

        <ObservedParameters parameters={node.parameters} />

        {node.connections.length > 0 && (
          <>
            <div className="graph-panel-section-label api-group-section">Connected nodes</div>
            <div className="api-group-list">
              {node.connections.map((connection) => (
                <div key={connection.id} className="api-group-list-row">
                  <span title={connection.label}>
                    <small>{connection.direction}</small> {connection.label}
                  </span>
                  {connection.count > 1 && <small>×{connection.count}</small>}
                </div>
              ))}
            </div>
          </>
        )}

        <ObservedVariants label="Page variants" variants={node.variants} />
        <button className="btn sm api-group-expand" onClick={onExpand}>
          Show individual pages
        </button>
      </div>
    </div>
  );
}

function SitemapApiGroupInspector({ node, onClose, onExpand }) {
  return (
    <div className="graph-panel api-group-panel">
      <div className="graph-panel-header">
        <div>
          <div className="api-group-method">{node.apiMethod}</div>
          <div className="graph-panel-url">{node.apiOrigin + node.apiPath}</div>
        </div>
        <button className="btn ghost sm" onClick={onClose} aria-label="Close API endpoint details">
          ✕
        </button>
      </div>
      <div className="graph-panel-body">
        <div className="api-group-summary">
          <div>
            <strong>{node.variantCount}</strong>
            <span>Request {node.variantCount === 1 ? "variant" : "variants"}</span>
          </div>
          <div>
            <strong>{node.callers.length}</strong>
            <span>Calling {node.callers.length === 1 ? "page" : "pages"}</span>
          </div>
          <div>
            <strong>{node.parameters.length}</strong>
            <span>Parameters</span>
          </div>
        </div>

        <div className="graph-panel-section-label">Calling pages</div>
        {node.callers.length > 0 ? (
          <div className="api-group-list">
            {node.callers.map((caller) => (
              <div key={caller.id} className="api-group-list-row">
                <span title={caller.url}>{caller.label}</span>
                {caller.observationCount > 1 && <small>×{caller.observationCount}</small>}
              </div>
            ))}
          </div>
        ) : (
          <div className="subtle">No calling page was recorded.</div>
        )}

        <ObservedParameters parameters={node.parameters} />
        <ObservedVariants label="Request variants" variants={node.variants} />
        <button className="btn sm api-group-expand" onClick={onExpand}>
          Show individual requests
        </button>
      </div>
    </div>
  );
}

function ObservedParameters({ parameters }) {
  return (
    <>
      <div className="graph-panel-section-label api-group-section">Observed parameters</div>
      {parameters.length > 0 ? (
        <div className="api-parameter-table">
          {parameters.map((parameter) => (
            <div key={`${parameter.location}:${parameter.name}`} className="api-parameter-row">
              <span className="api-parameter-location">{parameter.location}</span>
              <code>{parameter.name}</code>
              <span title={parameter.values.join(", ")}>
                {parameter.values.slice(0, 3).join(", ")}
                {parameter.values.length > 3 ? ` +${parameter.values.length - 3}` : ""}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="subtle">No path or query parameters were observed.</div>
      )}
    </>
  );
}

function ObservedVariants({ label, variants }) {
  return (
    <>
      <div className="graph-panel-section-label api-group-section">{label}</div>
      <div className="api-group-variants">
        {variants.slice(0, 12).map((url) => (
          <code key={url}>{url}</code>
        ))}
        {variants.length > 12 && <span>+{variants.length - 12} more</span>}
      </div>
    </>
  );
}

function SitemapPageInspector({
  node,
  detail,
  views,
  cascade,
  scopeBusy,
  testStateBusy,
  testStateMessage,
  scannerSessions,
  selectedSession,
  onSessionChange,
  onCascade,
  onClose,
  onToggleScope,
  onDelete,
  onTestState,
}) {
  const isFailed = node.status === "failed" || detail?.status === "failed";
  const errorMessage = detail?.error_message || node.error_message;

  return (
    <div className="graph-panel">
      <div className="graph-panel-header">
        <div className="graph-panel-url">
          {node.state_label ? `${node.url} · ${node.state_label}` : node.url}
        </div>
        <button className="btn ghost sm" onClick={onClose}>
          ✕
        </button>
      </div>
      {detail ? (
        <div className="graph-panel-body">
          {detail.title && <div className="graph-panel-title">{detail.title}</div>}
          {isFailed && (
            <div
              className="sitemap-failed-banner"
              style={{
                background: "rgba(245, 158, 11, 0.12)",
                border: "1px solid #f59e0b",
                color: "#f59e0b",
                padding: "8px 12px",
                borderRadius: 6,
                marginBottom: 12,
                fontSize: 12,
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                <span>⚠️ Page Load Failed</span>
              </div>
              {errorMessage && (
                <div
                  style={{
                    color: "var(--text-2, #d1d5db)",
                    fontFamily: "monospace",
                    fontSize: 11,
                    wordBreak: "break-word",
                  }}
                >
                  {errorMessage}
                </div>
              )}
            </div>
          )}
          <div className="graph-panel-section-label">Scope</div>
          <div className="scope-row">
            <span className={"scope-badge " + (node.in_scope === false ? "out" : "in")}>
              {node.in_scope === false ? "Out of Scope" : "In Scope"}
            </span>
            {isFailed && (
              <span className="cat-badge cat-no" style={{ fontSize: 11 }}>
                Failed
              </span>
            )}
            <button className="btn sm" onClick={onToggleScope} disabled={scopeBusy}>
              {scopeBusy ? "…" : node.in_scope === false ? "Mark in scope" : "Mark out of scope"}
            </button>
            <button
              className="btn danger-outline sm"
              onClick={onDelete}
              disabled={scopeBusy}
              title="Delete this node (and children if checkbox is ticked)"
            >
              🗑
            </button>
          </div>
          <label className="scope-cascade-label">
            <input
              type="checkbox"
              checked={cascade}
              onChange={(event) => onCascade(event.target.checked)}
            />
            Also apply to all children
          </label>
          {detail.browser_replay && (
            <div className="spa-state-action">
              <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 6 }}>
                <label className="subtle">Session</label>
                <select
                  value={selectedSession}
                  onChange={(event) => onSessionChange(event.target.value)}
                >
                  <option value="">Discovering session</option>
                  {scannerSessions.map((session) => (
                    <option key={session.id || session.label} value={session.label}>
                      {session.label}
                      {session.username ? ` · ${session.username}` : ""}
                    </option>
                  ))}
                </select>
              </div>
              <button className="btn sm" onClick={onTestState} disabled={testStateBusy}>
                {testStateBusy ? "…" : "Test this state"}
              </button>
              {testStateMessage && <span className="subtle">{testStateMessage}</span>}
            </div>
          )}
          <PageCategories detail={detail} />
          {views.length > 0 ? (
            <PageViews views={views} detail={detail} />
          ) : (
            <PageContext detail={detail} />
          )}
          {views.length > 0 && <PageStateEvidence detail={detail} />}
        </div>
      ) : (
        <div className="subtle" style={{ padding: 12 }}>
          Loading…
        </div>
      )}
    </div>
  );
}

function PageCategories({ detail }) {
  const categories = [
    ["req_auth", "Auth Required"],
    ["takes_input", "Takes Input"],
    ["has_object_ref", "Object Reference"],
    ["has_business_logic", "Business Logic"],
  ];
  return (
    <>
      <div className="graph-panel-section-label" style={{ marginTop: 14 }}>
        Page Categories
      </div>
      <div className="page-cats">
        {categories.map(([key, label]) => {
          const value = detail[key];
          return (
            <div key={key} className="cat-row">
              <span className="cat-label">{label}</span>
              <span
                className={
                  "cat-badge " +
                  (value === true ? "cat-yes" : value === false ? "cat-no" : "cat-unknown")
                }
              >
                {value === true ? "Yes" : value === false ? "No" : "?"}
              </span>
            </div>
          );
        })}
      </div>
      {detail.owasp_applicable && Object.keys(detail.owasp_applicable).length > 0 && (
        <>
          <div className="graph-panel-section-label" style={{ marginTop: 14 }}>
            OWASP Top 10:2025
          </div>
          <div className="page-cats">
            {Object.entries(detail.owasp_applicable).map(([category, applicable]) => (
              <div key={category} className="cat-row">
                <span className="cat-label" style={{ fontSize: 11 }}>
                  {category} {OWASP_WEB_LABELS[category] || ""}
                </span>
                <span className={"cat-badge " + (applicable ? "cat-yes" : "cat-no")}>
                  {applicable ? "Yes" : "No"}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}

function PageViews({ views, detail }) {
  return (
    <>
      <div className="graph-panel-section-label" style={{ marginTop: 14 }}>
        Views by User
      </div>
      {views.map((view) => {
        const transcript = apiTranscriptText(view.page_text || detail.page_text);
        return (
          <div key={view.id} className="credential-view-card">
            <div className="credential-view-label">{view.username || "Anonymous"}</div>
            {view.screenshot_b64 && (
              <img
                src={"data:image/png;base64," + view.screenshot_b64}
                className="credential-view-screenshot"
                alt={"screenshot (" + view.username + ")"}
              />
            )}
            {!view.screenshot_b64 && transcript && (
              <>
                <div className="api-transcript-label">API Request / Response</div>
                <pre className="api-transcript">{transcript}</pre>
              </>
            )}
            <div className="credential-view-context">{view.llm_context || "No context."}</div>
          </div>
        );
      })}
    </>
  );
}

function PageContext({ detail }) {
  const transcript = apiTranscriptText(detail.page_text);
  return (
    <>
      <div className="graph-panel-section-label" style={{ marginTop: 14 }}>
        LLM Context
      </div>
      <div className="graph-panel-context">{detail.llm_context || "No context available."}</div>
      {detail.screenshot_b64 && (
        <>
          <div className="graph-panel-section-label" style={{ marginTop: 12 }}>
            Screenshot
          </div>
          <img
            src={"data:image/png;base64," + detail.screenshot_b64}
            style={{ width: "100%", borderRadius: 6, border: "1px solid var(--border)" }}
            alt="screenshot"
          />
        </>
      )}
      {!detail.screenshot_b64 && transcript && (
        <>
          <div className="graph-panel-section-label" style={{ marginTop: 12 }}>
            API Request / Response
          </div>
          <pre className="api-transcript">{transcript}</pre>
        </>
      )}
      {<PageStateEvidence detail={detail} />}
    </>
  );
}

function PageStateEvidence({ detail }) {
  return (
    <>
      {detail.browser_replay && (
        <>
          <div className="graph-panel-section-label" style={{ marginTop: 14 }}>
            Replay
          </div>
          <div className="graph-panel-context">
            {detail.state_kind === "interactive"
              ? "Interactive browser state"
              : "URL with replay fallback"}{" "}
            · {detail.browser_replay.steps.length} deterministic steps
          </div>
        </>
      )}
      {detail.traffic?.length > 0 && (
        <>
          <div className="graph-panel-section-label" style={{ marginTop: 14 }}>
            Captured traffic
          </div>
          <div className="graph-panel-context">
            {detail.traffic.slice(0, 8).map((item) => (
              <div key={item.id}>
                {item.method} {item.url} → {item.status ?? "failed"}
              </div>
            ))}
          </div>
        </>
      )}
      {detail.object_references?.length > 0 && (
        <>
          <div className="graph-panel-section-label" style={{ marginTop: 14 }}>
            Object references
          </div>
          <div className="graph-panel-context">
            {detail.object_references.slice(0, 8).map((item) => (
              <div key={item.id}>
                {item.key}: {item.value}
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
