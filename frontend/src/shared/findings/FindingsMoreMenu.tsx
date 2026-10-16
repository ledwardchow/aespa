import { useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";

export function FindingsMoreMenu({
  hasFindings,
  onExport,
  onImport,
  onClear,
  clearBusy = false,
}: {
  hasFindings: boolean;
  onExport: () => void;
  onImport: (event: ChangeEvent<HTMLInputElement>) => void;
  onClear?: () => void;
  clearBusy?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  const choose = (action: () => void) => {
    setOpen(false);
    action();
  };

  return (
    <div className="findings-more-menu" ref={menuRef}>
      <button
        className="btn secondary sm findings-more-trigger"
        type="button"
        aria-label="More finding actions"
        aria-haspopup="menu"
        aria-expanded={open}
        title="More finding actions"
        onClick={() => setOpen((current) => !current)}
      >
        ⋯
      </button>
      {open && (
        <div className="findings-more-popover" role="menu">
          {hasFindings && (
            <button type="button" role="menuitem" onClick={() => choose(onExport)}>
              Export findings
            </button>
          )}
          <button
            type="button"
            role="menuitem"
            onClick={() => choose(() => input.current?.click())}
          >
            Import findings
          </button>
          {hasFindings && onClear && (
            <>
              <div className="findings-more-separator" role="separator" />
              <button
                type="button"
                role="menuitem"
                className="danger"
                disabled={clearBusy}
                onClick={() => choose(onClear)}
              >
                {clearBusy ? "Clearing…" : "Clear all findings"}
              </button>
            </>
          )}
        </div>
      )}
      <input
        ref={input}
        type="file"
        accept=".md,text/markdown,text/plain"
        hidden
        onChange={onImport}
      />
    </div>
  );
}
