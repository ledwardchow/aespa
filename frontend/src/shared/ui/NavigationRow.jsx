import { nav } from "../navigation/router.js";

const INTERACTIVE_SELECTOR =
  'a, button, input, select, textarea, summary, [role="button"], [role="link"], [contenteditable="true"]';

function startedInsideInteractiveElement(event) {
  return Boolean(event.target.closest?.(INTERACTIVE_SELECTOR));
}

export function NavigationRow({ href, label, className = "", children }) {
  if (!href) return <tr className={className || undefined}>{children}</tr>;

  const open = () => nav(href);

  const onClick = (event) => {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey ||
      startedInsideInteractiveElement(event)
    ) {
      return;
    }
    open();
  };

  const onKeyDown = (event) => {
    if (
      event.defaultPrevented ||
      startedInsideInteractiveElement(event) ||
      (event.key !== "Enter" && event.key !== " ")
    ) {
      return;
    }
    event.preventDefault();
    open();
  };

  return (
    <tr
      className={["navigation-row", className].filter(Boolean).join(" ")}
      tabIndex={0}
      aria-label={label}
      onClick={onClick}
      onKeyDown={onKeyDown}
    >
      {children}
    </tr>
  );
}
