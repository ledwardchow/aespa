import { useEffect, useRef, useState } from "react";
import {
  importSastSource,
  searchSastImportSources,
  type DynamicRunKind,
  type SastImportPage,
  type SastImportSource,
} from "../api/sastImport.ts";
import { ReportImportPanel } from "./ReportImportPanel.tsx";
import styles from "./SastImportDialog.module.css";

type Props = {
  runId: number;
  runKind: DynamicRunKind;
  onClose: () => void;
  onImported: (count: number) => Promise<void>;
};

export function SastImportDialog({ runId, runKind, onClose, onImported }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"scan" | "file">("scan");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<SastImportPage | null>(null);
  const [selected, setSelected] = useState<SastImportSource | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const element = dialog.current;
    const opener = document.activeElement;
    element?.showModal();
    search.current?.focus();
    return () => {
      element?.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);

  useEffect(() => {
    if (mode !== "scan") return;
    const controller = new AbortController();
    const timer = setTimeout(
      async () => {
        try {
          const data = await searchSastImportSources(
            runKind,
            runId,
            query,
            page,
            controller.signal,
          );
          if (controller.signal.aborted) return;
          setResult(data);
        } catch (e) {
          if (!controller.signal.aborted)
            setError(e instanceof Error ? e.message : "Could not load SAST scans.");
        } finally {
          if (!controller.signal.aborted) setLoading(false);
        }
      },
      query ? 250 : 0,
    );
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [runId, runKind, query, page, retry, mode]);

  function resetResults() {
    setResult(null);
    setLoading(true);
    setError(null);
    setSelected(null);
  }
  async function onImport() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const { imported } = await importSastSource(runKind, runId, selected.id);
      await onImported(imported);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not import leads.");
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      className={styles.dialog}
      aria-labelledby="sast-import-heading"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <header className={styles.header}>
        <div>
          <h2 id="sast-import-heading">Import SAST leads</h2>
          <p>Choose a source scan or import a report from another scanner.</p>
        </div>
        <button
          className="btn sm"
          aria-label="Close import dialog"
          disabled={busy}
          onClick={onClose}
        >
          ×
        </button>
      </header>
      <div
        className={styles.tabs}
        role="tablist"
        aria-label="Import source"
        onKeyDown={(event) => {
          if (busy || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
          event.preventDefault();
          const next =
            event.key === "Home"
              ? "scan"
              : event.key === "End"
                ? "file"
                : mode === "scan"
                  ? "file"
                  : "scan";
          setMode(next);
          if (next === "scan") resetResults();
          event.currentTarget
            .querySelector<HTMLButtonElement>(
              next === "scan" ? "#sast-source-scan" : "#sast-source-file",
            )
            ?.focus();
        }}
      >
        <button
          id="sast-source-scan"
          role="tab"
          aria-selected={mode === "scan"}
          tabIndex={mode === "scan" ? 0 : -1}
          aria-controls="sast-scan-panel"
          disabled={busy}
          onClick={() => {
            setMode("scan");
            resetResults();
          }}
        >
          AESPA scans
        </button>
        <button
          id="sast-source-file"
          role="tab"
          aria-selected={mode === "file"}
          tabIndex={mode === "file" ? 0 : -1}
          aria-controls="sast-file-panel"
          disabled={busy}
          onClick={() => setMode("file")}
        >
          Import from file
        </button>
      </div>
      {mode === "file" ? (
        <div
          id="sast-file-panel"
          role="tabpanel"
          aria-labelledby="sast-source-file"
          className={styles.tabPanel}
        >
          <ReportImportPanel
            runId={runId}
            runKind={runKind}
            busy={busy}
            onBusyChange={setBusy}
            onClose={onClose}
            onImported={onImported}
          />
        </div>
      ) : (
        <div
          id="sast-scan-panel"
          role="tabpanel"
          aria-labelledby="sast-source-scan"
          className={styles.tabPanel}
        >
          <div className={styles.search}>
            <label htmlFor="sast-import-search">Search scans</label>
            <input
              ref={search}
              id="sast-import-search"
              type="search"
              placeholder="Search by scan name, source filename, or ID…"
              maxLength={200}
              value={query}
              disabled={busy}
              onChange={(event) => {
                resetResults();
                setQuery(event.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className={styles.listHeading}>
            <span>
              {loading ? "Loading scans…" : `${result?.total ?? 0} completed scans with leads`}
            </span>
            <span>Newest first</span>
          </div>
          {error && (
            <div className={styles.error} role="alert">
              {error}
              <button
                className="btn sm"
                disabled={busy}
                onClick={() => {
                  resetResults();
                  setRetry((value) => value + 1);
                }}
              >
                Retry
              </button>
            </div>
          )}
          <div className={styles.results} aria-busy={loading}>
            {!loading && !error && result?.items.length === 0 && (
              <p className={styles.empty}>
                {query.trim()
                  ? "No scans match your search. Try another name, source filename, or ID."
                  : "No completed SAST scans with leads yet. Complete a SAST scan, then import its leads here."}
              </p>
            )}
            {!loading && result && (
              <fieldset className={styles.options} disabled={busy}>
                <legend className={styles.srOnly}>Source scan</legend>
                {result.items.map((scan) => (
                  <label
                    key={scan.id}
                    className={`${styles.scan} ${selected?.id === scan.id ? styles.selected : ""}`}
                  >
                    <input
                      type="radio"
                      name="sast-import-source"
                      checked={selected?.id === scan.id}
                      disabled={scan.new_count === 0}
                      onChange={() => setSelected(scan)}
                    />
                    <span className={styles.scanInfo}>
                      <strong>{scan.name || `SAST scan #${scan.id}`}</strong>
                      <span>{scan.source_filename || "Source filename unavailable"}</span>
                      <span>
                        #{scan.id} ·{" "}
                        {scan.completed_at
                          ? new Date(scan.completed_at).toLocaleString()
                          : "Completion date unavailable"}
                      </span>
                    </span>
                    <span className={styles.counts}>
                      <strong>
                        {scan.new_count === 0
                          ? scan.imported_count
                            ? "Already imported"
                            : "No importable leads"
                          : scan.new_count === undefined
                            ? `${scan.leads_count} leads`
                            : `${scan.new_count} new lead${scan.new_count === 1 ? "" : "s"}`}
                      </strong>
                      <span>
                        {scan.leads_count} total
                        {scan.imported_count !== undefined
                          ? ` · ${scan.imported_count} imported`
                          : ""}
                      </span>
                    </span>
                  </label>
                ))}
              </fieldset>
            )}
          </div>
          <div className={styles.pagination}>
            <span aria-live="polite">
              {!loading && result && result.total > 0
                ? `${(page - 1) * result.page_size + 1}–${Math.min(page * result.page_size, result.total)} of ${result.total}`
                : ""}
            </span>
            <div>
              <button
                className="btn sm"
                disabled={loading || busy || page === 1}
                onClick={() => {
                  resetResults();
                  setPage(page - 1);
                }}
              >
                Previous
              </button>
              <button
                className="btn sm"
                disabled={loading || busy || !result || page * result.page_size >= result.total}
                onClick={() => {
                  resetResults();
                  setPage(page + 1);
                }}
              >
                Next
              </button>
            </div>
          </div>
          <div className={styles.selection} aria-live="polite">
            {selected ? (
              <>
                <strong>{selected.name}</strong>
                <span>
                  {selected.new_count === undefined
                    ? "Existing leads will be skipped."
                    : `${selected.new_count} new lead${selected.new_count === 1 ? "" : "s"} to import · ${selected.imported_count} already imported`}
                </span>
              </>
            ) : (
              "Select a scan to import its leads."
            )}
          </div>
          <footer className={styles.footer}>
            <span>Existing leads will be skipped.</span>
            <div>
              <button className="btn" disabled={busy} onClick={onClose}>
                Cancel
              </button>
              <button
                className="btn primary"
                disabled={!selected || loading || busy || selected.new_count === 0}
                onClick={onImport}
              >
                {busy
                  ? "Importing…"
                  : selected?.new_count !== undefined
                    ? `Import ${selected.new_count} new lead${selected.new_count === 1 ? "" : "s"}`
                    : "Import leads"}
              </button>
            </div>
          </footer>
        </div>
      )}
    </dialog>
  );
}
