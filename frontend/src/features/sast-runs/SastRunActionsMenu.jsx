import { useEffect, useRef, useState } from "react";

export function SastRunActionsMenu({ runId, onDelete }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!menuRef.current?.contains(event.target)) setOpen(false);
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

  return (
    <div className="sast-actions-menu" ref={menuRef}>
      <button
        className="btn ghost sast-actions-menu-trigger"
        type="button"
        aria-label="More run actions"
        aria-haspopup="menu"
        aria-expanded={open}
        title="More run actions"
        onClick={() => setOpen((current) => !current)}
      >
        ⋯
      </button>
      {open && (
        <div className="sast-actions-popover" role="menu">
          <a
            href={`/api/sast-runs/${runId}/export`}
            download
            role="menuitem"
            onClick={() => setOpen(false)}
          >
            Export run
          </a>
          <button
            type="button"
            className="danger"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onDelete();
            }}
          >
            Delete run
          </button>
        </div>
      )}
    </div>
  );
}
