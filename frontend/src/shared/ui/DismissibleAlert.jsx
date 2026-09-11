export function DismissibleAlert({ variant = "info", className = "", onDismiss, children }) {
  return (
    <div
      className={["alert", variant, "dismissible", className].filter(Boolean).join(" ")}
      role={variant === "error" ? "alert" : "status"}
    >
      <span className="alert-message">{children}</span>
      <button
        type="button"
        className="alert-dismiss"
        aria-label="Dismiss notification"
        onClick={onDismiss}
      >
        ×
      </button>
    </div>
  );
}
