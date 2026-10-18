import * as sitesApi from "../../shared/api/sites.js";
import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { createPortal } from "react-dom";
import { nav } from "../../shared/navigation/router.js";

import { IconPlus } from "../../shared/ui/Icons.jsx";
import { EmptyState } from "../../shared/ui/EmptyState.jsx";
import { NavigationRow } from "../../shared/ui/NavigationRow.jsx";
import { PageError } from "../../shared/ui/Notice.jsx";

// ── Sites list ────────────────────────────────────────────────────────────────

function SiteExportMenu({ site }) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState(null);
  const buttonRef = useRef(null);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!buttonRef.current?.contains(event.target) && !menuRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    const closeOnScroll = () => setOpen(false);
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    window.addEventListener("scroll", closeOnScroll, true);
    window.addEventListener("resize", closeOnScroll);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
      window.removeEventListener("scroll", closeOnScroll, true);
      window.removeEventListener("resize", closeOnScroll);
    };
  }, [open]);

  const toggle = () => {
    if (!open) {
      const bounds = buttonRef.current.getBoundingClientRect();
      setPosition({ top: bounds.bottom + 6, right: window.innerWidth - bounds.right });
    }
    setOpen((current) => !current);
  };

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="btn secondary sm"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={toggle}
      >
        Export ↓
      </button>
      {open &&
        createPortal(
          <div
            ref={menuRef}
            className="sast-actions-popover"
            role="menu"
            style={{ position: "fixed", ...position }}
          >
            <a
              href={`/api/sites/${site.id}/export?configuration_only=true`}
              download
              role="menuitem"
              onClick={() => setOpen(false)}
            >
              Export settings only
            </a>
            <a
              href={`/api/sites/${site.id}/export`}
              download
              role="menuitem"
              onClick={() => setOpen(false)}
            >
              Export settings and runs
            </a>
          </div>,
          document.body,
        )}
    </>
  );
}

export function SitesList() {
  const [sites, setSites] = useState(null);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
  const [sortField, setSortField] = useState("name");
  const [sortDir, setSortDir] = useState("asc");
  const importRef = useRef(null);

  const load = useCallback(async () => {
    try {
      setSites(await sitesApi.listSites());
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const sortArrow = (field) => {
    if (sortField !== field) return null;
    return (
      <span style={{ marginLeft: "4px", fontSize: "10px", opacity: 0.85 }}>
        {sortDir === "asc" ? "▲" : "▼"}
      </span>
    );
  };

  const sortedSites = useMemo(() => {
    if (!sites) return [];
    return [...sites].sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (sortField === "credential_count") {
        valA = a.credential_count || 0;
        valB = b.credential_count || 0;
      }

      if (valA == null) valA = "";
      if (valB == null) valB = "";

      let cmp =
        typeof valA === "number" && typeof valB === "number"
          ? valA - valB
          : String(valA).localeCompare(String(valB), undefined, {
              sensitivity: "base",
              numeric: true,
            });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [sites, sortField, sortDir]);

  const onDelete = async (s) => {
    if (!confirm(`Delete "${s.name}"? This also removes all test runs and credentials.`)) return;
    try {
      await sitesApi.deleteSite(s.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const onImportFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    e.target.value = "";
    setImporting(true);
    setError(null);
    try {
      const text = await file.text();
      await sitesApi.importSite(text);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  return (
    <>
      <div className="topbar">
        <div className="topbar-title">Sites</div>
        <div className="topbar-actions">
          <input
            ref={importRef}
            type="file"
            accept=".json"
            style={{
              display: "none",
            }}
            onChange={onImportFile}
          />
          <button
            className="btn secondary"
            onClick={() => importRef.current.click()}
            disabled={importing}
          >
            {importing ? "Importing…" : "Import site"}
          </button>
          <button className="btn" onClick={() => nav("#/sites/new")}>
            <IconPlus /> New site
          </button>
        </div>
      </div>
      <div className="content scroll-content">
        <PageError error={error} inline={!sites} onDismiss={() => setError(null)} />
        {sites === null && <div className="subtle">Loading…</div>}
        {sites !== null && sites.length === 0 && (
          <EmptyState
            title="No sites configured"
            sub="Add a target site to begin setting up your pentest scope."
            action={
              <button className="btn" onClick={() => nav("#/sites/new")}>
                <IconPlus /> New site
              </button>
            }
          />
        )}
        {sites && sites.length > 0 && (
          <div className="table-wrap">
            <table>
              <colgroup>
                <col
                  style={{
                    width: "38%",
                  }}
                />
                <col
                  style={{
                    width: "32%",
                  }}
                />
                <col
                  style={{
                    width: "12%",
                  }}
                />
                <col
                  style={{
                    width: "18%",
                  }}
                />
              </colgroup>
              <thead>
                <tr>
                  <th
                    style={{ cursor: "pointer", userSelect: "none" }}
                    onClick={() => toggleSort("name")}
                  >
                    Name {sortArrow("name")}
                  </th>
                  <th
                    style={{ cursor: "pointer", userSelect: "none" }}
                    onClick={() => toggleSort("base_url")}
                  >
                    Base URL {sortArrow("base_url")}
                  </th>
                  <th
                    style={{ cursor: "pointer", userSelect: "none" }}
                    onClick={() => toggleSort("credential_count")}
                  >
                    Credentials {sortArrow("credential_count")}
                  </th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sortedSites.map((s) => (
                  <NavigationRow key={s.id} href={`#/sites/${s.id}`} label={`Open ${s.name}`}>
                    <td>
                      <a
                        href={`#/sites/${s.id}`}
                        style={{
                          fontWeight: 600,
                        }}
                      >
                        {s.name}
                      </a>
                    </td>
                    <td className="url">{s.base_url}</td>
                    <td>
                      {s.credential_count > 0 ? (
                        s.credential_count
                      ) : (
                        <span className="subtle">—</span>
                      )}
                    </td>
                    <td>
                      <div
                        className="row"
                        style={{
                          justifyContent: "flex-end",
                        }}
                      >
                        <button className="btn secondary sm" onClick={() => nav(`#/sites/${s.id}`)}>
                          Open
                        </button>
                        <SiteExportMenu site={s} />
                        <button className="btn danger-outline sm" onClick={() => onDelete(s)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </NavigationRow>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
