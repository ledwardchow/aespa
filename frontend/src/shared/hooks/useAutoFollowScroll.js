import { useCallback, useLayoutEffect, useRef } from "react";

export const AUTO_FOLLOW_BOTTOM_THRESHOLD = 24;

export function isNearScrollBottom(element, threshold = AUTO_FOLLOW_BOTTOM_THRESHOLD) {
  return element.scrollHeight - element.clientHeight - element.scrollTop <= threshold;
}

export function useAutoFollowScroll(activeKey, content, pending) {
  const historyRef = useRef(null);
  const shouldAutoFollowRef = useRef(true);
  const lastScrollTopRef = useRef(0);
  const previousActiveKeyRef = useRef(activeKey);

  const handleScroll = useCallback((event) => {
    const element = event.currentTarget;
    const scrollingUp = element.scrollTop < lastScrollTopRef.current;

    if (scrollingUp) {
      shouldAutoFollowRef.current = false;
    } else if (isNearScrollBottom(element)) {
      shouldAutoFollowRef.current = true;
    }

    lastScrollTopRef.current = element.scrollTop;
  }, []);

  useLayoutEffect(() => {
    const element = historyRef.current;
    const activeKeyChanged = previousActiveKeyRef.current !== activeKey;

    if (activeKeyChanged) shouldAutoFollowRef.current = true;
    previousActiveKeyRef.current = activeKey;

    if (!element || !shouldAutoFollowRef.current) return;

    element.scrollTop = element.scrollHeight;
    lastScrollTopRef.current = element.scrollTop;
  }, [activeKey, content, pending]);

  return { historyRef, handleScroll };
}
