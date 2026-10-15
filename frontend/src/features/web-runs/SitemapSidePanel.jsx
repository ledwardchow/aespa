import { useState } from "react";

import { IconChevronLeft, IconChevronRight } from "../../shared/ui/Icons.jsx";

const OPEN_KEY = "aespa_sitemap_details_open";

function initialOpen() {
  try {
    const saved = localStorage.getItem(OPEN_KEY);
    if (saved === "true" || saved === "false") return saved === "true";
  } catch {
  }
  return typeof window === "undefined" || window.innerWidth > 900;
}

export function SitemapSidePanel({ children }) {
  const [open, setOpen] = useState(initialOpen);
  const update = (value) => {
    setOpen(value);
    try {
      localStorage.setItem(OPEN_KEY, String(value));
    } catch {
    }
  };
  if (!open) {
    return (
      <div className="sitemap-side-rail">
        <button
          type="button"
          className="sitemap-side-rail-button"
          aria-expanded="false"
          aria-controls="sitemap-side-panel"
          title="Show crawl details"
          onClick={() => update(true)}
        >
          <IconChevronRight />
          <span className="sitemap-side-rail-label">Crawl details</span>
        </button>
      </div>
    );
  }
  return (
    <aside id="sitemap-side-panel" className="sitemap-side-panel" aria-label="Crawl details">
      <div className="sitemap-side-header">
        <span>Crawl details</span>
        <button
          type="button"
          className="btn ghost sm sitemap-side-collapse"
          aria-expanded="true"
          aria-controls="sitemap-side-panel"
          aria-label="Collapse crawl details"
          title="Collapse crawl details"
          onClick={() => update(false)}
        >
          <IconChevronLeft />
        </button>
      </div>
      {children}
    </aside>
  );
}

export function SidePanelSection({ id, title, count, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen);
  const bodyId = `sitemap-side-${id}`;
  return (
    <section className="side-section">
      <button
        type="button"
        className="side-section-head"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="side-section-caret" aria-hidden="true">
          {open ? "▾" : "▸"}
        </span>
        <span className="side-section-title">{title}</span>
        {count ? <span className="side-section-count">{count}</span> : null}
      </button>
      <div id={bodyId} className="side-section-body" hidden={!open}>
        {children}
      </div>
    </section>
  );
}
