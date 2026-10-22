import { useMemo, useState } from "react";

const LANGUAGE_LABELS = {
  c_sharp: "C#",
  go: "Go",
  java: "Java",
  javascript: "JavaScript",
  php: "PHP",
  python: "Python",
  ruby: "Ruby",
  tsx: "TSX",
  typescript: "TypeScript",
};

const REACHABILITY_ROWS = [
  ["reachable", "Reachable", "Called from a route, request handler, or top-level code"],
  [
    "no_callers",
    "No callers",
    "Nothing calls this function directly; it may be called by the framework",
  ],
  ["not_reached", "Not reached", "Only called from code that no entry point reaches"],
  ["unknown", "Not parsed", "The file's language is not parsed"],
];
const EMPTY_FILES = [];

function buildFileTree(files) {
  const root = { children: new Map() };
  for (const file of files) {
    const parts = file.path.split("/").filter(Boolean);
    let parent = root;
    parts.forEach((name, index) => {
      const isFile = index === parts.length - 1;
      if (isFile) {
        parent.children.set(name, { kind: "file", name, ...file });
      } else {
        if (!parent.children.has(name)) {
          parent.children.set(name, {
            kind: "folder",
            name,
            path: parts.slice(0, index + 1).join("/"),
            children: new Map(),
            fileCount: 0,
            openedCount: 0,
            readCount: 0,
          });
        }
        parent = parent.children.get(name);
        parent.fileCount += 1;
        parent.openedCount += Number(Boolean(file.reviewed));
        parent.readCount += file.read_count || 0;
      }
    });
  }
  function sortedChildren(node) {
    return [...node.children.values()]
      .sort((a, b) =>
        a.kind === b.kind ? a.name.localeCompare(b.name) : a.kind === "folder" ? -1 : 1,
      )
      .map((child) =>
        child.kind === "folder" ? { ...child, children: sortedChildren(child) } : child,
      );
  }
  return sortedChildren(root);
}

function matchingNodes(nodes, query) {
  if (!query) return nodes;
  return nodes.flatMap((node) => {
    if (node.path.toLowerCase().includes(query)) return [node];
    if (node.kind === "file") return [];
    const children = matchingNodes(node.children, query);
    return children.length ? [{ ...node, children }] : [];
  });
}

function FileBrowserRows({ nodes, depth, expanded, setExpanded, searching }) {
  return nodes.map((node) => {
    const folder = node.kind === "folder";
    const open = searching || expanded.has(node.path);
    return (
      <div key={node.path} role="listitem">
        <div className={`sast-file-row ${folder ? "sast-file-folder" : ""}`}>
          <div className="sast-file-name" style={{ paddingInlineStart: `${depth * 18 + 12}px` }}>
            {folder && searching ? (
              <span className="sast-file-label">
                <span className="sast-file-chevron" aria-hidden="true">
                  ▾
                </span>
                <span className="sast-file-icon sast-file-icon-folder" aria-hidden="true" />
                <span>{node.name}</span>
              </span>
            ) : folder ? (
              <button
                type="button"
                className="sast-file-toggle"
                aria-label={`${open ? "Collapse" : "Expand"} ${node.path}`}
                aria-expanded={open}
                onClick={() =>
                  setExpanded((current) => {
                    const next = new Set(current);
                    if (next.has(node.path)) next.delete(node.path);
                    else next.add(node.path);
                    return next;
                  })
                }
              >
                <span className="sast-file-chevron" aria-hidden="true">
                  {open ? "▾" : "▸"}
                </span>
                <span className="sast-file-icon sast-file-icon-folder" aria-hidden="true" />
                <span>{node.name}</span>
              </button>
            ) : (
              <span className="sast-file-label" title={node.path}>
                <span className="sast-file-indent" aria-hidden="true" />
                <span className="sast-file-icon sast-file-icon-document" aria-hidden="true" />
                <span>{node.name}</span>
              </span>
            )}
          </div>
          <span className="sast-file-status">
            {folder
              ? `${node.openedCount}/${node.fileCount} opened`
              : node.reviewed
                ? "✓ Opened"
                : "Not opened"}
          </span>
          <span className="sast-file-type">
            {folder ? "Folder" : LANGUAGE_LABELS[node.language] || node.language || "Other"}
          </span>
          <span className="sast-file-reads">{folder ? node.readCount : node.read_count || 0}</span>
        </div>
        {folder && open ? (
          <div role="list">
            <FileBrowserRows
              nodes={node.children}
              depth={depth + 1}
              expanded={expanded}
              setExpanded={setExpanded}
              searching={searching}
            />
          </div>
        ) : null}
      </div>
    );
  });
}

export function CodeMapPanel({ codeGraph }) {
  if (!codeGraph) return null;
  const filesParsed = codeGraph.files_parsed || 0;
  const calls = codeGraph.calls || 0;
  const resolved = codeGraph.resolved_calls || 0;
  const sinks = codeGraph.sink_reachability || {};
  const sinkTotal = Object.values(sinks).reduce((total, count) => total + count, 0);
  const languages = Object.entries(codeGraph.languages || {}).sort((a, b) => b[1] - a[1]);
  return (
    <section className="sast-panel sast-coverage-summary" aria-label="Code map">
      <div className="sast-panel-header">
        <div>
          <div className="sast-panel-title">Code map</div>
          <div className="sast-panel-sub">Functions and calls found by parsing the source</div>
        </div>
        {languages.length ? (
          <span className="sast-state">
            {languages
              .map(([language, count]) => `${LANGUAGE_LABELS[language] || language} ${count}`)
              .join(" · ")}
          </span>
        ) : null}
      </div>
      {filesParsed ? (
        <>
          <dl>
            <div>
              <dt>Files parsed</dt>
              <dd>{filesParsed}</dd>
            </div>
            <div>
              <dt>Functions</dt>
              <dd>{codeGraph.functions || 0}</dd>
            </div>
            <div>
              <dt>Calls</dt>
              <dd>{calls}</dd>
            </div>
            <div>
              <dt>Calls matched to a function</dt>
              <dd>
                {resolved} ({calls ? Math.round((resolved / calls) * 100) : 0}%)
              </dd>
            </div>
          </dl>
          {sinkTotal ? (
            <div className="sast-coverage-grid">
              <div className="sast-coverage-name">Risky calls by reachability</div>
              {REACHABILITY_ROWS.filter(([key]) => sinks[key]).map(([key, label, help]) => (
                <div className="sast-coverage-row" key={key} title={help}>
                  <div className="sast-coverage-name">{label}</div>
                  <div className="sast-coverage-bar">
                    <span style={{ width: `${Math.round((sinks[key] / sinkTotal) * 100)}%` }} />
                  </div>
                  <div className="sast-coverage-count">
                    {sinks[key]}/{sinkTotal}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
          <div className="sast-coverage-note">
            Reachability sets the review order only. Every risky call is still reviewed.
            {codeGraph.sink_matches_outside_calls
              ? ` ${codeGraph.sink_matches_outside_calls} matches in comments or strings were skipped.`
              : ""}
          </div>
        </>
      ) : (
        <div className="sast-coverage-note">
          No PHP, JavaScript, TypeScript, Python, Java, Go, C#, or Ruby files were parsed. Risky
          calls were found by text search only.
        </div>
      )}
    </section>
  );
}

export function CoverageView({ coverage, workProgram }) {
  const summary = coverage?.summary || {};
  const files = coverage?.files || EMPTY_FILES;
  const total = workProgram?.files?.total ?? summary.files_total ?? 0;
  const directlyOpened = workProgram?.files?.directly_opened ?? summary.files_reviewed ?? 0;
  const percent = total ? Math.round((directlyOpened / total) * 100) : 0;
  const languages = Object.entries(summary.languages || {}).sort((a, b) => b[1].total - a[1].total);
  const [fileSearch, setFileSearch] = useState("");
  const [expanded, setExpanded] = useState(new Set());
  const tree = useMemo(() => buildFileTree(files), [files]);
  const query = fileSearch.trim().toLowerCase();
  const visibleTree = useMemo(() => matchingNodes(tree, query), [tree, query]);
  return (
    <div className="sast-coverage-layout">
      <div className="sast-coverage-main">
        <section className="sast-panel">
          <div className="sast-panel-header">
            <div>
              <div className="sast-panel-title">Direct file reads</div>
              <div className="sast-panel-sub">
                A search across a directory does not count as opening every file
              </div>
            </div>
            <span className="sast-state sast-state-confirmed">
              {directlyOpened} / {total} opened
            </span>
          </div>
          <div className="sast-coverage-grid">
            <div className="sast-coverage-row">
              <div className="sast-coverage-name">All files</div>
              <div className="sast-coverage-bar">
                <span style={{ width: `${percent}%` }} />
              </div>
              <div className="sast-coverage-count">{percent}%</div>
            </div>
            {languages.map(([language, counts]) => {
              const languagePercent = counts.total
                ? Math.round((counts.reviewed / counts.total) * 100)
                : 0;
              return (
                <div className="sast-coverage-row" key={language}>
                  <div className="sast-coverage-name">{language}</div>
                  <div className="sast-coverage-bar">
                    <span style={{ width: `${languagePercent}%` }} />
                  </div>
                  <div className="sast-coverage-count">
                    {counts.reviewed}/{counts.total}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
        <CodeMapPanel codeGraph={workProgram?.code_graph} />
      </div>
      <section className="sast-panel sast-file-receipts">
        <div className="sast-panel-header">
          <div>
            <div className="sast-panel-title">Direct read receipts</div>
            <div className="sast-panel-sub">{files.length} inventoried files</div>
          </div>
        </div>
        <div className="sast-file-toolbar">
          <input
            type="search"
            aria-label="Find a file or folder"
            placeholder="Find a file or folder"
            value={fileSearch}
            onChange={(event) => setFileSearch(event.target.value)}
          />
        </div>
        <div className="sast-file-list" role="list" aria-label="Direct read receipts">
          <div className="sast-file-columns" aria-hidden="true">
            <span>Name</span>
            <span>Status</span>
            <span>Type</span>
            <span>Reads</span>
          </div>
          {visibleTree.length ? (
            <FileBrowserRows
              nodes={visibleTree}
              depth={0}
              expanded={expanded}
              setExpanded={setExpanded}
              searching={Boolean(query)}
            />
          ) : (
            <div className="sast-file-empty">
              {query ? "No files or folders match your search." : "No files inventoried."}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
