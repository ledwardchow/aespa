"""Read plan usage percentages from the Codex CLI.

Codex reports the signed-in ChatGPT plan's usage windows through its
app-server. AESPA's Codex CLI provider always uses that account. ChatGPT plan
provider usage only counts when it uses the same ChatGPT account.
"""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from aespa.db import get_engine

from . import usage
from .models import Meta, Reading, now

STATUS_KEY = "codex_status"
WINDOW_MINUTES = {300: "five_hour", 10080: "weekly"}
_lock = threading.Lock()


def _configured_path() -> str | None:
    from aespa.models import CodexIntegrationConfig

    with Session(get_engine()) as session:
        row = session.get(CodexIntegrationConfig, 1)
        return row.executable_path if row else None


def _plan_email() -> str | None:
    """Email of the account selected for AESPA's ChatGPT plan provider."""
    from aespa.services import chatgpt_plan

    active = next(
        (row for row in chatgpt_plan.status()["accounts"] if row.get("active")), None
    )
    return (active or {}).get("email") or None


def parse(result: dict[str, Any]) -> dict[str, Any]:
    """Pick the regular Codex usage limit and its 5-hour and weekly windows."""
    limits = result.get("rate_limits") or {}
    by_id = limits.get("rateLimitsByLimitId")
    snapshot = by_id.get("codex") if isinstance(by_id, dict) else None
    if not isinstance(snapshot, dict):
        snapshot = limits.get("rateLimits")
    if not isinstance(snapshot, dict):
        snapshot = {}
    windows = []
    for key in ("primary", "secondary"):
        item = snapshot.get(key)
        if not isinstance(item, dict):
            continue
        window = WINDOW_MINUTES.get(item.get("windowDurationMins"))
        percent = item.get("usedPercent")
        if window is None or not isinstance(percent, (int, float)):
            continue
        reset = item.get("resetsAt")
        windows.append(
            {
                "window": window,
                "used_percent": float(percent),
                "resets_at": (
                    datetime.fromtimestamp(reset, timezone.utc)
                    if isinstance(reset, (int, float))
                    else None
                ),
            }
        )
    account = (result.get("account") or {}).get("account") or {}
    return {
        "email": account.get("email"),
        "plan_type": snapshot.get("planType") or account.get("planType"),
        "limit_id": snapshot.get("limitId"),
        "windows": windows,
    }


def _changed(last: Reading | None, item: dict[str, Any]) -> bool:
    if last is None or abs(last.used_percent - item["used_percent"]) > 1e-6:
        return True
    if (last.resets_at is None) != (item["resets_at"] is None):
        return True
    return bool(
        last.resets_at
        and abs(last.resets_at - item["resets_at"]) > usage.RESET_TOLERANCE
    )


def record(
    store, parsed: dict[str, Any], at: datetime, note: str = "", force: bool = False
) -> int:
    """Save a reading for each window whose percentage or reset time changed.

    ``force`` saves every window, such as when a scan starts or stops.
    """
    added = 0
    with store.session() as session:
        for item in parsed["windows"]:
            last = session.exec(
                select(Reading)
                .where(Reading.window == item["window"], Reading.source == "codex")
                .order_by(Reading.observed_at.desc())
            ).first()
            if force or _changed(last, item):
                session.add(
                    Reading(
                        window=item["window"],
                        used_percent=item["used_percent"],
                        observed_at=at,
                        resets_at=item["resets_at"],
                        source="codex",
                        note=note[:500],
                    )
                )
                added += 1
        session.commit()
    return added


def _save_status(store, status: dict[str, Any]) -> None:
    with store.session() as session:
        row = session.get(Meta, STATUS_KEY) or Meta(key=STATUS_KEY, value="")
        row.value = json.dumps(status, default=usage.iso)
        session.add(row)
        session.commit()


def status(store) -> dict[str, Any] | None:
    with store.session() as session:
        row = session.get(Meta, STATUS_KEY)
    if row is None:
        return None
    try:
        return json.loads(row.value)
    except ValueError:
        return None


def poll(store, note: str = "", force: bool = False) -> dict[str, Any]:
    """Ask Codex for current usage and save changed readings."""
    from aespa.services import codex_provider

    with _lock:
        at = now()
        result: dict[str, Any] = {"checked_at": at, "ok": False, "added": 0}
        try:
            plan_email = _plan_email()
            parsed = parse(
                asyncio.run(codex_provider.read_account_usage(_configured_path()))
            )
            same = (
                None
                if not plan_email or not parsed["email"]
                else plan_email.casefold() == parsed["email"].casefold()
            )
            result |= {
                "ok": True,
                "email": parsed["email"],
                "plan_type": parsed["plan_type"],
                "limit_id": parsed["limit_id"],
                "chatgpt_plan_email": plan_email,
                "same_account": same,
                "windows": parsed["windows"],
            }
            usage.sample(store, at)
            result["added"] = record(store, parsed, at, note, force)
            result["removed"] = usage.prune_readings(store)
        except Exception as exc:
            message = str(exc).strip() or type(exc).__name__
            result["error"] = message[:300]
        _save_status(store, result)
        return json.loads(json.dumps(result, default=usage.iso))
