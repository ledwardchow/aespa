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

/**
 * A message in the lower-right corner of the window. It never moves the page
 * content. Errors stay until dismissed; other messages also close on their own
 * after a few seconds.
 */
export function Notice({ variant = "error", onDismiss, children }) {
  // Parents usually pass a new callback on every render; keep the latest one
  // so polling pages do not restart the timer.
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

/**
 * A page's error. When nothing has loaded, the error is the page's content and
 * stays inline; otherwise it is a dismissible notice in the corner.
 */
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
