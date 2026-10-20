from __future__ import annotations

import logging
import threading
import time

from aespa.extensions import SourceProviderField, get_extension_manager

from . import codex, models, scans, usage
from .router import build_router

log = logging.getLogger(__name__)

EXTENSION_ID = "aespa.chatgptplanusage"
SAMPLE_SECONDS = 15
DEFAULT_CODEX_MINUTES = 5
DEFAULT_SCAN_MINUTES = 2

SETTINGS = [
    SourceProviderField(
        key="codex_readings",
        label="Read usage from Codex",
        type="boolean",
        default=True,
        help=(
            "Check the plan's 5-hour and weekly usage with the Codex CLI. Codex must "
            "be signed in. ChatGPT plan provider usage counts only on the same account."
        ),
    ),
    SourceProviderField(
        key="codex_poll_minutes",
        label="Minutes between Codex checks",
        type="number",
        default=DEFAULT_CODEX_MINUTES,
        help="Each check starts Codex briefly. The lowest allowed value is 1.",
    ),
    SourceProviderField(
        key="scan_poll_minutes",
        label="Minutes between Codex checks during a scan",
        type="number",
        default=DEFAULT_SCAN_MINUTES,
        help=(
            "Used while a crawl or scan uses the ChatGPT plan or Codex CLI provider. "
            "Readings are also taken when such a scan starts and ends."
        ),
    ),
]


def _settings() -> dict:
    return get_extension_manager().get_settings(EXTENSION_ID)


def _minutes(settings: dict, key: str, default: float) -> float:
    value = settings.get(key, default)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        value = default
    return max(1.0, float(value))


def _codex_minutes(settings: dict) -> float | None:
    if not settings.get("codex_readings", True):
        return None
    return _minutes(settings, "codex_poll_minutes", DEFAULT_CODEX_MINUTES)


def _quietly(action, store) -> None:
    try:
        action(store)
    except Exception:
        log.debug("ChatGPT plan usage task failed", exc_info=True)


def _scan_note(started, ended) -> str:
    return "; ".join(
        [f"{scan.label} started" for scan in started]
        + [f"{scan.label} ended" for scan in ended]
    )


def codex_step(store, watcher, settings: dict, next_codex: float, now: float) -> float:
    """Take any Codex reading that is due and return when the next one is due."""
    minutes = _codex_minutes(settings)
    if minutes is None:
        return next_codex
    try:
        current = scans.active_plan_scans()
    except Exception:
        log.debug("Could not list active scans", exc_info=True)
        current = watcher.active
    started, ended = watcher.check(current)
    if started or ended:
        note = _scan_note(started, ended)
        _quietly(lambda target: codex.poll(target, note=note, force=True), store)
    elif now >= next_codex:
        _quietly(codex.poll, store)
    else:
        return next_codex
    if watcher.active:
        minutes = _minutes(settings, "scan_poll_minutes", DEFAULT_SCAN_MINUTES)
    return now + minutes * 60


def _sample_loop(store, stop: threading.Event) -> None:
    watcher = scans.ScanWatcher()
    next_codex = time.monotonic() + SAMPLE_SECONDS
    first = True
    while True:
        if get_extension_manager().data_stores.get(EXTENSION_ID) is not store:
            return
        _quietly(usage.sample, store)
        if not first:
            try:
                next_codex = codex_step(
                    store, watcher, _settings(), next_codex, time.monotonic()
                )
            except Exception:
                log.debug("ChatGPT plan usage check failed", exc_info=True)
        first = False
        if stop.wait(SAMPLE_SECONDS):
            return


class ChatGPTPlanUsageExtension:
    def register(self, registry) -> None:
        registry.register_settings_fields(SETTINGS)
        store = registry.data_store(models.metadata)
        _quietly(usage.prune_readings, store)
        registry.register_api_router(build_router(store))
        threading.Thread(
            target=_sample_loop,
            args=(store, threading.Event()),
            name="chatgpt-plan-usage-sampler",
            daemon=True,
        ).start()


def create_extension():
    return ChatGPTPlanUsageExtension()
