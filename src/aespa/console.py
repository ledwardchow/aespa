"""Interactive terminal logging for the AESPA CLI server."""

from __future__ import annotations

import json
import logging
import os
import re
import select
import shutil
import socket
import subprocess
import sys
import textwrap
import threading
from collections import deque
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from aespa.console_logs import ConsoleLogStore

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TextIO


HTTP = "http"
ERRORS = "errors"
LLM = "llm"
AGENT = "agent"
TESTING = "testing"
SETTINGS = "settings"
LOGO = "logo"

_MODES = (AGENT, ERRORS, LLM, HTTP, TESTING, SETTINGS, LOGO)
_MODE_KEYS = {
    "0": LOGO,
    "1": AGENT,
    "2": ERRORS,
    "3": LLM,
    "4": HTTP,
    "5": TESTING,
    "6": SETTINGS,
}
_PAGE_UP = b"\x1b[5~"
_PAGE_DOWN = b"\x1b[6~"
_ARROW_UP = b"\x1b[A"
_ARROW_DOWN = b"\x1b[B"
_SGR_MOUSE_PREFIX = b"\x1b[<"
_LEGACY_MOUSE_PREFIX = b"\x1b[M"
_MOUSE_MODIFIER_MASK = 4 | 8 | 16
_MOUSE_WHEEL_UP = 64
_MOUSE_WHEEL_DOWN = 65
_PYTHON_EXECUTOR_IMAGE = "ledwardchow/aespa-python-executor:0.1"
_ANSI_RED = "\x1b[38;5;196m"
_ANSI_ORANGE = "\x1b[38;5;202m"
_ANSI_CORAL = "\x1b[38;5;203m"
_ANSI_DIM_RED = "\x1b[38;5;88m"
_ANSI_WHITE = "\x1b[38;5;255m"
_ANSI_RESET = "\x1b[0m"
_ANSI_SGR = re.compile(r"\x1b\[[0-9;]*m")
_ANSI_256_FOREGROUND = re.compile(r"\x1b\[38;5;(\d+)m")
_LOGO_ANIMATION_INTERVAL = 0.05
_LOGO_LOOP_DURATION = 1.5
_LOGO_PAUSE_DURATION = 1.0
_STARTUP_FADE_FRAMES = 4
_STARTUP_SIDE_HOLD = 0.5
_STARTUP_SIDE_FADE = 0.4
_STARTUP_INTERFACE_HOLD = 0.5
_STARTUP_WAVE_DURATION = 1.0
_LOGO_PULSE_RADIUS = 7.0
_LOGO_RADIAL_PULSE_DURATION = 0.65
_LOGO_ROW_ASPECT = 2.0
_LOGO_TRACE_RADIUS = 2.1
_LOGO_PULSE_GRADIENT = (
    (1.25, _ANSI_WHITE),
    (2.5, "\x1b[38;5;254m"),
    (4.0, "\x1b[38;5;252m"),
    (5.5, "\x1b[38;5;250m"),
    (_LOGO_PULSE_RADIUS, "\x1b[38;5;248m"),
)

_AESPA_LOGO = (
    "                     +ooooooooooooooooooooooooo+",
    "                    +sssssssssssssssssssssssssss+",
    "                   +sssooooooooooooooooooooooosss+",
    "                  +sss+         .ooo.         +sss+",
    "                 +sss+          .oso.          +sss+",
    "                +sss+    +o+    .oso.           +sss+",
    "               +sss+     osooooooosooooooooo+    +sss+",
    "              +sss+     +so+    +oso+     oso     +sss+",
    "             +sss+     .so     +ssoss+.   +os+     +sss+",
    "            +sss+     .oo.   .oss+.+sso+    oo.     +sss+",
    "           +sss+     .oo.   .osooso .oss+.  .oo.     +sss+",
    "          +sss+     .oo.   +osoosss. .+sso.  .oo.     +sss+",
    "         +sss+      os.  .+ssoosoos+   +oss+  .oo      +sss+",
    "        +sss+      +s+  .oss+oso.+so.   .+sso. +s+......+sss+",
    "  .+++++oss++++++++s+++++so+oso. .os+    .+os++++ssssssssssso+++++.",
    "  +sssssssssssssssssssssssssso.   +so.  +ossssssssssssssssssssssss+",
    "  .+++++++sso++++++++++++oso+.    .os+ +ssso++++++++++++oss+++++++.",
    "       .+sso+o+        +oso+       +soossooso+        +o+oss+.",
    "      .osso.oso       +oso+        .ssss+ +oso+       oso.osso.",
    "     .osso.+so+      +oso+          oso+   +oso+      +os+.osso.",
    "    +ossooosooooooooooso+           .+.     +osoooooooooosooosso+",
    "    ossssssssssssssssso+                     +ossssssssssssssssso",
)

_AESPA_LOGO_COMPACT = (
    "           .+++++++++++++.",
    "          .ossssssssssssso.",
    "          +so+++++++++++os+",
    "         +so..+. +s+ .+..os+",
    "        +ss. +sooosooos+ .ss+",
    "       +ss+ +s++ss+ss++s+ +ss+",
    "      .ss+ +s+osos+.oso+s+ +ss.",
    "     .os+ +s+ss+soo..+ss+s+.+so.",
    " .+++os+++s+so+s++s+  .os+ssssss+++.",
    " +sssssssssssss+ .oo..+ssssssssssss+",
    " .+++os++++++os+  +s++so++++++so+++.",
    "  .+ss++++++ss+.  .oos+ss++++++ss+.",
    "  +ssssssssso+     +s+ +osssssssss+",
)

# High-detail terminal trace derived from frontend/public/icon.png.  It keeps
# the raster mark's outer A, central flare, circuit branches, and heartbeat.
_AESPA_LOGO_LARGE = (
    "                                                o",
    "                                       +oooooooosoooooooo+",
    "                                      osssssssssssssssssss+",
    "                                     osso      +s       sss+",
    "                                    osso     +ossoo.     sss+",
    "                                   osso    +sssssssso    .sss.",
    "                                  osso...++sssssssssso++...sss.",
    "                                 +sso.++++ossssssssssso+++++sss.",
    "                                +sso       .sssssssss       .sss.",
    "                               +sso          +ossso+         .sss",
    "                              +sss    ..       +s             .sss",
    "                             +sss   .ssss+     os+             +sss",
    "                            .sss    +s++ss    osss+     .osso   +sso",
    "                           .sss.    ossoo    osssss+    so +s+   +sso",
    "                          .sss     osso     osso sss.   +ssss.    +sso",
    "                         .sss.    +sso     +sso   sss.    .sss     +sso",
    "                        .sss.    +sso     +sso     sss.    .sss     +sso",
    "                        sss.    +sso     +sso      .sss.    .sss     +sso",
    "                       sss.    +sso     +sso        .sss.    .sso     +sso",
    "                      sss.    +sso     +sso          .sss     +sso     osso",
    "                     sss+    +sss     +sso    .o      .sss     +ssso+   osso",
    "                    sss+    .sss     +sso     ss.      .sss     +ssssssoossso",
    "                   sss+    .sss     +sss     osso       .sss     +sso+ossssss+",
    "                  oss+    .sss      +++     +ssss.       .++.     +sso   .+oos+",
    "                 +oo+     ooo               ssssso                 +sso",
    "                                           oss.oss.                 osso",
    "      ossssssssssssssssssssssssssssssssssssss+  sso   .sssssssssssssssss+     osssssssssss+",
    "     .ooooooooooooooooosssoooooooooooooooooo+   oss.  sssooooooooooooooss+     ossooooooooo",
    "                      sss.                       sso oss+              oss+     sss.",
    "            osso     sss.                        ossosso                oss+     sss.",
    "           osso     sss.    .sssssssssssssso      sssss    sssssssso     oss+     sss.",
    "          +sso     sss.    .sssoooooooooooo+      osss.    ooooooosso     oss.    .sss.",
    "         +sso     oss+    .sss                     ss+            +sso     sss.    .sss.",
    "        +sso   .osss+    .sss.                     oo              +sso     sss+.   .sss",
    "       +sso   .so+os    .sss.                                       +sso    .sooso   .sss",
    "      +sso     ssoso   .sss.                                         +sso   +so+ss    .sss",
    "     +sss       ...    sss.                                           +sso   .oo+      +sss",
    "    +sss              sss.                                             osso             +sss",
    "   .ssso+++++++++++++sss.                                               osso+++++++++++++osso",
    "  .ssssssssssssssssssss+                                                 ossssssssssssssssssso",
    "   ...................                                                     ..................",
)

_AESPA_WAVE_PATH = ((2, 15), (29, 15), (34, 12), (38, 20), (43, 15), (66, 15))
_AESPA_WAVE_PATH_COMPACT = ((0, 9), (14, 9), (17, 7), (20, 12), (23, 9), (35, 9))
_AESPA_WAVE_PATH_LARGE = ((6, 27), (42, 27), (47, 20), (53, 34), (58, 27), (94, 27))


def _record_view(record: logging.LogRecord) -> str | None:
    if record.name == "aespa.agent.activity":
        return AGENT
    if record.name == "aespa.llm.traffic":
        return LLM
    if record.name == "aespa.testing.traffic":
        return TESTING
    if record.levelno >= logging.ERROR:
        return ERRORS
    if record.name == "uvicorn.access":
        return HTTP
    return None


class InteractiveConsoleHandler(logging.Handler):
    """Route log records into switchable, buffered terminal views."""

    def __init__(
        self,
        stream: TextIO,
        *,
        max_records: int = 200,
        port: int = 8000,
        host: str = "127.0.0.1",
        env_path: Path | None = None,
        on_port_change: Callable[[int], None] | None = None,
        allow_port_change: bool = True,
        terminal_size: tuple[int, int] | None = None,
        log_db_path: Path | None = None,
    ) -> None:
        super().__init__(level=logging.DEBUG)
        self.stream = stream
        self.mode = AGENT
        self.buffers = {mode: deque(maxlen=max_records) for mode in _MODES}
        self._output_lock = threading.RLock()
        self._screen_active = False
        self._screen_size: tuple[int, int] | None = None
        self.page_indices = {mode: 0 for mode in _MODES}
        self.follow_live = {mode: True for mode in _MODES}
        self.llm_calls: list[dict] = []
        self.llm_selected = -1
        self.llm_expanded: set[int] = set()
        self.testing_calls: list[dict] = []
        self.testing_selected = -1
        self.testing_expanded: set[int] = set()
        self._max_records = max_records
        self.runtime_port = port
        self.configured_port = port
        self.host = host
        self.env_path = env_path or Path(".env")
        self.on_port_change = on_port_change
        self.allow_port_change = allow_port_change
        self.fixed_terminal_size = terminal_size
        self.log_store = ConsoleLogStore(log_db_path or Path("logs.db"))
        self.settings_editing = False
        self.settings_replace_on_digit = False
        self.settings_value = str(port)
        self.settings_status = ""
        self.settings_section = "root"
        self.settings_selected = 0
        self.database_selected = 0
        self.database_action: str | None = None
        self.database_input = ""
        self._ready_announced = False
        self._agent_message_seen = False
        self._logo_animation_frame = 0
        self._startup_logo_active = False
        self._startup_logo_completed = False
        self._startup_fade_phase: str | None = None
        self._startup_fade_frame = 0
        self._finishing_logo_animation = False

    def emit(self, record: logging.LogRecord) -> None:
        view = _record_view(record)
        if view is None:
            return
        try:
            with self._output_lock:
                if view != TESTING:
                    self.log_store.append(record, view)
                if view == AGENT:
                    self._agent_message_seen = True
                    self._finishing_logo_animation = False
                if view == LLM and hasattr(record, "aespa_llm_call_id"):
                    self._store_llm_record(record)
                elif view == TESTING and hasattr(record, "aespa_testing_traffic_id"):
                    self._store_testing_record(record)
                else:
                    self.buffers[view].append(self._format_record(record, view))
                if self.mode == view and self._screen_active:
                    self._redraw_locked()
        except Exception:
            self.handleError(record)

    def switch(self, mode: str) -> None:
        if mode not in self.buffers:
            raise ValueError(f"Unknown console mode: {mode}")
        with self._output_lock:
            previous_mode = self.mode
            if self._startup_logo_active or self._startup_fade_phase is not None:
                self._startup_logo_active = False
                self._startup_logo_completed = True
                self._startup_fade_phase = None
                self._startup_fade_frame = 0
            self._finishing_logo_animation = False
            if previous_mode == LOGO and mode == AGENT and not self._agent_message_seen:
                cycle_frames = round(
                    (_LOGO_LOOP_DURATION + _LOGO_PAUSE_DURATION)
                    / _LOGO_ANIMATION_INTERVAL
                )
                active_frames = round(_LOGO_LOOP_DURATION / _LOGO_ANIMATION_INTERVAL)
                self._finishing_logo_animation = (
                    self._logo_animation_frame % cycle_frames < active_frames
                )
            self.mode = mode
            self._redraw_locked()

    def set_runtime_port(self, port: int) -> None:
        """Update the Settings view after the listener has restarted."""
        with self._output_lock:
            self.runtime_port = port
            self.configured_port = port
            self.settings_value = str(port)
            self.settings_status = f"AESPA is now listening on port {port}."
            if self._screen_active and self.mode == SETTINGS:
                self._redraw_locked()

    def handle_settings_key(self, key: str) -> bool:
        """Handle one key when the Settings view is active."""
        if self.mode != SETTINGS:
            return False
        with self._output_lock:
            if self.settings_section == "database":
                return self._handle_database_key(key)
            if self.settings_section == "logging":
                return self._handle_log_database_key(key)
            if self.settings_section == "root":
                if key not in ("\r", "\n"):
                    return False
                self.settings_section = ("server", "database", "logging")[
                    self.settings_selected
                ]
                self.settings_status = ""
                self._redraw_locked()
                return True
            if not self.settings_editing:
                if key == "\x1b":
                    self.settings_section = "root"
                    self.settings_status = ""
                    self._redraw_locked()
                    return True
                if key in ("\r", "\n"):
                    if not self.allow_port_change:
                        self.settings_status = (
                            "The desktop app selects its port automatically."
                        )
                        self._redraw_locked()
                        return True
                    self.settings_editing = True
                    self.settings_replace_on_digit = True
                    self.settings_value = str(self.configured_port)
                    self.settings_status = (
                        "Type a port number, then press Enter to apply."
                    )
                    self._redraw_locked()
                    return True
                return False

            if key.isdigit():
                if self.settings_replace_on_digit:
                    self.settings_value = ""
                    self.settings_replace_on_digit = False
                if len(self.settings_value) < 5:
                    self.settings_value += key
                self._redraw_locked()
                return True
            if key in ("\b", "\x7f"):
                self.settings_replace_on_digit = False
                self.settings_value = self.settings_value[:-1]
                self._redraw_locked()
                return True
            if key == "\x1b":
                self.settings_editing = False
                self.settings_replace_on_digit = False
                self.settings_value = str(self.configured_port)
                self.settings_status = "Change cancelled."
                self._redraw_locked()
                return True
            if key in ("\r", "\n"):
                self._save_port()
                self._redraw_locked()
                return True
            return True

    def _handle_log_database_key(self, key: str) -> bool:
        if key == "\x1b":
            self.settings_section = "root"
            self.settings_status = ""
            self._redraw_locked()
            return True
        if key not in ("\r", "\n"):
            return False
        enabled = not self.log_store.enabled
        if self.log_store.set_enabled(enabled):
            state = "enabled" if enabled else "disabled"
            self.settings_status = f"Console log database {state}."
        else:
            self.settings_status = (
                "Could not update the console log database: "
                f"{self.log_store.last_error}"
            )
        self._redraw_locked()
        return True

    def _handle_database_key(self, key: str) -> bool:
        if self.database_action is None:
            if key == "\x1b":
                self.settings_section = "root"
                self.settings_status = ""
                self._redraw_locked()
                return True
            if key not in ("\r", "\n"):
                return False
            action = ("backup", "clear", "reset")[self.database_selected]
            self.database_action = action
            self.settings_editing = True
            self.settings_status = ""
            self.database_input = (
                str(_default_database_backup_path()) if action == "backup" else ""
            )
            self._redraw_locked()
            return True

        if key == "\x1b":
            self.database_action = None
            self.database_input = ""
            self.settings_editing = False
            self.settings_status = "Action cancelled."
            self._redraw_locked()
            return True
        if key in ("\b", "\x7f"):
            self.database_input = self.database_input[:-1]
            self._redraw_locked()
            return True
        if key in ("\r", "\n"):
            self._run_database_action()
            return True
        if key.isprintable():
            self.database_input += key
            self._redraw_locked()
        return True

    def _run_database_action(self) -> None:
        from aespa.services import database_operations

        action = self.database_action
        confirmation = self.database_input
        if action == "clear" and confirmation != "CLEAR":
            self.settings_status = 'Confirmation did not match. Type "CLEAR" exactly.'
            self.database_input = ""
            self._redraw_locked()
            return
        if action == "reset" and confirmation != "RESET":
            self.settings_status = 'Confirmation did not match. Type "RESET" exactly.'
            self.database_input = ""
            self._redraw_locked()
            return

        self.settings_status = {
            "backup": "Creating database backup...",
            "clear": "Clearing scans...",
            "reset": "Resetting database...",
        }[action]
        self._redraw_locked()
        try:
            if action == "backup":
                destination = database_operations.backup_database(Path(confirmation))
                self.settings_status = f"Database backup saved to {destination}"
            elif action == "clear":
                count = database_operations.clear_scans()
                suffix = "run" if count == 1 else "runs"
                self.settings_status = f"Cleared {count} scan {suffix}."
            else:
                database_operations.reset_database()
                self.settings_status = "Database reset complete."
        except Exception as exc:
            self.settings_status = f"Database operation failed: {exc}"
        finally:
            self.database_action = None
            self.database_input = ""
            self.settings_editing = False
            self._redraw_locked()

    def _save_port(self) -> None:
        try:
            port = int(self.settings_value)
        except ValueError:
            self.settings_status = "Enter a port between 1 and 65535."
            return
        if not 1 <= port <= 65535:
            self.settings_status = "Enter a port between 1 and 65535."
            return
        if port == self.runtime_port:
            self.settings_editing = False
            self.configured_port = port
            self.settings_status = f"AESPA is already listening on port {port}."
            return
        if not _port_available(self.host, port):
            self.settings_status = (
                f"Port {port} is already in use. Choose another port."
            )
            return
        try:
            _write_port_setting(self.env_path, port)
        except OSError as exc:
            self.settings_status = f"Could not save the port: {exc}"
            return
        self.settings_editing = False
        self.configured_port = port
        self.settings_status = f"Saved port {port}. Restarting the AESPA listener…"
        if self.on_port_change is not None:
            self.on_port_change(port)

    def select_previous_llm(self) -> None:
        if self.mode == SETTINGS and not self.settings_editing:
            self._move_settings_selection(-1)
            return
        self._move_llm_selection(-1)

    def select_next_llm(self) -> None:
        if self.mode == SETTINGS and not self.settings_editing:
            self._move_settings_selection(1)
            return
        self._move_llm_selection(1)

    def _move_settings_selection(self, delta: int) -> None:
        with self._output_lock:
            if self.settings_section == "database":
                self.database_selected = min(max(self.database_selected + delta, 0), 2)
            elif self.settings_section == "root":
                self.settings_selected = min(max(self.settings_selected + delta, 0), 2)
            self._redraw_locked()

    def toggle_selected_llm(self) -> None:
        with self._output_lock:
            calls, selected, expanded = self._structured_state()
            if not calls or selected < 0:
                return
            item_id = self._structured_item_id(calls[selected])
            if item_id in expanded:
                expanded.remove(item_id)
            else:
                expanded.add(item_id)
            self.follow_live[self.mode] = False
            self._show_selected_structured_page()
            self._redraw_locked()

    def page_up(self) -> None:
        """Move one page toward older records in the selected view."""
        with self._output_lock:
            width, height = self._terminal_size()
            width = max(20, width)
            height = max(5, height)
            page_count = self._page_count(height - 3, width - 2)
            current = (
                page_count - 1
                if self.follow_live[self.mode]
                else min(self.page_indices[self.mode], page_count - 1)
            )
            self.page_indices[self.mode] = max(0, current - 1)
            self.follow_live[self.mode] = page_count == 1
            self._redraw_locked()

    def page_down(self) -> None:
        """Move one page toward the newest records in the selected view."""
        with self._output_lock:
            width, height = self._terminal_size()
            width = max(20, width)
            height = max(5, height)
            page_count = self._page_count(height - 3, width - 2)
            newest = page_count - 1
            current = (
                newest
                if self.follow_live[self.mode]
                else min(self.page_indices[self.mode], newest)
            )
            self.page_indices[self.mode] = min(current + 1, newest)
            self.follow_live[self.mode] = self.page_indices[self.mode] == newest
            self._redraw_locked()

    def start_screen(self) -> None:
        with self._output_lock:
            if not self._ready_announced:
                self.buffers[AGENT].append(
                    f"Ready - listening on {_listening_url(self.host, self.runtime_port)}"
                )
                python_executor_status = _python_executor_runtime_status()
                if python_executor_status == "docker_not_installed":
                    self.buffers[AGENT].append(
                        "Python sandbox is unavailable - Docker is not installed"
                    )
                elif python_executor_status == "docker_unavailable":
                    self.buffers[AGENT].append(
                        "Python sandbox is unavailable - Docker is installed, but its "
                        "service is not running or cannot be reached. Start Docker and "
                        "try again"
                    )
                elif python_executor_status == "image_missing":
                    self.buffers[AGENT].append(
                        "Python executor image is not installed - run "
                        f"docker pull {_PYTHON_EXECUTOR_IMAGE}"
                    )
                self._ready_announced = True
            if not self._screen_active:
                self._logo_animation_frame = 0
                self._startup_logo_active = (
                    self.mode == AGENT and not self._agent_message_seen
                )
                self._startup_logo_completed = (
                    self.mode != AGENT or self._agent_message_seen
                )
                self._startup_fade_phase = None
                self._startup_fade_frame = 0
            self._screen_active = True
            self.stream.write("\x1b[?1049h\x1b[?1000h\x1b[?1006h\x1b[?25l")
            self._redraw_locked()

    def stop_screen(self) -> None:
        with self._output_lock:
            if not self._screen_active:
                return
            self._screen_active = False
            self.stream.write("\x1b[?1006l\x1b[?1000l\x1b[?1049l\x1b[?25h")
            self.stream.flush()

    def refresh_for_resize(self) -> bool:
        """Redraw when the terminal dimensions changed since the last frame."""
        with self._output_lock:
            size = self._terminal_size()
            if not self._screen_active or size == self._screen_size:
                return False
            self._redraw_locked(size=size)
            return True

    def _startup_duration(self) -> float:
        width, height = self._terminal_size()
        if width >= 100 and height >= len(_AESPA_LOGO_LARGE):
            art, path = _AESPA_LOGO_LARGE, _AESPA_WAVE_PATH_LARGE
        elif width < 69 or height < len(_AESPA_LOGO):
            art, path = _AESPA_LOGO_COMPACT, _AESPA_WAVE_PATH_COMPACT
        else:
            art, path = _AESPA_LOGO, _AESPA_WAVE_PATH
        return _startup_wave_timing(width, art, path)[-1] + _STARTUP_INTERFACE_HOLD

    def advance_logo_animation(self) -> bool:
        """Advance the idle Agent-view pulse and redraw when it is visible."""
        with self._output_lock:
            if (
                not self._screen_active
                or self.mode not in (AGENT, LOGO)
                or (
                    self.mode == AGENT
                    and not self._startup_logo_active
                    and self._startup_fade_phase != "console"
                    and not self._finishing_logo_animation
                    and (self._agent_message_seen or self._startup_logo_completed)
                )
            ):
                return False
            if self.mode == LOGO:
                self._logo_animation_frame += 1
            elif self._startup_logo_active:
                self._logo_animation_frame += 1
                if (
                    self._logo_animation_frame * _LOGO_ANIMATION_INTERVAL
                    >= self._startup_duration()
                ):
                    self._startup_logo_active = False
                    # Park on the idle frame, not the next pulse's first frame.
                    self._logo_animation_frame = round(
                        _LOGO_LOOP_DURATION / _LOGO_ANIMATION_INTERVAL
                    )
                    self._startup_fade_phase = "console"
                    self._startup_fade_frame = 0
            elif self._startup_fade_phase == "console":
                self._startup_fade_frame += 1
                if self._startup_fade_frame >= _STARTUP_FADE_FRAMES:
                    self._startup_fade_phase = None
                    self._startup_logo_completed = True
            elif self._finishing_logo_animation:
                self._logo_animation_frame += 1
                cycle_frames = round(
                    (_LOGO_LOOP_DURATION + _LOGO_PAUSE_DURATION)
                    / _LOGO_ANIMATION_INTERVAL
                )
                active_frames = round(_LOGO_LOOP_DURATION / _LOGO_ANIMATION_INTERVAL)
                if self._logo_animation_frame % cycle_frames >= active_frames:
                    self._finishing_logo_animation = False
            self._redraw_locked()
            return True

    def _redraw_locked(self, *, size: tuple[int, int] | None = None) -> None:
        width, height = size or self._terminal_size()
        width = max(20, width)
        height = max(5, height)
        self._screen_size = (width, height)
        if self.mode == LOGO or self._startup_logo_active:
            self._redraw_logo_locked(width, height)
            return
        if self.mode == AGENT and (
            not self._agent_message_seen or self._startup_fade_phase == "console"
        ):
            self._redraw_agent_logo_locked(width, height)
            return
        body_height = height - 3
        content_width = width - 2
        body_lines = self._body_lines(content_width, body_height)
        page_count = max(1, (len(body_lines) + body_height - 1) // body_height)
        if self.follow_live[self.mode]:
            page = page_count - 1
        else:
            page = min(self.page_indices[self.mode], page_count - 1)
        self.page_indices[self.mode] = page
        end = min(len(body_lines), (page + 1) * body_height)
        start = page * body_height
        visible = body_lines[start:end]
        structured_calls, structured_selected, _ = self._structured_state()
        title = _title(
            self.mode,
            page + 1,
            page_count,
            selected=structured_selected + 1 if structured_calls else 0,
            item_count=len(structured_calls),
            width=width,
        )
        scrollbar = _scrollbar(body_height, page, page_count)
        screen = f"\x1b[2J\x1b[H{title[:width]}\x1b[2;1H{'─' * width}"
        for index in range(body_height):
            row = index + 3
            line = visible[index] if index < len(visible) else ""
            screen += (
                f"\x1b[{row};1H{_truncate_terminal_line(line, content_width)}"
                f"\x1b[{row};{width}H{scrollbar[index]}"
            )
        screen += (
            f"\x1b[{height};1H\x1b[2K"
            f"{_legend(self.mode, self.settings_editing, self.settings_section)[:width]}"
        )
        if self._startup_fade_phase == "console":
            screen = _fade_terminal_frame(
                screen, self._startup_fade_frame / _STARTUP_FADE_FRAMES
            )
        self.stream.write(screen)
        self.stream.flush()

    def _redraw_logo_locked(self, width: int, height: int) -> None:
        """Render the hidden logo-only view without tabs, chrome, or legend."""
        large = width >= 100 and height >= len(_AESPA_LOGO_LARGE)
        compact = not large and (width < 69 or height < len(_AESPA_LOGO))
        logo_lines = _aespa_logo_lines(
            width,
            animation_frame=self._logo_animation_frame,
            compact=compact,
            large=large,
            reveal=self._startup_logo_active,
        )
        first_row = max(1, ((height - len(logo_lines)) // 2) + 1)
        screen = "\x1b[2J\x1b[H"
        for index, line in enumerate(logo_lines):
            row = first_row + index
            if row > height:
                break
            screen += f"\x1b[{row};1H{_truncate_terminal_line(line, width)}"
        self.stream.write(screen)
        self.stream.flush()

    def _redraw_agent_logo_locked(self, width: int, height: int) -> None:
        """Render normal console chrome around a logo that stays screen-centred."""
        large = width >= 100 and height >= len(_AESPA_LOGO_LARGE)
        compact = not large and (width < 69 or height < len(_AESPA_LOGO))
        logo_lines = _aespa_logo_lines(
            width,
            animation_frame=self._logo_animation_frame,
            compact=compact,
            large=large,
        )
        first_row = max(1, ((height - len(logo_lines)) // 2) + 1)
        title = _title(AGENT, 1, 1, width=width)
        screen = f"\x1b[2J\x1b[H{title[:width]}\x1b[2;1H{'─' * width}"
        record_row = max(3, first_row + len(logo_lines))
        for record in self.buffers[AGENT]:
            for line in record.splitlines() or [""]:
                if record_row >= height:
                    break
                rendered_line = _truncate_terminal_line(line, width)
                visible_width = len(_ANSI_SGR.sub("", rendered_line))
                column = max(1, ((width - visible_width) // 2) + 1)
                screen += f"\x1b[{record_row};{column}H{rendered_line}"
                record_row += 1
        screen += f"\x1b[{height};1H\x1b[2K{_legend(AGENT, False, 'root')[:width]}"
        if self._startup_fade_phase == "console":
            screen = _fade_terminal_frame(
                screen, self._startup_fade_frame / _STARTUP_FADE_FRAMES
            )
        for index, line in enumerate(logo_lines):
            row = first_row + index
            if 3 <= row < height:
                screen += f"\x1b[{row};1H{_truncate_terminal_line(line, width)}"
        self.stream.write(screen)
        self.stream.flush()

    def _terminal_size(self) -> tuple[int, int]:
        if self.fixed_terminal_size is not None:
            return self.fixed_terminal_size
        try:
            size = os.get_terminal_size(self.stream.fileno())
        except (AttributeError, OSError, ValueError):
            size = shutil.get_terminal_size(fallback=(120, 30))
        return max(20, int(size[0])), max(5, int(size[1]))

    def _body_lines(self, width: int, available_height: int | None = None) -> list[str]:
        large = width >= 100 and bool(
            available_height and available_height >= len(_AESPA_LOGO_LARGE) + 2
        )
        if self.mode == LOGO:
            return _aespa_logo_lines(
                width,
                animation_frame=self._logo_animation_frame,
                large=large,
            )
        if self.mode == SETTINGS:
            return self._settings_body_lines(width)
        if self.mode == LLM and self.llm_calls:
            return self._llm_body_lines(width)[0]
        if self.mode == TESTING and self.testing_calls:
            return self._testing_body_lines(width)[0]
        body_lines: list[str] = []
        if self.mode == AGENT and not self._agent_message_seen:
            body_lines.extend(
                _aespa_logo_lines(
                    width,
                    animation_frame=self._logo_animation_frame,
                    large=large,
                )
            )
            body_lines.append("")
        for record in self.buffers[self.mode]:
            for line in record.replace("\r", "").replace("\x1b", "\\x1b").split("\n"):
                wrapped = textwrap.wrap(
                    line.expandtabs(4),
                    width=width,
                    replace_whitespace=False,
                    drop_whitespace=False,
                )
                body_lines.extend(wrapped or [""])
        return body_lines

    def _settings_body_lines(self, width: int) -> list[str]:
        if self.settings_section == "database":
            return self._database_settings_body_lines(width)
        if self.settings_section == "server":
            return self._server_settings_body_lines(width)
        if self.settings_section == "logging":
            return self._log_database_settings_body_lines(width)
        return [
            f"{'▶' if self.settings_selected == 0 else ' '} Server Settings",
            f"{'▶' if self.settings_selected == 1 else ' '} Database Operations",
            f"{'▶' if self.settings_selected == 2 else ' '} Console Log Database",
        ]

    def _server_settings_body_lines(self, width: int) -> list[str]:
        value = (
            self.settings_value if self.settings_editing else str(self.configured_port)
        )
        cursor = "▌" if self.settings_editing else ""
        guidance = (
            "Press Enter to edit the port. AESPA restarts its listener after saving."
            if self.allow_port_change
            else "The desktop app selects an available local port automatically."
        )
        lines = [
            "Server Settings",
            "",
            f"  Listening address   http://{self.host}:{self.runtime_port}",
            f"  Port                {value}{cursor}",
            "",
            guidance,
        ]
        if self.allow_port_change:
            lines.append(
                f"The setting is saved in {self.env_path} for future launches."
            )
        if os.environ.get("AESPA_PORT"):
            lines.extend(
                [
                    "",
                    "Note: the AESPA_PORT environment variable may override the saved value",
                    "on the next launch.",
                ]
            )
        if self.settings_status:
            lines.extend(["", self.settings_status])
        wrapped: list[str] = []
        for line in lines:
            wrapped.extend(_wrap_console_line(line, width))
        return wrapped

    def _database_settings_body_lines(self, width: int) -> list[str]:
        lines = [
            "Database Operations",
            "",
            f"{'▶' if self.database_selected == 0 else ' '} Backup database",
            "      Save a complete copy of the SQLite database.",
            "",
            f"{'▶' if self.database_selected == 1 else ' '} Clear scans",
            "      Remove all web, API, SAST, and campaign runs. Keep targets,",
            "      LLM connections, and settings.",
            "",
            f"{'▶' if self.database_selected == 2 else ' '} Reset database",
            "      Delete all data, including targets, LLM connections, and settings.",
        ]
        if self.database_action == "backup":
            lines.extend(
                [
                    "",
                    "Backup file path:",
                    f"  {self.database_input}▌",
                    "Press Enter to save the backup or Esc to cancel.",
                ]
            )
        elif self.database_action in ("clear", "reset"):
            required = self.database_action.upper()
            lines.extend(
                [
                    "",
                    f'Type "{required}" to confirm:',
                    f"  {self.database_input}▌",
                    "Press Esc to cancel.",
                ]
            )
        else:
            lines.extend(["", "Press Esc to return to Settings."])
        if self.settings_status:
            lines.extend(["", self.settings_status])
        wrapped: list[str] = []
        for line in lines:
            wrapped.extend(_wrap_console_line(line, width))
        return wrapped

    def _log_database_settings_body_lines(self, width: int) -> list[str]:
        enabled = self.log_store.enabled
        lines = [
            "Console Log Database",
            "",
            f"  Status              {'Enabled' if enabled else 'Disabled'}",
            f"  Database            {self.log_store.path}",
            "",
            "Stores new Agent, Errors, LLM, and HTTP console entries.",
            "Testing Traffic is excluded because it is already stored by the scanner.",
            "Complete LLM requests and responses are stored without truncation.",
            "",
            "Warning: prompts and responses may contain credentials, cookies,",
            "tokens, source code, or other sensitive data.",
            "",
            f"Press Enter to {'disable' if enabled else 'enable'} logging.",
            "Press Esc to return to Settings.",
        ]
        if self.log_store.last_error:
            lines.extend(["", f"Last write error: {self.log_store.last_error}"])
        if self.settings_status:
            lines.extend(["", self.settings_status])
        wrapped: list[str] = []
        for line in lines:
            wrapped.extend(_wrap_console_line(line, width))
        return wrapped

    def _llm_body_lines(self, width: int) -> tuple[list[str], list[int]]:
        lines: list[str] = []
        header_positions: list[int] = []
        for index, call in enumerate(self.llm_calls):
            header_positions.append(len(lines))
            call_id = int(call["call_id"])
            expanded = call_id in self.llm_expanded
            marker = "▶" if index == self.llm_selected else " "
            disclosure = "▾" if expanded else "▸"
            status = _llm_call_status(call)
            header = (
                f"{marker} {disclosure} {call['created_at']} {call['run_label']} "
                f"#{call_id} {call['operation']} "
                f"[{call['kind']}] {status}"
            )
            lines.extend(_wrap_console_line(header, width))
            if not expanded:
                continue
            lines.extend(_wrap_console_line(f"    {call['context']}", width))
            for direction in ("REQUEST", "RESPONSE", "FAILED"):
                payload = call["payloads"].get(direction)
                if payload is None:
                    continue
                lines.extend(_wrap_console_line(f"    --- {direction} ---", width))
                for payload_line in payload.split("\n"):
                    lines.extend(_wrap_console_line(f"    {payload_line}", width))
            lines.append("")
        return lines, header_positions

    def _testing_body_lines(self, width: int) -> tuple[list[str], list[int]]:
        lines: list[str] = []
        header_positions: list[int] = []
        for index, call in enumerate(self.testing_calls):
            header_positions.append(len(lines))
            traffic_id = int(call["traffic_id"])
            expanded = traffic_id in self.testing_expanded
            marker = "▶" if index == self.testing_selected else " "
            disclosure = "▾" if expanded else "▸"
            status = call["status"] if call["status"] is not None else "FAILED"
            duration = (
                f" {call['duration_ms']}ms" if call["duration_ms"] is not None else ""
            )
            header = (
                f"{marker} {disclosure} #{traffic_id} {call['method']} {call['url']} "
                f"[{status}{duration}]"
            )
            lines.extend(_wrap_console_line(header, width))
            if not expanded:
                continue
            context = f"{call['run_kind']} run {call['run_id']} · {call['source']}"
            if call.get("session_label"):
                context += f" · session {call['session_label']}"
            if call.get("username"):
                context += f" · user {call['username']}"
            lines.extend(_wrap_console_line(f"    {context}", width))
            for direction, headers_key, body_key in (
                ("REQUEST", "request_headers", "request_body"),
                ("RESPONSE", "response_headers", "response_body"),
            ):
                lines.extend(_wrap_console_line(f"    --- {direction} ---", width))
                headers = json.dumps(call[headers_key], indent=2, sort_keys=True)
                for payload_line in headers.split("\n"):
                    lines.extend(_wrap_console_line(f"    {payload_line}", width))
                body = call.get(body_key)
                if body:
                    for payload_line in str(body).split("\n"):
                        lines.extend(_wrap_console_line(f"    {payload_line}", width))
            lines.append("")
        return lines, header_positions

    def _store_llm_record(self, record: logging.LogRecord) -> None:
        call_id = int(record.aespa_llm_call_id)
        call = next(
            (item for item in self.llm_calls if item["call_id"] == call_id), None
        )
        if call is None:
            run_id = getattr(record, "aespa_llm_run_id", None)
            run_kind = str(getattr(record, "aespa_llm_run_kind", "web"))
            call = {
                "call_id": call_id,
                "created_at": datetime.fromtimestamp(record.created).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "run_label": f"{run_kind} run {run_id}"
                if run_id is not None
                else "no run",
                "operation": str(record.aespa_llm_operation),
                "kind": str(record.aespa_llm_kind),
                "context": str(record.aespa_llm_context),
                "payloads": {},
            }
            self.llm_calls.append(call)
            if len(self.llm_calls) > self._max_records:
                removed = self.llm_calls.pop(0)
                self.llm_expanded.discard(int(removed["call_id"]))
                self.llm_selected = max(-1, self.llm_selected - 1)
        call["payloads"][str(record.aespa_llm_direction)] = str(
            record.aespa_llm_payload
        )
        if self.follow_live[LLM] or self.llm_selected < 0:
            self.llm_selected = len(self.llm_calls) - 1

    def _store_testing_record(self, record: logging.LogRecord) -> None:
        call = {
            "traffic_id": int(record.aespa_testing_traffic_id),
            "run_kind": str(record.aespa_testing_run_kind),
            "run_id": int(record.aespa_testing_run_id),
            "source": str(record.aespa_testing_source),
            "method": str(record.aespa_testing_method),
            "url": str(record.aespa_testing_url),
            "status": record.aespa_testing_status,
            "duration_ms": record.aespa_testing_duration_ms,
            "username": record.aespa_testing_username,
            "session_label": record.aespa_testing_session_label,
            "request_headers": record.aespa_testing_request_headers,
            "request_body": record.aespa_testing_request_body,
            "response_headers": record.aespa_testing_response_headers,
            "response_body": record.aespa_testing_response_body,
        }
        self.testing_calls.append(call)
        if len(self.testing_calls) > self._max_records:
            removed = self.testing_calls.pop(0)
            self.testing_expanded.discard(int(removed["traffic_id"]))
            self.testing_selected = max(-1, self.testing_selected - 1)
        if self.follow_live[TESTING] or self.testing_selected < 0:
            self.testing_selected = len(self.testing_calls) - 1

    def _move_llm_selection(self, delta: int) -> None:
        with self._output_lock:
            calls, selected, _ = self._structured_state()
            if not calls:
                return
            selected = min(max(selected + delta, 0), len(calls) - 1)
            if self.mode == LLM:
                self.llm_selected = selected
            else:
                self.testing_selected = selected
            self.follow_live[self.mode] = False
            self._show_selected_structured_page()
            self._redraw_locked()

    def _structured_state(self) -> tuple[list[dict], int, set[int]]:
        if self.mode == LLM:
            return self.llm_calls, self.llm_selected, self.llm_expanded
        if self.mode == TESTING:
            return self.testing_calls, self.testing_selected, self.testing_expanded
        return [], -1, set()

    @staticmethod
    def _structured_item_id(item: dict) -> int:
        return int(item.get("call_id", item.get("traffic_id")))

    def _show_selected_structured_page(self) -> None:
        width, height = self._terminal_size()
        body_height = height - 3
        if self.mode == LLM:
            _, positions = self._llm_body_lines(width - 2)
            selected = self.llm_selected
        elif self.mode == TESTING:
            _, positions = self._testing_body_lines(width - 2)
            selected = self.testing_selected
        else:
            return
        if positions and selected >= 0:
            self.page_indices[self.mode] = positions[selected] // body_height

    def _page_count(self, body_height: int, content_width: int) -> int:
        line_count = len(self._body_lines(content_width, body_height))
        return max(1, (line_count + body_height - 1) // body_height)

    def _format_record(self, record: logging.LogRecord, view: str) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        if view == HTTP and isinstance(record.args, tuple) and len(record.args) >= 5:
            client, method, path, http_version, status = record.args[:5]
            return (
                f"{timestamp}  {status}  {method} {path}  HTTP/{http_version}  {client}"
            )

        message = record.getMessage()
        if view in (LLM, AGENT):
            return f"{timestamp}  {message}"

        rendered = f"{timestamp}  {record.levelname}  {record.name}: {message}"
        if record.exc_info:
            formatter = logging.Formatter()
            rendered += "\n" + formatter.formatException(record.exc_info)
        return rendered


def _title(
    mode: str,
    page: int,
    page_count: int,
    *,
    selected: int = 0,
    item_count: int = 0,
    width: int = 120,
) -> str:
    tab_specs = (
        ("1", AGENT, "Agent", "A"),
        ("2", ERRORS, "Err", "E"),
        ("3", LLM, "LLM", "L"),
        ("4", HTTP, "HTTP", "H"),
        ("5", TESTING, "Testing Traffic", "T"),
        ("6", SETTINGS, "Settings", "S"),
    )
    if width < 100:
        tabs = [
            f"[{key} {label}]" if selected_mode == mode else f"{key}{short_label}"
            for key, selected_mode, label, short_label in tab_specs
        ]
        tab_separator = " "
    else:
        tabs = [
            f"[{key} {label}]" if selected_mode == mode else f" {key} {label} "
            for key, selected_mode, label, _ in tab_specs
        ]
        tab_separator = "  "
    scrollback = _scrollback_percent(page - 1, page_count)
    item_label = "Call" if mode == LLM else "Request"
    selection = (
        f"  |  {item_label} {selected}/{item_count}"
        if mode in (LLM, TESTING) and item_count
        else ""
    )
    return (
        f"AESPA  {tab_separator.join(tabs)}  |  Page {page}/{page_count}"
        f"{selection}  |  Scrollback {scrollback}%"
    )


def _wrap_console_line(line: str, width: int) -> list[str]:
    wrapped = textwrap.wrap(
        line.expandtabs(4),
        width=width,
        replace_whitespace=False,
        drop_whitespace=False,
    )
    return wrapped or [""]


def _llm_call_status(call: dict) -> str:
    payloads = call["payloads"]
    if "FAILED" in payloads:
        return "FAILED"
    if "RESPONSE" in payloads:
        return "COMPLETE"
    return "PENDING"


def _scrollback_percent(page: int, page_count: int) -> int:
    if page_count <= 1:
        return 0
    return round(((page_count - 1 - page) / (page_count - 1)) * 100)


def _scrollbar(body_height: int, page: int, page_count: int) -> list[str]:
    """Build a scrollbar with oldest content at the top and live output at bottom."""
    if page_count <= 1:
        return ["█"] * body_height
    thumb_height = max(1, round(body_height / page_count))
    travel = body_height - thumb_height
    position_from_oldest = page / (page_count - 1)
    thumb_start = round(travel * position_from_oldest)
    return [
        "█" if thumb_start <= row < thumb_start + thumb_height else "│"
        for row in range(body_height)
    ]


def _legend(
    mode: str = AGENT, editing: bool = False, settings_section: str = "root"
) -> str:
    if mode == SETTINGS:
        if settings_section == "logging":
            return "[Enter] Enable/Disable  [Esc] Back  [Ctrl+C] Quit"
        if settings_section == "database":
            if editing:
                return "[Enter] Confirm  [Backspace] Delete  [Esc] Cancel"
            return "[↑/↓] Select  [Enter] Open  [Esc] Back"
        if settings_section == "root":
            return "[1-6] Views  [↑/↓] Select  [Enter] Open  [Ctrl+C] Quit"
        if editing:
            return "[0-9] Port  [Backspace] Delete  [Enter] Save  [Esc] Cancel"
        return "[Enter] Change port  [Esc] Back  [Ctrl+C] Quit"
    return (
        "[1-6] Views  [↑/↓] Select  [Enter] Expand  "
        "[Wheel/PgUp/PgDn] Scroll  [Ctrl+C] Quit"
    )


def _listening_url(host: str, port: int) -> str:
    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"http://{display_host}:{port}"


def _aespa_logo_lines(
    width: int,
    *,
    animation_frame: int = 0,
    compact: bool | None = None,
    large: bool = False,
    reveal: bool = False,
) -> list[str]:
    """Return a centered ANSI-color logo for the empty Agent screen."""
    if compact is None:
        compact = width < 46 and not large
    if large:
        art = _AESPA_LOGO_LARGE
        wave_path = _AESPA_WAVE_PATH_LARGE
    elif compact:
        art = _AESPA_LOGO_COMPACT
        wave_path = _AESPA_WAVE_PATH_COMPACT
    else:
        art = _AESPA_LOGO
        wave_path = _AESPA_WAVE_PATH

    art_width = max(len(line) for line in art)
    padding = " " * max(0, (width - art_width) // 2)
    trace_progress, trace_length = _wave_trace_progress(art, wave_path)
    pulse_span = trace_length + (_LOGO_PULSE_RADIUS * 2)
    cycle_duration = _LOGO_LOOP_DURATION + _LOGO_PAUSE_DURATION
    elapsed = animation_frame * _LOGO_ANIMATION_INTERVAL
    if not reveal:
        elapsed %= cycle_duration
    speed, entry_duration, wave_duration, exit_start, fade_end = _startup_wave_timing(
        width, art, wave_path
    )
    if not reveal:
        entry_duration, wave_duration = 0.0, _STARTUP_WAVE_DURATION
    wave_elapsed = elapsed - entry_duration
    pulse_position = (
        wave_elapsed / wave_duration * pulse_span - _LOGO_PULSE_RADIUS
        if wave_elapsed < wave_duration
        else None
    )
    radial_trigger_progress = _wave_progress_at_vertex(wave_path, 2)
    radial_origin = _wave_visual_center(wave_path)
    radial_trigger = (
        radial_trigger_progress + _LOGO_PULSE_RADIUS
    ) / pulse_span * wave_duration + entry_duration
    radial_elapsed = elapsed - radial_trigger
    radial_radius = (
        _radial_pulse_radius(art, radial_origin, radial_elapsed)
        if 0 <= radial_elapsed < _LOGO_RADIAL_PULSE_DURATION
        else None
    )
    revealed_radius = (
        _radial_pulse_radius(art, radial_origin, radial_elapsed)
        if radial_elapsed >= 0
        else -1.0
    )
    radial_speed = (
        _radial_pulse_radius(art, radial_origin, _LOGO_RADIAL_PULSE_DURATION)
        / _LOGO_RADIAL_PULSE_DURATION
    )
    lines: list[str] = []
    for row, line in enumerate(art):
        if not line:
            lines.append("")
            continue
        pulse_colors = {
            column: color
            for (trace_row, column), progress in trace_progress.items()
            if trace_row == row
            and pulse_position is not None
            and (color := _pulse_gradient_color(abs(progress - pulse_position)))
        }
        if radial_radius is not None:
            scaled_row = row * _LOGO_ROW_ASPECT
            for column, character in enumerate(line):
                if character == " ":
                    continue
                distance = (
                    (column - radial_origin[0]) ** 2
                    + (scaled_row - radial_origin[1]) ** 2
                ) ** 0.5
                radial_color = _pulse_gradient_color(abs(distance - radial_radius))
                if radial_color is not None:
                    pulse_colors[column] = _brighter_pulse_color(
                        pulse_colors.get(column), radial_color
                    )
        visible = []
        if reveal:
            pulse_colors = {}
        for column, character in enumerate(line):
            progress = trace_progress.get((row, column))
            if progress is not None:
                shown = pulse_position is None or progress <= pulse_position
                struck_at = (
                    progress + _LOGO_PULSE_RADIUS
                ) / pulse_span * wave_duration + entry_duration
            else:
                distance = (
                    (column - radial_origin[0]) ** 2
                    + (row * _LOGO_ROW_ASPECT - radial_origin[1]) ** 2
                ) ** 0.5
                shown = distance <= revealed_radius
                struck_at = radial_trigger + distance / radial_speed
            visible.append(character if shown or not reveal else " ")
            if shown and character != " ":
                # A crisp white strike leaves a warm afterglow as it settles.
                age = elapsed - struck_at
                if age < 0.10:
                    pulse_colors[column] = _ANSI_WHITE
                elif age < 0.20:
                    pulse_colors[column] = "\x1b[38;5;217m"
                elif age < 0.32:
                    pulse_colors[column] = _ANSI_CORAL
        line = "".join(visible)
        sample_column = wave_path[0][0] + 4
        side_glyph = art[row][sample_column] if sample_column < len(art[row]) else " "
        if (
            reveal
            and abs(row - wave_path[0][1]) <= 1
            and side_glyph != " "
            and 0 < elapsed < fade_end
        ):
            # Extend only the baseline outside the artwork, preserving logo glyphs.
            original = art[row]
            left = len(padding) + len(original) - len(original.lstrip())
            right = len(padding) + len(original.rstrip())
            full_line = list((padding + line).ljust(width))
            colors = {
                column + len(padding): color for column, color in pulse_colors.items()
            }
            brightness = min(
                1.0,
                max(
                    0.0,
                    (fade_end - elapsed) / _STARTUP_SIDE_FADE,
                ),
            )
            for column in range(width):
                if column < left:
                    arrival = column / speed
                elif column >= right:
                    arrival = (
                        exit_start + (column - len(padding) - wave_path[-1][0]) / speed
                    )
                else:
                    continue
                if elapsed < arrival:
                    continue
                full_line[column] = side_glyph
                base_color = {".": 88, "+": 202, "o": 196, "s": 203}.get(
                    side_glyph, 196
                )
                rgb = _xterm_color_rgb(255 if elapsed - arrival < 0.10 else base_color)
                red, green, blue = (round(channel * brightness) for channel in rgb)
                colors[column] = f"\x1b[38;2;{red};{green};{blue}m"
            lines.append(
                _color_ascii_logo_line("".join(full_line), pulse_colors=colors)
            )
            continue
        lines.append(
            padding
            + _color_ascii_logo_line(
                line,
                pulse_colors=pulse_colors,
            )
        )
    return lines


def _startup_wave_timing(
    width: int, art: tuple[str, ...], path: tuple[tuple[int, int], ...]
) -> tuple[float, float, float, float, float]:
    """Cross the terminal in one second at a shared side-line and wave speed."""
    _, trace_length = _wave_trace_progress(art, path)
    padding = max(0, (width - max(map(len, art))) // 2)
    exit_distance = max(0, width - 1 - padding - path[-1][0])
    distance = padding + path[0][0] + trace_length + exit_distance
    speed = distance / _STARTUP_WAVE_DURATION
    entry = (padding + path[0][0] - _LOGO_PULSE_RADIUS) / speed
    duration = (trace_length + 2 * _LOGO_PULSE_RADIUS) / speed
    exit_start = (padding + path[0][0] + trace_length) / speed
    exit_end = _STARTUP_WAVE_DURATION
    fade_end = exit_end + _STARTUP_SIDE_HOLD + _STARTUP_SIDE_FADE
    return speed, entry, duration, exit_start, fade_end


def _wave_visual_center(path: tuple[tuple[int, int], ...]) -> tuple[float, float]:
    """Return the display-scaled centre of the heartbeat path bounds."""
    columns = [column for column, _ in path]
    rows = [row for _, row in path]
    return (
        (min(columns) + max(columns)) / 2,
        ((min(rows) + max(rows)) / 2) * _LOGO_ROW_ASPECT,
    )


def _wave_progress_at_vertex(
    path: tuple[tuple[int, int], ...], vertex_index: int
) -> float:
    """Return the display-scaled path distance to one heartbeat vertex."""
    progress = 0.0
    for (start_x, start_y), (end_x, end_y) in zip(
        path[:vertex_index], path[1 : vertex_index + 1]
    ):
        progress += (
            (end_x - start_x) ** 2 + ((end_y - start_y) * _LOGO_ROW_ASPECT) ** 2
        ) ** 0.5
    return progress


def _radial_pulse_radius(
    art: tuple[str, ...], center: tuple[float, float], elapsed: float
) -> float:
    """Expand the radial pulse far enough to clear every visible logo glyph."""
    center_x, center_y = center
    furthest_distance = max(
        ((column - center_x) ** 2 + ((row * _LOGO_ROW_ASPECT) - center_y) ** 2) ** 0.5
        for row, line in enumerate(art)
        for column, character in enumerate(line)
        if character != " "
    )
    return (elapsed / _LOGO_RADIAL_PULSE_DURATION) * (
        furthest_distance + _LOGO_PULSE_RADIUS
    )


def _brighter_pulse_color(current: str | None, candidate: str) -> str:
    """Keep the brighter color where the travelling and radial pulses overlap."""
    if current is None:
        return candidate
    colors = [color for _, color in _LOGO_PULSE_GRADIENT]
    return min((current, candidate), key=colors.index)


@lru_cache(maxsize=3)
def _wave_trace_progress(
    art: tuple[str, ...], path: tuple[tuple[int, int], ...]
) -> tuple[dict[tuple[int, int], float], float]:
    """Map visible glyphs near the heartbeat polyline to distance along its path."""
    segments: list[tuple[float, float, float, float, float, float]] = []
    elapsed = 0.0
    for (start_x, start_y), (end_x, end_y) in zip(path, path[1:]):
        scaled_start_y = start_y * _LOGO_ROW_ASPECT
        scaled_end_y = end_y * _LOGO_ROW_ASPECT
        delta_x = end_x - start_x
        delta_y = scaled_end_y - scaled_start_y
        length = (delta_x**2 + delta_y**2) ** 0.5
        segments.append((start_x, scaled_start_y, delta_x, delta_y, length, elapsed))
        elapsed += length

    progress: dict[tuple[int, int], float] = {}
    for row, line in enumerate(art):
        scaled_row = row * _LOGO_ROW_ASPECT
        for column, character in enumerate(line):
            if character == " ":
                continue
            nearest_distance = float("inf")
            nearest_progress = 0.0
            for start_x, start_y, delta_x, delta_y, length, segment_start in segments:
                projection = (
                    (column - start_x) * delta_x + (scaled_row - start_y) * delta_y
                ) / (length**2)
                projection = min(1.0, max(0.0, projection))
                projected_x = start_x + projection * delta_x
                projected_y = start_y + projection * delta_y
                distance = (
                    (column - projected_x) ** 2 + (scaled_row - projected_y) ** 2
                ) ** 0.5
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_progress = segment_start + projection * length
            if nearest_distance <= _LOGO_TRACE_RADIUS:
                progress[(row, column)] = nearest_progress
    return progress, elapsed


def _pulse_gradient_color(distance: float) -> str | None:
    for edge, color in _LOGO_PULSE_GRADIENT:
        if distance <= edge:
            return color
    return None


def _color_ascii_logo_line(
    line: str, *, pulse_colors: dict[int, str] | None = None
) -> str:
    """Color density characters separately to retain the shaded ASCII effect."""
    density_colors = {
        ".": _ANSI_DIM_RED,
        "+": _ANSI_ORANGE,
        "o": _ANSI_RED,
        "s": _ANSI_CORAL,
    }
    rendered: list[str] = []
    active_color = ""
    for column, character in enumerate(line):
        color = (pulse_colors or {}).get(
            column,
            density_colors.get(character, _ANSI_RED if character != " " else ""),
        )
        if color != active_color:
            if active_color:
                rendered.append(_ANSI_RESET)
            if color:
                rendered.append(color)
            active_color = color
        rendered.append(character)
    if active_color:
        rendered.append(_ANSI_RESET)
    return "".join(rendered)


def _truncate_terminal_line(value: str, width: int) -> str:
    """Crop a line by visible characters without cutting ANSI color sequences."""
    result: list[str] = []
    visible = 0
    position = 0
    for match in _ANSI_SGR.finditer(value):
        text = value[position : match.start()]
        remaining = width - visible
        if remaining <= 0:
            break
        result.append(text[:remaining])
        visible += min(len(text), remaining)
        if visible < width or match.start() == position:
            result.append(match.group())
        position = match.end()
    if visible < width:
        result.append(value[position : position + width - visible])
    rendered = "".join(result)
    if "\x1b[" in rendered and not rendered.endswith(_ANSI_RESET):
        rendered += _ANSI_RESET
    return rendered


def _fade_terminal_frame(value: str, brightness: float) -> str:
    """Dim an ANSI frame while preserving its cursor-positioning sequences."""
    brightness = min(1.0, max(0.0, brightness))
    default_level = round(255 * brightness)
    default_color = f"\x1b[38;2;{default_level};{default_level};{default_level}m"

    def fade_color(match: re.Match[str]) -> str:
        red, green, blue = _xterm_color_rgb(int(match.group(1)))
        return (
            f"\x1b[38;2;{round(red * brightness)};"
            f"{round(green * brightness)};{round(blue * brightness)}m"
        )

    faded = _ANSI_256_FOREGROUND.sub(fade_color, value)
    faded = faded.replace(_ANSI_RESET, _ANSI_RESET + default_color)
    return default_color + faded + _ANSI_RESET


def _xterm_color_rgb(index: int) -> tuple[int, int, int]:
    """Convert one xterm 256-color index to RGB for startup fading."""
    system_colors = (
        (0, 0, 0),
        (128, 0, 0),
        (0, 128, 0),
        (128, 128, 0),
        (0, 0, 128),
        (128, 0, 128),
        (0, 128, 128),
        (192, 192, 192),
        (128, 128, 128),
        (255, 0, 0),
        (0, 255, 0),
        (255, 255, 0),
        (0, 0, 255),
        (255, 0, 255),
        (0, 255, 255),
        (255, 255, 255),
    )
    if index < 16:
        return system_colors[index]
    if index < 232:
        cube = index - 16
        levels = (0, 95, 135, 175, 215, 255)
        return (
            levels[cube // 36],
            levels[(cube % 36) // 6],
            levels[cube % 6],
        )
    gray = 8 + ((index - 232) * 10)
    return gray, gray, gray


def _default_database_backup_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path.home() / f"aespa-backup-{timestamp}.db"


def _port_available(host: str, port: int) -> bool:
    """Return whether a TCP port can be bound before stopping the live server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        try:
            listener.bind((host, port))
        except OSError:
            return False
    return True


def _python_executor_runtime_status() -> str:
    """Return the availability state of Docker and the optional executor image."""
    if shutil.which("docker") is None:
        return "docker_not_installed"
    try:
        info = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
        if info.returncode != 0:
            return "docker_unavailable"
        image = subprocess.run(
            ["docker", "image", "inspect", _PYTHON_EXECUTOR_IMAGE],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "docker_unavailable"
    return "ready" if image.returncode == 0 else "image_missing"


def _write_port_setting(path: Path, port: int) -> None:
    """Persist AESPA_PORT while preserving unrelated .env settings."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    replacement = f"AESPA_PORT={port}"
    pattern = re.compile(r"^\s*(?:export\s+)?AESPA_PORT\s*=.*$", re.MULTILINE)
    if pattern.search(existing):
        updated = pattern.sub(replacement, existing)
    else:
        separator = "" if not existing or existing.endswith(("\n", "\r")) else "\n"
        updated = f"{existing}{separator}{replacement}\n"
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        temporary.write_text(updated, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class InteractiveConsole:
    """Own the log handler and the background keyboard reader."""

    def __init__(
        self,
        *,
        input_stream: TextIO = sys.stdin,
        output_stream: TextIO = sys.stdout,
        port: int = 8000,
        host: str = "127.0.0.1",
        env_path: Path | None = None,
        on_port_change: Callable[[int], None] | None = None,
        allow_port_change: bool = True,
        replace_logging_handlers: bool = True,
        terminal_size: tuple[int, int] | None = None,
        log_db_path: Path | None = None,
    ) -> None:
        self.input_stream = input_stream
        self.handler = InteractiveConsoleHandler(
            output_stream,
            port=port,
            host=host,
            env_path=env_path,
            on_port_change=on_port_change,
            allow_port_change=allow_port_change,
            terminal_size=terminal_size,
            log_db_path=log_db_path,
        )
        self.replace_logging_handlers = replace_logging_handlers
        self._stop = threading.Event()
        self._logo_animation_stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._animation_thread: threading.Thread | None = None
        self._terminal_state = None
        self._key_buffer = b""
        self._previous_root_level: int | None = None
        self._logger_states: dict[str, tuple[list[logging.Handler], bool]] = {}
        self._capturing = False
        self._attached = False

    def start(self) -> None:
        self.start_capture()
        self.attach(
            input_stream=self.input_stream,
            output_stream=self.handler.stream,
            terminal_size=self.handler.fixed_terminal_size,
        )

    def start_capture(self) -> None:
        """Capture console records without requiring a visible terminal."""
        if self._capturing:
            return
        self._configure_logging()
        self._capturing = True

    def attach(
        self,
        *,
        input_stream: TextIO,
        output_stream: TextIO,
        terminal_size: tuple[int, int] | None = None,
    ) -> None:
        """Attach a terminal while retaining all previously captured state."""
        if self._attached:
            raise RuntimeError("The AESPA console already has an attached terminal")
        self.start_capture()
        self.input_stream = input_stream
        self.handler.stream = output_stream
        self.handler.fixed_terminal_size = terminal_size
        self._stop.clear()
        self._logo_animation_stop.clear()
        self._key_buffer = b""
        self._enable_immediate_keys()
        self.handler.start_screen()
        self._attached = True
        self._thread = threading.Thread(
            target=self._read_keys, name="aespa-console-input", daemon=True
        )
        self._thread.start()
        self._animation_thread = threading.Thread(
            target=self._animate_logo, name="aespa-console-logo", daemon=True
        )
        self._animation_thread.start()

    def detach(self) -> None:
        """Detach the terminal but continue buffering console records."""
        if not self._attached:
            return
        self._stop.set()
        self._logo_animation_stop.set()
        self._restore_terminal()
        try:
            self.handler.stop_screen()
        finally:
            animation_thread = self._animation_thread
            if (
                animation_thread is not None
                and animation_thread is not threading.current_thread()
            ):
                animation_thread.join(timeout=_LOGO_ANIMATION_INTERVAL * 2)
            self._attached = False
            self._thread = None
            self._animation_thread = None

    def stop(self) -> None:
        self.detach()
        if not self._capturing:
            return
        root = logging.getLogger()
        root.removeHandler(self.handler)
        self.handler.log_store.close()
        if not self.replace_logging_handlers:
            if self._previous_root_level is not None:
                root.setLevel(self._previous_root_level)
            for name, (handlers, propagate) in self._logger_states.items():
                logger = logging.getLogger(name)
                logger.handlers[:] = handlers
                logger.propagate = propagate
            self._logger_states.clear()
        self._capturing = False

    def wait(self) -> None:
        """Wait until the console input stream closes."""
        if self._thread is not None:
            self._thread.join()

    def _configure_logging(self) -> None:
        root = logging.getLogger()
        self._previous_root_level = root.level
        root.setLevel(logging.INFO)
        if self.replace_logging_handlers:
            for existing in list(root.handlers):
                root.removeHandler(existing)
                existing.close()
        root.addHandler(self.handler)
        for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            logger = logging.getLogger(name)
            if not self.replace_logging_handlers:
                self._logger_states[name] = (list(logger.handlers), logger.propagate)
            logger.handlers.clear()
            logger.propagate = True
        logging.getLogger("uvicorn.access").setLevel(logging.INFO)
        logging.getLogger("aespa.llm.traffic").setLevel(logging.INFO)
        logging.getLogger("aespa.agent.activity").setLevel(logging.INFO)
        logging.getLogger("aespa.testing.traffic").setLevel(logging.INFO)

    def _enable_immediate_keys(self) -> None:
        if os.name == "nt":
            return
        try:
            import termios
            import tty

            fd = self.input_stream.fileno()
            self._terminal_state = (fd, termios.tcgetattr(fd))
            tty.setcbreak(fd)
        except (AttributeError, OSError, termios.error):
            self._terminal_state = None

    def _restore_terminal(self) -> None:
        if self._terminal_state is None:
            return
        import termios

        fd, state = self._terminal_state
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, state)
        except (OSError, termios.error):
            pass
        self._terminal_state = None

    def _read_keys(self) -> None:
        if not self.input_stream.isatty():
            self._read_stream_keys()
            return
        if os.name == "nt":
            self._read_windows_keys()
            return
        try:
            fd = self.input_stream.fileno()
            while not self._stop.is_set():
                readable, _, _ = select.select([fd], [], [], 0.2)
                if readable:
                    self._process_posix_keys(os.read(fd, 32))
                self.handler.refresh_for_resize()
        except (AttributeError, OSError):
            return

    def _animate_logo(self) -> None:
        """Drive the idle logo independently of keyboard and resize events."""
        while not self._logo_animation_stop.wait(_LOGO_ANIMATION_INTERVAL):
            self.handler.advance_logo_animation()

    def _read_stream_keys(self) -> None:
        """Read ANSI key bytes from a redirected stream or console bridge."""
        try:
            while not self._stop.is_set():
                data = self.input_stream.read(32)
                if not data:
                    return
                if isinstance(data, str):
                    data = data.encode()
                self._process_posix_keys(data)
        except (AttributeError, OSError, ValueError):
            return

    def _process_posix_keys(self, data: bytes) -> None:
        self._key_buffer += data
        sequences = {
            _PAGE_UP: self.handler.page_up,
            _PAGE_DOWN: self.handler.page_down,
            _ARROW_UP: self.handler.select_previous_llm,
            _ARROW_DOWN: self.handler.select_next_llm,
        }
        while self._key_buffer:
            mouse_result = self._consume_mouse_sequence()
            if mouse_result is None:
                return
            if mouse_result:
                continue
            if self.handler.mode == SETTINGS and self.handler.settings_editing:
                key = self._key_buffer[:1].decode(errors="ignore")
                self._key_buffer = self._key_buffer[1:]
                self.handler.handle_settings_key(key)
                continue
            matched = next(
                (
                    sequence
                    for sequence in sequences
                    if self._key_buffer.startswith(sequence)
                ),
                None,
            )
            if matched is not None:
                self._key_buffer = self._key_buffer[len(matched) :]
                sequences[matched]()
                continue
            if any(sequence.startswith(self._key_buffer) for sequence in sequences):
                return
            key = self._key_buffer[:1].decode(errors="ignore")
            self._key_buffer = self._key_buffer[1:]
            if self.handler.handle_settings_key(key):
                continue
            if key in _MODE_KEYS:
                self.handler.switch(_MODE_KEYS[key])
            elif key in ("\r", "\n"):
                self.handler.toggle_selected_llm()

    def _consume_mouse_sequence(self) -> bool | None:
        """Consume one terminal mouse report, waiting when a report is incomplete."""
        if self._key_buffer.startswith(_SGR_MOUSE_PREFIX):
            match = re.match(rb"\x1b\[<(\d+);\d+;\d+([Mm])", self._key_buffer)
            if match is None:
                if len(self._key_buffer) <= 64 and not self._key_buffer.endswith(
                    (b"M", b"m")
                ):
                    return None
                self._key_buffer = self._key_buffer[1:]
                return True
            self._key_buffer = self._key_buffer[match.end() :]
            if match.group(2) == b"M":
                self._handle_mouse_button(int(match.group(1)))
            return True

        if self._key_buffer.startswith(_LEGACY_MOUSE_PREFIX):
            if len(self._key_buffer) < 6:
                return None
            button = self._key_buffer[3] - 32
            self._key_buffer = self._key_buffer[6:]
            self._handle_mouse_button(button)
            return True

        if _SGR_MOUSE_PREFIX.startswith(
            self._key_buffer
        ) or _LEGACY_MOUSE_PREFIX.startswith(self._key_buffer):
            return None
        return False

    def _handle_mouse_button(self, button: int) -> None:
        button &= ~_MOUSE_MODIFIER_MASK
        if button == _MOUSE_WHEEL_UP:
            self.handler.page_up()
        elif button == _MOUSE_WHEEL_DOWN:
            self.handler.page_down()

    def _read_windows_keys(self) -> None:
        import msvcrt
        import time

        while not self._stop.is_set():
            if msvcrt.kbhit():
                key = msvcrt.getwch()
                if key in ("\x00", "\xe0"):
                    special = msvcrt.getwch()
                    if special == "I":
                        self.handler.page_up()
                    elif special == "Q":
                        self.handler.page_down()
                    elif special == "H":
                        self.handler.select_previous_llm()
                    elif special == "P":
                        self.handler.select_next_llm()
                elif self.handler.handle_settings_key(key):
                    continue
                elif key in _MODE_KEYS:
                    self.handler.switch(_MODE_KEYS[key])
                elif key == "\r":
                    self.handler.toggle_selected_llm()
            else:
                time.sleep(0.05)
            self.handler.refresh_for_resize()


def interactive_console_available() -> bool:
    """Return whether stdin and stdout support an interactive terminal UI."""
    return bool(sys.stdin.isatty() and sys.stdout.isatty())
