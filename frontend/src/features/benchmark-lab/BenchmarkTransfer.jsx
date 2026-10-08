import { useRef, useState } from "react";
import { benchmarkExportUrl, importBenchmarkData } from "../../shared/api/benchmarkTransfer";

export function BenchmarkTransfer({ onChange }) {
  const input = useRef(null);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const importFile = async (file) => {
    if (!file) return;
    setBusy(true);
    setReport(null);
    setError(null);
    try {
      const result = await importBenchmarkData(await file.text());
      setReport(result);
      await onChange();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="card">
      <h2>Share benchmark data</h2>
      <p className="subtle">
        Combine datasets, results, reviews, and comparisons from several installations. Existing
        records are kept. Repeated imports skip duplicates and report conflicting edits.
      </p>
      <p className="subtle">
        Files include finding evidence and scan details. Scan files, provider credentials, model
        settings, and local app assignments are not included.
      </p>
      <div className="form-actions">
        <a className="btn secondary" href={benchmarkExportUrl} download="aespa-benchmark-lab.json">
          Export benchmark data
        </a>
        <button
          className="btn secondary"
          type="button"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          {busy ? "Importing..." : "Import benchmark data"}
        </button>
        <input
          ref={input}
          type="file"
          accept=".json,application/json"
          hidden
          aria-label="Benchmark data file"
          onChange={(event) => {
            importFile(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
      </div>
      {error && (
        <p role="alert" className="alert error">
          {error}
        </p>
      )}
      {report && (
        <div role="status">
          <p>
            Datasets added: {report.datasets_added}. Records imported: {report.imported}. Duplicates
            skipped: {report.skipped}.
          </p>
          {report.conflicts.length > 0 && (
            <>
              <p>Conflicts: {report.conflicts.length}. Existing records were kept:</p>
              <ul>
                {report.conflicts.map((item) => (
                  <li key={item.key}>
                    {item.name || item.key} ({item.kind})
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </section>
  );
}
