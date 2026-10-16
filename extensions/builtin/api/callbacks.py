"""Turn scan state changes into signed callbacks and send them.

AESPA's run-change notices only say which run may have changed. Each pass
reads the current status of changed scans (and, every ``RECHECK_SECONDS``, of
every unfinished scan with a callback URL), compares it with what was last
seen, and queues events. A separate step sends queued callbacks with retries.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlmodel import select

from aespa.extensions import ExtensionDataStore

from . import scans
from .auth import aware
from .models import ApiDelivery, ApiIdempotency, ApiScan, now

log = logging.getLogger(__name__)

RECHECK_SECONDS = 15
PROGRESS_INTERVAL = timedelta(minutes=1)
REQUEST_TIMEOUT = 10.0
# Delay before each retry; a delivery is given up after len(RETRY_DELAYS) + 1 tries.
RETRY_DELAYS = (
    timedelta(seconds=30),
    timedelta(minutes=2),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(minutes=30),
)
IDEMPOTENCY_TTL = timedelta(hours=24)
TERMINAL = {
    "completed": "scan.completed",
    "failed": "scan.failed",
    "stopped": "scan.stopped",
}
ACTIVE = {"preparing", "running", "needs_action"}


class ChangedRuns:
    """Run IDs reported by AESPA since the last pass. Safe across threads."""

    def __init__(self) -> None:
        self._ids: set[int] = set()
        self._lock = threading.Lock()

    def add(self, run_id: int, _kind: str = "", _reason: str = "") -> None:
        with self._lock:
            self._ids.add(run_id)

    def take(self) -> set[int]:
        with self._lock:
            ids, self._ids = self._ids, set()
        return ids


def sign(secret: str, timestamp: int, body: bytes) -> str:
    digest = hmac.new(
        secret.encode("utf-8"), f"{timestamp}.".encode("ascii") + body, hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def events_for(row: ApiScan, status: dict[str, Any], at: datetime) -> list[str]:
    """Events caused by moving from the row's last state to ``status``.

    Every scan reports ``scan.started`` once, before any other event, even
    when it paused or finished before AESPA first saw it running.
    """
    state, phase = status["state"], status.get("phase")
    previous = row.last_state
    if state == "queued":
        return []
    events: list[str] = []
    if previous in (None, "queued"):
        events.append("scan.started")
    if state in TERMINAL:
        if previous not in TERMINAL:
            events.append(TERMINAL[state])
        return events
    if state in ACTIVE and previous == "paused":
        events.append("scan.phase_changed")
    elif (
        state in ACTIVE and previous not in (None, "queued") and phase != row.last_phase
    ):
        events.append("scan.phase_changed")
    if state == "needs_action" and previous != "needs_action":
        events.append("scan.needs_action")
    if state == "paused" and previous != "paused":
        events.append("scan.paused")
    sent = aware(row.last_progress_sent_at)
    if (
        state == "running"
        and status.get("percent") is not None
        and status.get("percent") != row.last_percent
        and (sent is None or at - sent >= PROGRESS_INTERVAL)
    ):
        events.append("scan.progress")
    return events


def check_scans(
    store: ExtensionDataStore,
    core,
    changed: set[int] | None = None,
    *,
    at: datetime | None = None,
) -> int:
    """Queue callbacks for scans whose state changed. Returns how many."""
    at = at or now()
    queued = 0
    with store.session() as session:
        query = (
            select(ApiScan)
            .where(ApiScan.finished == False)  # noqa: E712
            .where(ApiScan.callback_url != None)  # noqa: E711
        )
        if changed is not None:
            if not changed:
                return 0
            query = query.where(ApiScan.run_id.in_(changed))
        rows = session.exec(query).all()
        for row in rows:
            try:
                status = scans.status_payload(core, row)
            except Exception:  # noqa: BLE001 - one deleted run must not stop others
                row.finished = True
                session.add(row)
                continue
            wanted = set(scans.callback_events(row))
            for event in events_for(row, status, at):
                if event == "scan.progress":
                    row.last_progress_sent_at = at
                    row.last_percent = status["percent"]
                if event not in wanted:
                    continue
                delivery_id = str(uuid.uuid4())
                payload = {
                    "id": delivery_id,
                    "event": event,
                    "created_at": at.isoformat(),
                    "scan": status,
                }
                session.add(
                    ApiDelivery(
                        delivery_id=delivery_id,
                        scan_id=row.id,
                        event=event,
                        url=row.callback_url,
                        payload_json=json.dumps(payload),
                        next_attempt_at=at,
                    )
                )
                queued += 1
            row.last_state = status["state"]
            row.last_phase = status.get("phase")
            row.finished = status["state"] in TERMINAL
            session.add(row)
        session.commit()
    return queued


def deliver_due(
    store: ExtensionDataStore,
    client: httpx.Client,
    *,
    at: datetime | None = None,
    limit: int = 20,
) -> int:
    """Send callbacks that are due. Returns how many were delivered."""
    at = at or now()
    delivered = 0
    with store.session() as session:
        items = session.exec(
            select(ApiDelivery)
            .where(ApiDelivery.status == "pending")
            .where(ApiDelivery.next_attempt_at <= at)
            .order_by(ApiDelivery.id)
            .limit(limit)
        ).all()
        for item in items:
            scan = session.get(ApiScan, item.scan_id)
            secret = scan.callback_secret if scan else None
            body = item.payload_json.encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "AESPA-API/1",
                "X-AESPA-Event": item.event,
                "X-AESPA-Delivery": item.delivery_id,
            }
            if secret:
                headers["X-AESPA-Signature"] = sign(secret, int(at.timestamp()), body)
            item.attempts += 1
            try:
                response = client.post(item.url, content=body, headers=headers)
                item.last_status_code = response.status_code
                ok = 200 <= response.status_code < 300
                item.last_error = None if ok else f"HTTP {response.status_code}"
            except httpx.HTTPError as exc:
                ok = False
                item.last_status_code = None
                item.last_error = type(exc).__name__
            if ok:
                item.status = "delivered"
                item.delivered_at = at
                delivered += 1
            elif item.attempts > len(RETRY_DELAYS):
                item.status = "failed"
            else:
                item.next_attempt_at = at + RETRY_DELAYS[item.attempts - 1]
            session.add(item)
        session.commit()
    return delivered


def prune(store: ExtensionDataStore, *, at: datetime | None = None) -> None:
    cutoff = (at or now()) - IDEMPOTENCY_TTL
    with store.session() as session:
        for row in session.exec(
            select(ApiIdempotency).where(ApiIdempotency.created_at < cutoff)
        ).all():
            session.delete(row)
        session.commit()


def make_client() -> httpx.Client:
    return httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=False)


def run_worker(
    store: ExtensionDataStore,
    core,
    changed: ChangedRuns,
    stop: threading.Event,
    is_current,
    is_enabled=lambda: True,
) -> None:
    """Background loop. Ends when the extension is disabled or reloaded."""
    next_full_check = 0.0
    next_prune = 0.0
    with make_client() as client:
        while not stop.wait(1.0) and is_current():
            clock = time.monotonic()
            try:
                if not is_enabled():
                    changed.take()
                    continue
                if clock >= next_full_check:
                    changed.take()
                    check_scans(store, core)
                    next_full_check = clock + RECHECK_SECONDS
                else:
                    check_scans(store, core, changed.take())
                deliver_due(store, client)
                if clock >= next_prune:
                    prune(store)
                    next_prune = clock + 3600
            except Exception:  # noqa: BLE001 - keep the worker alive
                log.debug("API callback worker pass failed", exc_info=True)
