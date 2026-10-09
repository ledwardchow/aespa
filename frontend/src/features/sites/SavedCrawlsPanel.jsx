import { useCallback, useEffect, useRef, useState } from "react";
import * as sitesApi from "../../shared/api/sites.js";
import { fmtDate } from "../../shared/lib/dates.js";
import { fmtSize } from "../../shared/lib/sizes.js";
import { IconChevronDown } from "../../shared/ui/Icons.jsx";

const CRAWLER_MODE_LABELS = { url: "URL", interactive: "Interactive SPA" };

function SavedCrawlRow({ siteId, saved, onChanged, onDeleted, onError }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ name: saved.name, notes: saved.notes || "" });
  const [busy, setBusy] = useState(false);

  const startEdit = () => {
    setForm({ name: saved.name, notes: saved.notes || "" });
    setEditing(true);
  };
  const save = async () => {
    if (!form.name.trim()) return;
    setBusy(true);
    try {
      onChanged(
        await sitesApi.updateSavedCrawl(siteId, saved.id, {
          name: form.name.trim(),
          notes: form.notes.trim(),
        }),
      );
      setEditing(false);
    } catch (e) {
      onError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const remove = async () => {
    if (
      !confirm(`Delete saved crawl "${saved.name}"? Runs already loaded from it keep their data.`)
    )
      return;
    try {
      await sitesApi.deleteSavedCrawl(siteId, saved.id);
      onDeleted(saved.id);
    } catch (e) {
      onError(e.message);
    }
  };

  if (editing) {
    return (
      <tr>
        <td colSpan={7}>
          <div className="row" style={{ gap: 8, alignItems: "center" }}>
            <input
              aria-label="Name"
              value={form.name}
              maxLength={200}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              style={{ flex: "1 1 30%" }}
            />
            <input
              aria-label="Note"
              placeholder="Note (optional)"
              value={form.notes}
              maxLength={2000}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              style={{ flex: "1 1 50%" }}
            />
            <button className="btn sm" onClick={save} disabled={busy || !form.name.trim()}>
              {busy ? "Saving…" : "Save"}
            </button>
            <button className="btn ghost sm" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td>
        <strong>{saved.name}</strong>
        {saved.notes && (
          <div className="subtle" style={{ fontSize: 12, marginTop: 2 }}>
            {saved.notes}
          </div>
        )}
      </td>
      <td>{saved.page_count}</td>
      <td>{CRAWLER_MODE_LABELS[saved.crawler_mode] || saved.crawler_mode}</td>
      <td>{fmtSize(saved.size_bytes)}</td>
      <td className="subtle">{fmtDate(saved.created_at)}</td>
      <td>
        {saved.source_run_id == null ? (
          <span className="subtle">From file</span>
        ) : saved.source_run_exists ? (
          <a href={`#/runs/${saved.source_run_id}`}>Run #{saved.source_run_id}</a>
        ) : (
          <span className="subtle">Run deleted</span>
        )}
      </td>
      <td>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn secondary sm" onClick={startEdit}>
            Edit
          </button>
          <button
            className="btn secondary sm"
            onClick={() => sitesApi.downloadSavedCrawl(siteId, saved.id)}
          >
            Download
          </button>
          <button className="btn danger-outline sm" onClick={remove}>
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
}

export function SavedCrawlsPanel({ siteId }) {
  const [items, setItems] = useState(null);
  const [expanded, setExpanded] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  const load = useCallback(async () => {
    try {
      setItems(await sitesApi.listSavedCrawls(siteId));
    } catch (e) {
      setError(e.message);
    }
  }, [siteId]);

  useEffect(() => {
    load();
  }, [load]);

  const onFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const saved = await sitesApi.uploadSavedCrawl(siteId, file);
      setItems((list) => [saved, ...(list || [])]);
      setExpanded(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const count = items?.length || 0;
  const totalSize = (items || []).reduce((sum, item) => sum + (item.size_bytes || 0), 0);

  return (
    <div className="card saved-crawls-panel">
      <div className="row spread">
        <button
          type="button"
          className="saved-crawls-heading"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
        >
          <span className={`site-details-chevron${expanded ? " is-expanded" : ""}`}>
            <IconChevronDown />
          </span>
          Saved crawls
          {items && <span className="subtle saved-crawls-count">{count}</span>}
        </button>
        <button
          className="btn secondary sm"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? "Adding…" : "Add from file"}
        </button>
        <input ref={fileRef} type="file" accept="application/json,.json" hidden onChange={onFile} />
      </div>
      {error && (
        <div className="alert error" style={{ marginTop: 10 }}>
          {error}
        </div>
      )}
      {expanded && items === null && !error && (
        <div className="subtle" style={{ marginTop: 10 }}>
          Loading…
        </div>
      )}
      {expanded && items && count === 0 && (
        <div className="subtle" style={{ marginTop: 10, fontSize: 13 }}>
          No saved crawls yet. Open a run with crawl data and choose Save crawl to site.
        </div>
      )}
      {expanded && count > 0 && (
        <>
          <div className="table-wrap saved-crawls-table">
            <table>
              <colgroup>
                <col style={{ width: "30%" }} />
                <col style={{ width: "7%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "8%" }} />
                <col style={{ width: "14%" }} />
                <col style={{ width: "9%" }} />
                <col style={{ width: "20%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Pages</th>
                  <th>Crawler mode</th>
                  <th>Size</th>
                  <th>Saved on</th>
                  <th>From</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((saved) => (
                  <SavedCrawlRow
                    key={saved.id}
                    siteId={siteId}
                    saved={saved}
                    onError={setError}
                    onChanged={(updated) =>
                      setItems((list) =>
                        list.map((item) => (item.id === updated.id ? updated : item)),
                      )
                    }
                    onDeleted={(id) => setItems((list) => list.filter((item) => item.id !== id))}
                  />
                ))}
              </tbody>
            </table>
          </div>
          <div className="subtle" style={{ marginTop: 8, fontSize: 12 }}>
            {count} saved crawl{count !== 1 ? "s" : ""} · {fmtSize(totalSize)}
          </div>
        </>
      )}
    </div>
  );
}
