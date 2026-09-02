"""Interactive terminal logging for the AESPA CLI server."""

from __future__ import annotations

import json
import logging
import os
import select
import shutil
import sys
import textwrap
import threading
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TextIO


HTTP = "http"
ERRORS = "errors"
LLM = "llm"
AGENT = "agent"
TESTING = "testing"

_MODES = (AGENT, ERRORS, LLM, HTTP, TESTING)
_MODE_KEYS = {"1": AGENT, "2": ERRORS, "3": LLM, "4": HTTP, "5": TESTING}
_PAGE_UP = b"\x1b[5~"
_PAGE_DOWN = b"\x1b[6~"
_ARROW_UP = b"\x1b[A"
_ARROW_DOWN = b"\x1b[B"


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

    def __init__(self, stream: TextIO, *, max_records: int = 200) -> None:
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

    def emit(self, record: logging.LogRecord) -> None:
        view = _record_view(record)
        if view is None:
            return
        try:
            with self._output_lock:
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

    def select_previous_llm(self) -> None:
        self._move_llm_selection(-1)

    def select_next_llm(self) -> None:
        self._move_llm_selection(1)

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
                f"\x1b[{row};1H{line[:content_width]}"
                f"\x1b[{row};{width}H{scrollbar[index]}"
            )
        screen += f"\x1b[{height};1H\x1b[2K{_legend()[:width]}"
        self.stream.write(screen)
        self.stream.flush()

    def _terminal_size(self) -> tuple[int, int]:
        try:
            size = os.get_terminal_size(self.stream.fileno())
        except (AttributeError, OSError, ValueError):
            size = shutil.get_terminal_size(fallback=(120, 30))
        return max(20, int(size[0])), max(5, int(size[1]))

    def _body_lines(self, width: int) -> list[str]:
        if self.mode == LLM and self.llm_calls:
            return self._llm_body_lines(width)[0]
        if self.mode == TESTING and self.testing_calls:
            return self._testing_body_lines(width)[0]
        body_lines: list[str] = []
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
                f"{marker} {disclosure} #{call_id} {call['operation']} "
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
            call = {
                "call_id": call_id,
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


def _legend() -> str:
    return "[1-5] Views  [↑/↓] Select  [Enter] Expand  [PgUp/PgDn] Page  [Ctrl+C] Stop"


class InteractiveConsole:
    """Own the log handler and the background keyboard reader."""

    def __init__(
        self,
        *,
        input_stream: TextIO = sys.stdin,
        output_stream: TextIO = sys.stdout,
    ) -> None:
        self.input_stream = input_stream
        self.handler = InteractiveConsoleHandler(output_stream)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._terminal_state = None
        self._key_buffer = b""

    def start(self) -> None:
        self._configure_logging()
        self._enable_immediate_keys()
        self.handler.start_screen()
        self._thread = threading.Thread(
            target=self._read_keys, name="aespa-console-input", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._restore_terminal()
        self.handler.stop_screen()
        logging.getLogger().removeHandler(self.handler)

    def _configure_logging(self) -> None:
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        for existing in list(root.handlers):
            root.removeHandler(existing)
            existing.close()
        root.addHandler(self.handler)
        for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            logger = logging.getLogger(name)
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

    def _process_posix_keys(self, data: bytes) -> None:
        self._key_buffer += data
        sequences = {
            _PAGE_UP: self.handler.page_up,
            _PAGE_DOWN: self.handler.page_down,
            _ARROW_UP: self.handler.select_previous_llm,
            _ARROW_DOWN: self.handler.select_next_llm,
        }
        while self._key_buffer:
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
