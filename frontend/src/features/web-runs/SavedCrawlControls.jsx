import { useEffect, useRef, useState } from "react";
import * as sitesApi from "../../shared/api/sites.js";
import * as webRunsApi from "../../shared/api/webRuns.js";
import { fmtDate } from "../../shared/lib/dates.js";
import { fmtSize } from "../../shared/lib/sizes.js";

function usePopover() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!ref.current?.contains(event.target)) setOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);
  return { open, setOpen, ref };
}

export function LoadSavedCrawlButton({ siteId, runId, onLoaded, onError }) {
  const { open, setOpen, ref } = usePopover();
  const [items, setItems] = useState(null);
  const [loadingId, setLoadingId] = useState(null);

  useEffect(() => {
    if (!open || !siteId) return;
    let cancelled = false;
    setItems(null);
    sitesApi
      .listSavedCrawls(siteId)
      .then((list) => !cancelled && setItems(list))
      .catch((e) => {
        if (cancelled) return;
        setItems([]);
        onError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [open, siteId, onError]);

  const choose = async (saved) => {
    setLoadingId(saved.id);
    try {
      const run = await webRunsApi.loadSavedCrawl(runId, saved.id);
      setOpen(false);
      await onLoaded(run);
    } catch (e) {
      onError(e.message);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="saved-crawl-control" ref={ref}>
      <button
        className="btn secondary sm"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        Load saved crawl
      </button>
      {open && (
        <div className="saved-crawl-popover" role="menu">
          {items === null && <div className="subtle saved-crawl-popover-note">Loading…</div>}
          {items && items.length === 0 && (
            <div className="subtle saved-crawl-popover-note">
              No saved crawls for this site yet.
            </div>
          )}
          {items?.map((saved) => (
            <button
              key={saved.id}
              role="menuitem"
              className="saved-crawl-option"
              disabled={loadingId !== null}
              onClick={() => choose(saved)}
            >
              <span className="saved-crawl-option-name">
                {loadingId === saved.id ? "Loading…" : saved.name}
              </span>
              <span className="subtle saved-crawl-option-meta">
                {saved.page_count} pages · {fmtSize(saved.size_bytes)} · {fmtDate(saved.created_at)}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function SaveCrawlButton({ run, onError }) {
  const { open, setOpen, ref } = usePopover();
  const [form, setForm] = useState({ name: "", notes: "" });
  const [busy, setBusy] = useState(false);
  const [savedName, setSavedName] = useState("");

  const toggle = () => {
    if (!open) {
      setForm({ name: `${run.name} – ${new Date().toLocaleDateString()}`, notes: "" });
      setSavedName("");
    }
    setOpen((value) => !value);
  };
  const submit = async (event) => {
    event.preventDefault();
    if (!form.name.trim()) return;
    setBusy(true);
    try {
      const saved = await webRunsApi.saveCrawl(run.id, {
        name: form.name.trim(),
        notes: form.notes.trim() || null,
      });
      setSavedName(saved.name);
    } catch (e) {
      onError(e.message);
      setOpen(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="saved-crawl-control" ref={ref}>
      <button
        className="btn secondary sm"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={toggle}
      >
        Save crawl to site
      </button>
      {open && (
        <div className="saved-crawl-popover" role="dialog" aria-label="Save crawl to site">
          {savedName ? (
            <div className="saved-crawl-popover-note">
              Saved as <strong>{savedName}</strong>. Load it into a new run from that run's page.
              <div className="row" style={{ justifyContent: "flex-end", marginTop: 8 }}>
                <a className="btn secondary sm" href={`#/sites/${run.site_id}`}>
                  View saved crawls
                </a>
                <button className="btn sm" onClick={() => setOpen(false)}>
                  Done
                </button>
              </div>
            </div>
          ) : (
            <form className="stack" style={{ gap: 8 }} onSubmit={submit}>
              <div className="field" style={{ margin: 0 }}>
                <label>Name</label>
                <input
                  autoFocus
                  aria-label="Name"
                  value={form.name}
                  maxLength={200}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div className="field" style={{ margin: 0 }}>
                <label>
                  Note <span className="field-optional">(optional)</span>
                </label>
                <input
                  aria-label="Note"
                  value={form.notes}
                  maxLength={2000}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                />
              </div>
              <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
                <button type="button" className="btn ghost sm" onClick={() => setOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn sm" disabled={busy || !form.name.trim()}>
                  {busy ? "Saving…" : "Save"}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
