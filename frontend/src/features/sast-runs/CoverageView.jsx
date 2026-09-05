export function CoverageView({ coverage, workProgram }) {
  const summary = coverage?.summary || {};
  const files = coverage?.files || [];
  const total = workProgram?.files?.total ?? summary.files_total ?? 0;
  const directlyOpened = workProgram?.files?.directly_opened ?? summary.files_reviewed ?? 0;
  const percent = total ? Math.round((directlyOpened / total) * 100) : 0;
  const languages = Object.entries(summary.languages || {}).sort((a, b) => b[1].total - a[1].total);
  return (
    <div className="sast-coverage-layout">
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
