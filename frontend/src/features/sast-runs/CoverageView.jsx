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
  const files = coverage?.files || [];
  const total = workProgram?.files?.total ?? summary.files_total ?? 0;
  const directlyOpened = workProgram?.files?.directly_opened ?? summary.files_reviewed ?? 0;
  const percent = total ? Math.round((directlyOpened / total) * 100) : 0;
  const languages = Object.entries(summary.languages || {}).sort((a, b) => b[1].total - a[1].total);
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
        <div className="sast-file-list">
          {files.slice(0, 250).map((file) => (
            <div key={file.path}>
              <span
                className={`sast-evidence-status status-${file.reviewed ? "complete" : "pending"}`}
              >
                {file.reviewed ? "✓" : "·"}
              </span>
              <code title={file.path}>{file.path}</code>
              <small>
                {file.language} · {file.read_count} read{file.read_count === 1 ? "" : "s"}
              </small>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
