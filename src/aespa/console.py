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
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TextIO


HTTP = "http"
ERRORS = "errors"
LLM = "llm"
AGENT = "agent"
TESTING = "testing"
SETTINGS = "settings"

_MODES = (AGENT, ERRORS, LLM, HTTP, TESTING, SETTINGS)
_MODE_KEYS = {
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
_PYTHON_EXECUTOR_IMAGE = "ledwardchow/aespa-python-executor:0.1"
_ANSI_RED = "\x1b[38;5;196m"
_ANSI_ORANGE = "\x1b[38;5;202m"
_ANSI_CORAL = "\x1b[38;5;203m"
_ANSI_DIM_RED = "\x1b[38;5;88m"
_ANSI_RESET = "\x1b[0m"
_ANSI_SGR = re.compile(r"\x1b\[[0-9;]*m")

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
    "                              A E S P A",
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
    "              A E S P A",
)


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

    def emit(self, record: logging.LogRecord) -> None:
        view = _record_view(record)
        if view is None:
            return
        try:
            with self._output_lock:
                if view == AGENT:
                    self._agent_message_seen = True
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
            if self.settings_section == "root":
                if key not in ("\r", "\n"):
                    return False
                self.settings_section = (
                    "server" if self.settings_selected == 0 else "database"
                )
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
                self.settings_selected = min(max(self.settings_selected + delta, 0), 1)
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
                if not _python_executor_image_present():
                    self.buffers[AGENT].append(
                        "Python executor image is not installed - run "
                        f"docker pull {_PYTHON_EXECUTOR_IMAGE}"
                    )
                self._ready_announced = True
            self._screen_active = True
            self.stream.write("\x1b[?1049h")
            self._redraw_locked()

    def stop_screen(self) -> None:
        with self._output_lock:
            if not self._screen_active:
                return
            self._screen_active = False
            self.stream.write("\x1b[?1049l")
            self.stream.flush()

    def refresh_for_resize(self) -> bool:
        """Redraw when the terminal dimensions changed since the last frame."""
        with self._output_lock:
            size = self._terminal_size()
            if not self._screen_active or size == self._screen_size:
                return False
            self._redraw_locked(size=size)
            return True

    def _redraw_locked(self, *, size: tuple[int, int] | None = None) -> None:
        width, height = size or self._terminal_size()
        width = max(20, width)
        height = max(5, height)
        self._screen_size = (width, height)
        body_height = height - 3
        content_width = width - 2
        body_lines = self._body_lines(content_width)
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

    def _body_lines(self, width: int) -> list[str]:
        if self.mode == SETTINGS:
            return self._settings_body_lines(width)
        if self.mode == LLM and self.llm_calls:
            return self._llm_body_lines(width)[0]
        if self.mode == TESTING and self.testing_calls:
            return self._testing_body_lines(width)[0]
        body_lines: list[str] = []
        if self.mode == AGENT and not self._agent_message_seen:
            body_lines.extend(_aespa_logo_lines(width))
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
        return [
            f"{'▶' if self.settings_selected == 0 else ' '} Server Settings",
            f"{'▶' if self.settings_selected == 1 else ' '} Database Operations",
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
                "run_label": f"{run_kind} run {run_id}" if run_id is not None else "no run",
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
        line_count = len(self._body_lines(content_width))
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
        if settings_section == "database":
            if editing:
                return "[Enter] Confirm  [Backspace] Delete  [Esc] Cancel"
            return "[↑/↓] Select  [Enter] Open  [Esc] Back"
        if settings_section == "root":
            return "[1-6] Views  [↑/↓] Select  [Enter] Open  [Ctrl+C] Stop"
        if editing:
            return "[0-9] Port  [Backspace] Delete  [Enter] Save  [Esc] Cancel"
        return "[Enter] Change port  [Esc] Back  [Ctrl+C] Stop"
    return "[1-6] Views  [↑/↓] Select  [Enter] Expand  [PgUp/PgDn] Page  [Ctrl+C] Stop"


def _listening_url(host: str, port: int) -> str:
    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"http://{display_host}:{port}"


def _aespa_logo_lines(width: int) -> list[str]:
    """Return a centered ANSI-color logo for the empty Agent screen."""
    if width < 46:
        art = _AESPA_LOGO_COMPACT
    else:
        art = _AESPA_LOGO

    art_width = max(len(line) for line in art)
    padding = " " * max(0, (width - art_width) // 2)
    lines: list[str] = []
    for line in art:
        if not line:
            lines.append("")
            continue
        lines.append(padding + _color_ascii_logo_line(line))
    return lines


def _color_ascii_logo_line(line: str) -> str:
    """Color density characters separately to retain the shaded ASCII effect."""
    density_colors = {
        ".": _ANSI_DIM_RED,
        "+": _ANSI_ORANGE,
        "o": _ANSI_RED,
        "s": _ANSI_CORAL,
    }
    if line.strip() == "A E S P A":
        return f"{_ANSI_CORAL}{line}{_ANSI_RESET}"

    rendered: list[str] = []
    active_color = ""
    for character in line:
        color = density_colors.get(character, _ANSI_RED if character != " " else "")
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


def _python_executor_image_present() -> bool:
    """Return whether the optional Python executor image is available locally."""
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", _PYTHON_EXECUTOR_IMAGE],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


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
        )
        self.replace_logging_handlers = replace_logging_handlers
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
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
        self._key_buffer = b""
        self._enable_immediate_keys()
        self.handler.start_screen()
        self._attached = True
        self._thread = threading.Thread(
            target=self._read_keys, name="aespa-console-input", daemon=True
        )
        self._thread.start()

    def detach(self) -> None:
        """Detach the terminal but continue buffering console records."""
        if not self._attached:
            return
        self._stop.set()
        self._restore_terminal()
        try:
            self.handler.stop_screen()
        finally:
            self._attached = False
            self._thread = None

    def stop(self) -> None:
        self.detach()
        if not self._capturing:
            return
        root = logging.getLogger()
        root.removeHandler(self.handler)
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
