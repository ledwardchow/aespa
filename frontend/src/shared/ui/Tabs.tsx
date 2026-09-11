import type { KeyboardEvent, ReactNode } from "react";

export type Tab = { key: string; label: ReactNode; disabled?: boolean };
type Props = {
  tabs: Tab[];
  value: string;
  onChange: (value: string) => void;
  label: string;
  className?: string;
  buttonClassName?: string;
};

export function Tabs({
  tabs,
  value,
  onChange,
  label,
  className = "tab-bar",
  buttonClassName = "tab-btn",
}: Props) {
  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, key: string) {
    const available = tabs.filter((tab) => !tab.disabled);
    const index = available.findIndex((tab) => tab.key === key);
    const target =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? available.length - 1
          : event.key === "ArrowRight"
            ? (index + 1) % available.length
            : event.key === "ArrowLeft"
              ? (index + available.length - 1) % available.length
              : null;
    if (target === null) return;
    event.preventDefault();
    const next = available[target];
    onChange(next.key);
    const buttons = event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>(
      'button[role="tab"]:not(:disabled)',
    );
    buttons?.[target]?.focus();
  }
  return (
    <div className={className} role="tablist" aria-label={label}>
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          role="tab"
          className={`${buttonClassName}${value === tab.key ? " active" : ""}`}
          aria-selected={value === tab.key}
          tabIndex={value === tab.key ? 0 : -1}
          disabled={tab.disabled}
          onClick={() => onChange(tab.key)}
          onKeyDown={(event) => onKeyDown(event, tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
