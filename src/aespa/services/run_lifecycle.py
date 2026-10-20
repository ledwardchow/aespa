"""Notify in-process listeners that a run may have changed state.

Listeners get only ``(run_id, run_kind, reason)``. They should read the run's
current state through ``run_progress.get_progress`` rather than trusting the
notice, because notices are hints: they can arrive in bursts, and none are sent
for changes made while AESPA was not running. Listeners must return quickly and
must not raise; they run on the thread that emitted the event.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

log = logging.getLogger(__name__)

Listener = Callable[[int, str, str], None]

_listeners: list[Listener] = []
_lock = threading.Lock()

# High-volume events that never mean a state change.
_IGNORED_EVENTS = frozenset(
    {
        "http",
        "http_request",
        "http_response",
        "text",
        "timing",
        "timing_delta",
        "body_diff",
        "screenshot",
        "status_delta",
        "marker",
        "action_log",
        "node_accessible_by",
    }
)


def subscribe(listener: Listener) -> Callable[[], None]:
    """Register a listener and return a function that removes it."""
    with _lock:
        _listeners.append(listener)

    def unsubscribe() -> None:
        with _lock:
            if listener in _listeners:
                _listeners.remove(listener)

    return unsubscribe


def publish(run_id: int, run_kind: str, reason: str) -> None:
    if not _listeners or reason in _IGNORED_EVENTS:
        return
    with _lock:
        listeners = list(_listeners)
    for listener in listeners:
        try:
            listener(run_id, run_kind, reason)
        except Exception:  # noqa: BLE001 - a listener must not break a scan
            log.debug("Run lifecycle listener failed", exc_info=True)
