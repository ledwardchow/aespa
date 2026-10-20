import { useState } from "react";
import { ApiError } from "../api/request.ts";
import { importLeadReport, type DynamicRunKind, type ReportPreview } from "../api/sastImport.ts";
import { downloadTextFile } from "../lib/download.js";
import styles from "./SastImportDialog.module.css";

const markdownTemplate = `# External scanner findings

## Missing ownership check on account export

- Scanner: My scanner
- Rule ID: access-control-001
- Severity: high
- Category: A01
- Location: src/api/accounts.py:42
- Suggested endpoint: GET /api/accounts/{id}/export

### Description

The export handler accepts an account ID without checking whether the caller owns the account.
Verify the behavior against the live target before treating this as a confirmed finding.

### Evidence

\`\`\`python
return export_account(request.path_params["id"])
\`\`\`

## Another finding title

- Scanner: My scanner
- Severity: medium
- Location: src/api/example.py:12

### Description

Describe the suspected issue and how DAST could verify it.
`;

type Props = {
  runId: number;
  runKind: DynamicRunKind;
  busy: boolean;
  onBusyChange: (busy: boolean) => void;
  onClose: () => void;
  onImported: (count: number) => Promise<void>;
};

export function ReportImportPanel({
  runId,
  runKind,
  busy,
  onBusyChange,
  onClose,
  onImported,
}: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(importNow: boolean) {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setError("Reports must be 5 MiB or smaller.");
      return;
    }
    onBusyChange(true);
    setError(null);
    try {
      const result = await importLeadReport(runKind, runId, file, !importNow);
      if (importNow) {
        await onImported(result.imported);
        onClose();
      } else {
        setPreview(result);
      }
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 404 && e.message.toLowerCase() === "not found"
          ? "File import requires the updated backend. Wait until running scans finish, then restart AESPA."
          : e instanceof Error
            ? e.message
            : "Could not read the report.",
      );
    } finally {
      onBusyChange(false);
    }
  }
  return (
    <>
      <div className={styles.filePicker}>
        <label htmlFor="sast-report-file">Scanner report</label>
        <input
          id="sast-report-file"
          type="file"
          accept=".sarif,.json,.md,.markdown"
          disabled={busy}
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setPreview(null);
            setError(null);
          }}
        />
        <p>
          SARIF 2.1.0 or structured Markdown, up to 5 MiB. Imported findings remain unverified until
          DAST investigates them.
        </p>
        <p>
          For Markdown, use one <code>## Finding title</code> section per lead, with Severity and
          Location fields, then Description and Evidence sections. AESPA lead exports are also
          supported.
        </p>
        <button
          className="btn sm"
          disabled={busy}
          onClick={() =>
            downloadTextFile(
              "sast-leads-template.md",
              markdownTemplate,
              "text/markdown;charset=utf-8",
            )
          }
        >
          Download Markdown template
        </button>
      </div>
      {error && (
        <div className={styles.error} role="alert">
          {error}
        </div>
      )}
      {preview && (
        <>
          <div className={styles.selection} aria-live="polite">
            <strong>
              {preview.filename} · {preview.format}
            </strong>
            <span>
              {preview.new_count} new lead{preview.new_count === 1 ? "" : "s"} ·{" "}
              {preview.already_imported} already imported · {preview.skipped} skipped
            </span>
            {preview.warnings.map((warning) => (
              <span key={warning}>{warning}</span>
            ))}
            {preview.total === 0 && <span>No importable findings were found in this report.</span>}
          </div>
          <div className={styles.results}>
            <ul className={styles.previewList} aria-label="Report preview">
              {preview.items.map((item, index) => (
                <li key={index}>
                  <strong>{item.title}</strong>
                  <span>
                    {item.severity} · {item.scanner}
                    {item.already_imported ? " · Already imported" : ""}
                  </span>
                  <span>{item.location || "Location not provided"}</span>
                </li>
              ))}
            </ul>
            {preview.total > preview.preview_limit && (
              <p className={styles.empty}>
                Showing the first {preview.preview_limit} of {preview.total} leads.
              </p>
            )}
          </div>
        </>
      )}
      <footer className={styles.footer}>
        <span>{busy ? "Reading report…" : "No scan starts when you import."}</span>
        <div>
          <button className="btn" disabled={busy} onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn primary"
            disabled={!file || busy || preview?.new_count === 0}
            onClick={() => submit(preview !== null)}
          >
            {busy
              ? "Please wait…"
              : preview
                ? `Import ${preview.new_count} new lead${preview.new_count === 1 ? "" : "s"}`
                : "Preview report"}
          </button>
        </div>
      </footer>
    </>
  );
}
