import { useEffect, useRef } from "react";
import styles from "./SiteSummary.module.css";

export function CheckboxSelector({ label, options, selected, onToggle, onSelectAll }) {
  const ref = useRef(null);
  useEffect(() => {
    const closeOutside = (event) => {
      if (!ref.current?.contains(event.target) && ref.current) ref.current.open = false;
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, []);
  const selection =
    selected.length === options.length
      ? "All"
      : selected.length === 1
        ? selected[0]
        : `${selected.length} selected`;
  return (
    <div className={styles.selector}>
      <span className={styles.label}>{label}</span>
      <details
        ref={ref}
        className={styles.dropdown}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            ref.current.open = false;
            ref.current.querySelector("summary").focus();
          }
        }}
      >
        <summary aria-label={label}>
          {selection}
          <span aria-hidden="true">⌄</span>
        </summary>
        <fieldset className={styles.menu}>
          <legend className={styles.menuTitle}>{label}</legend>
          <label className={styles.selectAll}>
            <input
              type="checkbox"
              checked={options.length > 0 && selected.length === options.length}
              ref={(element) => {
                if (element)
                  element.indeterminate = selected.length > 0 && selected.length < options.length;
              }}
              disabled={!options.length}
              onChange={(event) => onSelectAll(event.target.checked)}
            />
            Select all
          </label>
          {options.map((option) => (
            <label key={option}>
              <input
                type="checkbox"
                checked={selected.includes(option)}
                onChange={(event) => onToggle(option, event.target.checked)}
              />
              {option}
            </label>
          ))}
          {!options.length && <span className="subtle">No models available</span>}
        </fieldset>
      </details>
    </div>
  );
}
