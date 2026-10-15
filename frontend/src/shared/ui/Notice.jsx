import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";

import { DismissibleAlert } from "./DismissibleAlert.jsx";

const SUCCESS_HIDE_MS = 6000;

function noticeStack() {
  let stack = document.querySelector(".notice-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "notice-stack";
    document.body.appendChild(stack);
  }
  return stack;
}

export function Notice({ variant = "error", onDismiss, children }) {
  const dismissRef = useRef(onDismiss);
  dismissRef.current = onDismiss;
  useEffect(() => {
    if (variant === "error") return undefined;
    const timer = setTimeout(() => dismissRef.current?.(), SUCCESS_HIDE_MS);
    return () => clearTimeout(timer);
  }, [variant, children]);
  if (typeof document === "undefined") return null;
  return createPortal(
    <DismissibleAlert variant={variant} className="notice" onDismiss={onDismiss}>
      {children}
    </DismissibleAlert>,
    noticeStack(),
  );
}

export function PageError({ error, inline = false, onDismiss }) {
  if (!error) return null;
  if (inline) {
    return (
      <div className="alert error" role="alert">
        {error}
      </div>
    );
  }
  return <Notice onDismiss={onDismiss}>{error}</Notice>;
}
