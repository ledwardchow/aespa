from __future__ import annotations

import asyncio
import io
import logging
import math
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from types import SimpleNamespace

from aespa.console import (
    _AESPA_LOGO,
    _AESPA_LOGO_COMPACT,
    _AESPA_LOGO_LARGE,
    _AESPA_WAVE_PATH,
    _AESPA_WAVE_PATH_COMPACT,
    _AESPA_WAVE_PATH_LARGE,
    _ANSI_SGR,
    AGENT,
    ERRORS,
    HTTP,
    LLM,
    LOGO,
    SETTINGS,
    TESTING,
    InteractiveConsole,
    InteractiveConsoleHandler,
    _aespa_logo_lines,
    _legend,
    _python_executor_runtime_status,
    _startup_wave_timing,
    _wave_visual_center,
    _write_port_setting,
)


def _record(name: str, level: int, message: str, args=()) -> logging.LogRecord:
    return logging.LogRecord(name, level, __file__, 1, message, args, None)


def _llm_record(
    call_id: int,
    direction: str,
    payload: str,
    *,
    operation: str = "scanner.thinking_scan",
    run_id: int | None = 7,
    run_kind: str = "web",
) -> logging.LogRecord:
    record = _record("aespa.llm.traffic", logging.INFO, "structured LLM traffic")
    record.aespa_llm_call_id = call_id
    record.aespa_llm_operation = operation
    record.aespa_llm_kind = "tools"
    record.aespa_llm_direction = direction
    record.aespa_llm_context = "openai/test-model - web run 7"
    record.aespa_llm_payload = payload
    record.aespa_llm_run_id = run_id
    record.aespa_llm_run_kind = run_kind
    record.created = datetime(2026, 9, 5, 18, 34, 46).timestamp()
    return record


def _testing_record(
    traffic_id: int,
    method: str,
    url: str,
    status: int | None,
) -> logging.LogRecord:
    record = _record("aespa.testing.traffic", logging.INFO, "structured test traffic")
    record.aespa_testing_traffic_id = traffic_id
    record.aespa_testing_run_kind = "web"
    record.aespa_testing_run_id = 7
    record.aespa_testing_source = "httpx"
    record.aespa_testing_method = method
    record.aespa_testing_url = url
    record.aespa_testing_status = status
    record.aespa_testing_duration_ms = 42
    record.aespa_testing_username = "alice"
    record.aespa_testing_session_label = "alice-session"
    record.aespa_testing_request_headers = {"content-type": "application/json"}
    record.aespa_testing_request_body = '{"payload":"test"}'
    record.aespa_testing_response_headers = {"content-type": "application/json"}
    record.aespa_testing_response_body = '{"ok":true}'
    return record


def test_console_routes_records_to_separate_views() -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)

    handler.emit(
        _record(
            "uvicorn.access",
            logging.INFO,
            '%s - "%s %s HTTP/%s" %d',
            ("127.0.0.1:1234", "GET", "/api/health", "1.1", 200),
        )
    )
    handler.emit(_record("aespa.service", logging.ERROR, "scan failed"))
    handler.emit(_record("aespa.llm.traffic", logging.INFO, "REQUEST model\nprompt"))
    handler.emit(
        _record("aespa.agent.activity", logging.INFO, "web run 7 ACTIVE Scanner")
    )
    handler.emit(_record("aespa.testing.traffic", logging.INFO, "GET /target"))
    handler.emit(_record("aespa.service", logging.WARNING, "ignored warning"))

    assert "GET /api/health" in handler.buffers[HTTP][0]
    assert "scan failed" in handler.buffers[ERRORS][0]
    assert "prompt" in handler.buffers[LLM][0]
    assert "Scanner" in handler.buffers[AGENT][0]
    assert "GET /target" in handler.buffers[TESTING][0]
    assert all("ignored warning" not in item for item in handler.buffers.values())


def test_switch_clears_screen_and_replays_selected_buffer() -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    handler.emit(_record("aespa.service", logging.ERROR, "visible error"))

    handler.start_screen()
    handler.switch(ERRORS)

    rendered = output.getvalue()
    assert "\x1b[2J\x1b[H" in rendered
    assert "[2 Err]" in rendered
    assert "visible error" in rendered


def test_agent_is_initial_view_and_number_keys_switch_all_views() -> None:
    output = io.StringIO()
    console = InteractiveConsole(input_stream=io.StringIO(), output_stream=output)

    assert console.handler.mode == AGENT
    console.handler.start_screen()
    splash = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "+ooooooooooooooooooooooooo+" not in _ANSI_SGR.sub("", splash)
    assert "[1 Agent]" not in splash
    logo_position = re.search(r"\x1b\[(\d+);1H", splash)
    assert logo_position is not None
    for _ in range(math.ceil(console.handler._startup_duration() / 0.05)):
        assert console.handler.advance_logo_animation() is True
    fading_interface = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "[1 Agent]" in fading_interface
    assert "+ooooooooooooooooooooooooo+" in _ANSI_SGR.sub("", fading_interface)
    assert logo_position.group() in fading_interface
    for _ in range(4):
        assert console.handler.advance_logo_animation() is True
    assert console.handler.advance_logo_animation() is False
    assert "Ready - listening on http://127.0.0.1:8000" in output.getvalue()
    ready_position = re.search(
        r"\x1b\[(\d+);(\d+)HReady - listening on http://127\.0\.0\.1:8000",
        output.getvalue(),
    )
    assert ready_position is not None
    assert int(ready_position.group(2)) > 1
    assert output.getvalue().index("[1 Agent]") < output.getvalue().index(" 4 HTTP ")

    console._process_posix_keys(b"4")
    assert console.handler.mode == HTTP
    assert "[4 HTTP]" in output.getvalue()

    console._process_posix_keys(b"1")
    assert console.handler.mode == AGENT

    console._process_posix_keys(b"5")
    assert console.handler.mode == TESTING
    assert "[5 Testing Traffic]" in output.getvalue()

    console._process_posix_keys(b"6")
    assert console.handler.mode == SETTINGS
    assert "[6 Settings]" in output.getvalue()

    console._process_posix_keys(b"0")
    assert console.handler.mode == LOGO
    logo_frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "+ooooooooooooooooooooooooo+" in _ANSI_SGR.sub("", logo_frame)
    assert "A E S P A" not in logo_frame
    assert "[1 Agent]" not in logo_frame
    assert "[1-6] Views" not in logo_frame

    console._process_posix_keys(b"1")
    assert console.handler.mode == AGENT


def test_startup_logo_pulses_once_then_opens_agent_view(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output, terminal_size=(100, 35))
    monkeypatch.setattr(
        "aespa.console._python_executor_runtime_status", lambda: "ready"
    )

    handler.start_screen()

    initial_frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert not re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", initial_frame).strip()
    assert "\x1b[38;5;196m" not in initial_frame
    assert "Ready - listening" not in initial_frame
    assert "[1 Agent]" not in initial_frame

    handler.emit(_record("aespa.agent.activity", logging.INFO, "Scanner started"))
    for _ in range(math.ceil(handler._startup_duration() / 0.05) - 1):
        assert handler.advance_logo_animation() is True
    pulsing_frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "+ooooooooooooooooooooooooo+" in _ANSI_SGR.sub("", pulsing_frame)
    assert "[1 Agent]" not in pulsing_frame

    assert handler.advance_logo_animation() is True
    fading_interface = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "\x1b[38;2;0;0;0m" in output.getvalue()
    assert "+ooooooooooooooooooooooooo+" in _ANSI_SGR.sub("", fading_interface)
    assert "\x1b[38;5;196m" in fading_interface
    for _ in range(4):
        assert handler.advance_logo_animation() is True
    agent_frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "+ooooooooooooooooooooooooo+" not in _ANSI_SGR.sub("", agent_frame)
    assert "Scanner started" in agent_frame
    assert "[1 Agent]" in agent_frame
    assert handler.advance_logo_animation() is False


def test_returning_from_logo_view_finishes_active_pulse_in_agent_view(
    monkeypatch,
) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output, terminal_size=(100, 35))
    monkeypatch.setattr(
        "aespa.console._python_executor_runtime_status", lambda: "ready"
    )
    handler.start_screen()
    handler.switch(LOGO)
    for _ in range(10):
        assert handler.advance_logo_animation() is True

    handler.switch(AGENT)
    switched_frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "[1 Agent]" in switched_frame
    assert "+ooooooooooooooooooooooooo+" in _ANSI_SGR.sub("", switched_frame)

    for _ in range(20):
        assert handler.advance_logo_animation() is True
    assert handler.advance_logo_animation() is False
    assert handler._logo_animation_frame == 30


def test_agent_logo_pulse_moves_left_to_right_across_waveform() -> None:
    first_frame = _aespa_logo_lines(98, animation_frame=3)
    second_frame = _aespa_logo_lines(98, animation_frame=7)
    peak_frame = _aespa_logo_lines(98, animation_frame=12)
    trough_frame = _aespa_logo_lines(98, animation_frame=17)
    compact_frame = _aespa_logo_lines(40, animation_frame=12)

    def pulse_cells(lines: list[str]) -> list[tuple[int, int, int]]:
        cells: list[tuple[int, int, int]] = []
        for row, line in enumerate(lines):
            for match in re.finditer(
                r"\x1b\[38;5;(248|250|252|254|255)m([^\x1b]+)", line
            ):
                start = len(_ANSI_SGR.sub("", line[: match.start()]))
                cells.extend(
                    (int(match.group(1)), start + offset, row)
                    for offset, character in enumerate(match.group(2))
                    if character != " "
                )
        return cells

    first_cells = pulse_cells(first_frame)
    second_cells = pulse_cells(second_frame)
    assert max(column for _, column, _ in second_cells) > max(
        column for _, column, _ in first_cells
    )
    assert {color for color, _, _ in first_cells} == {248, 250, 252, 254, 255}

    assert min(row for _, _, row in pulse_cells(peak_frame)) <= 11
    assert max(row for _, _, row in pulse_cells(trough_frame)) >= 20
    assert min(row for _, _, row in pulse_cells(compact_frame)) < 8
    for paused_frame in (30, 40, 49):
        assert pulse_cells(_aespa_logo_lines(98, animation_frame=paused_frame)) == []
    assert _aespa_logo_lines(98, animation_frame=50) == _aespa_logo_lines(
        98, animation_frame=0
    )
    assert _aespa_logo_lines(40, animation_frame=50) == _aespa_logo_lines(
        40, animation_frame=0
    )


def test_agent_logo_times_wave_centred_radial_pulse_to_first_peak() -> None:
    assert _wave_visual_center(_AESPA_WAVE_PATH) == (34, 32)
    assert _wave_visual_center(_AESPA_WAVE_PATH_COMPACT) == (17.5, 19)
    assert _wave_visual_center(_AESPA_WAVE_PATH_LARGE) == (50, 54)

    def pulse_cells(lines: list[str]) -> list[tuple[int, int]]:
        cells: list[tuple[int, int]] = []
        for row, line in enumerate(lines):
            for match in re.finditer(
                r"\x1b\[38;5;(248|250|252|254|255)m([^\x1b]+)", line
            ):
                start = len(_ANSI_SGR.sub("", line[: match.start()]))
                cells.extend(
                    (start + offset, row)
                    for offset, character in enumerate(match.group(2))
                    if character != " "
                )
        return cells

    peak_frame = pulse_cells(_aespa_logo_lines(98, animation_frame=10))
    expanding_frame = pulse_cells(_aespa_logo_lines(98, animation_frame=16))

    assert any(column < 48 and row < 12 for column, row in expanding_frame)
    assert any(column > 48 and row < 12 for column, row in expanding_frame)
    assert any(column < 48 and row > 12 for column, row in expanding_frame)
    assert any(column > 48 and row > 12 for column, row in expanding_frame)
    assert min(row for _, row in expanding_frame) < min(row for _, row in peak_frame)
    assert max(row for _, row in expanding_frame) > max(row for _, row in peak_frame)

    compact_expanding = pulse_cells(_aespa_logo_lines(40, animation_frame=19))
    large_expanding = pulse_cells(
        _aespa_logo_lines(120, animation_frame=18, large=True)
    )
    assert (
        max(row for _, row in compact_expanding)
        - min(row for _, row in compact_expanding)
        >= 8
    )
    assert (
        max(row for _, row in large_expanding) - min(row for _, row in large_expanding)
        >= 20
    )


def test_hidden_logo_view_centres_full_logo_and_keeps_animating(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output, terminal_size=(100, 35))
    monkeypatch.setattr(
        "aespa.console._python_executor_runtime_status", lambda: "ready"
    )
    handler.start_screen()
    handler.emit(_record("aespa.agent.activity", logging.INFO, "Scanner started"))

    handler.switch(LOGO)
    frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]

    assert "\x1b[7;1H" in frame
    assert "+ooooooooooooooooooooooooo+" in _ANSI_SGR.sub("", frame)
    assert "[1 Agent]" not in frame
    assert "[1-6] Views" not in frame
    assert handler.advance_logo_animation() is True


def test_large_terminal_uses_high_detail_logo_and_traced_heartbeat(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output, terminal_size=(120, 50))
    monkeypatch.setattr(
        "aespa.console._python_executor_runtime_status", lambda: "ready"
    )

    handler.start_screen()
    agent_frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    plain_agent_frame = _ANSI_SGR.sub("", agent_frame)
    assert "+oo+     ooo               ssssso" not in plain_agent_frame
    assert "A E S P A" not in plain_agent_frame

    handler.switch(LOGO)
    logo_frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "\x1b[5;1H" in logo_frame
    assert "+oo+     ooo               ssssso" in _ANSI_SGR.sub("", logo_frame)

    pulse_pattern = re.compile(r"\x1b\[38;5;(248|250|252|254|255)m")
    peak_rows = [
        row
        for row, line in enumerate(
            _aespa_logo_lines(120, animation_frame=12, large=True)
        )
        if pulse_pattern.search(line)
    ]
    trough_rows = [
        row
        for row, line in enumerate(
            _aespa_logo_lines(120, animation_frame=18, large=True)
        )
        if pulse_pattern.search(line)
    ]
    assert min(peak_rows) <= 20
    assert max(trough_rows) >= 33
    assert not any(
        pulse_pattern.search(line)
        for line in _aespa_logo_lines(120, animation_frame=40, large=True)
    )


def test_agent_logo_has_a_compact_narrow_terminal_variant(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output, terminal_size=(40, 24))
    monkeypatch.setattr(
        "aespa.console._python_executor_runtime_status", lambda: "ready"
    )

    handler.start_screen()

    frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "A E S P A" not in frame
    assert ".ossssssssssssso." not in _ANSI_SGR.sub("", frame)

    plain_lines = [_ANSI_SGR.sub("", line) for line in _aespa_logo_lines(38)]
    centers = []
    for line in plain_lines:
        first = len(line) - len(line.lstrip())
        last = len(line.rstrip()) - 1
        centers.append((first + last) / 2)
    assert max(centers) - min(centers) <= 1


def test_console_ready_line_uses_configured_ipv6_host_and_port(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output, host="::1", port=8123)
    monkeypatch.setattr(
        "aespa.console._python_executor_runtime_status", lambda: "ready"
    )

    handler.start_screen()
    handler.start_screen()

    assert list(handler.buffers[AGENT]) == ["Ready - listening on http://[::1]:8123"]


def test_console_warns_below_ready_line_when_python_executor_is_missing(
    monkeypatch,
) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    monkeypatch.setattr(
        "aespa.console._python_executor_runtime_status", lambda: "image_missing"
    )

    handler.start_screen()
    handler.start_screen()

    assert list(handler.buffers[AGENT]) == [
        "Ready - listening on http://127.0.0.1:8000",
        (
            "Python executor image is not installed - run docker pull "
            "ledwardchow/aespa-python-executor:0.1"
        ),
    ]


def test_console_warns_when_docker_service_is_unavailable(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    monkeypatch.setattr(
        "aespa.console._python_executor_runtime_status", lambda: "docker_unavailable"
    )

    handler.start_screen()

    assert list(handler.buffers[AGENT]) == [
        "Ready - listening on http://127.0.0.1:8000",
        (
            "Python sandbox is unavailable - Docker is installed, but its service is "
            "not running or cannot be reached. Start Docker and try again"
        ),
    ]


def test_python_executor_check_inspects_the_published_image(monkeypatch) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr("aespa.console.shutil.which", lambda command: "/bin/docker")

    def fake_run(command, **_kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0 if command[1] == "info" else 1)

    monkeypatch.setattr("aespa.console.subprocess.run", fake_run)

    assert _python_executor_runtime_status() == "image_missing"
    assert commands == [
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        [
            "docker",
            "image",
            "inspect",
            "ledwardchow/aespa-python-executor:0.1",
        ],
    ]


def test_legend_is_drawn_on_last_terminal_row(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    monkeypatch.setattr(
        "aespa.console.shutil.get_terminal_size", lambda fallback: (80, 12)
    )

    handler.start_screen()
    for _ in range(58):
        handler.advance_logo_animation()
    handler.emit(
        _record(
            "uvicorn.access",
            logging.INFO,
            '%s - "%s %s HTTP/%s" %d',
            ("127.0.0.1:1234", "GET", "/api/health", "1.1", 200),
        )
    )

    assert "\x1b[12;1H\x1b[2K[1-6] Views" in output.getvalue()


def test_console_legends_call_ctrl_c_quit() -> None:
    legends = [
        _legend(AGENT),
        _legend(SETTINGS, settings_section="root"),
        _legend(SETTINGS, settings_section="server"),
    ]

    assert all("[Ctrl+C] Quit" in legend for legend in legends)
    assert all("[Ctrl+C] Stop" not in legend for legend in legends)


def test_page_up_and_page_down_navigate_fixed_viewport(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    monkeypatch.setattr(
        "aespa.console.shutil.get_terminal_size", lambda fallback: (80, 8)
    )
    for index in range(12):
        handler.emit(
            _record(
                "uvicorn.access",
                logging.INFO,
                '%s - "%s %s HTTP/%s" %d',
                ("client", "GET", f"/request/{index}", "1.1", 200),
            )
        )
    handler.switch(HTTP)
    handler.start_screen()

    handler.page_up()
    older_frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert handler.page_indices[HTTP] == 1
    assert "Page 2/3" in older_frame
    assert "Scrollback 50%" in older_frame
    assert "\x1b[3;80H│" in older_frame
    assert "/request/11" not in older_frame

    handler.page_down()
    newest_frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert handler.page_indices[HTTP] == 2
    assert "Page 3/3" in newest_frame
    assert "Scrollback 0%" in newest_frame
    assert "\x1b[7;80H█" in newest_frame
    assert "/request/11" in newest_frame


def test_scrolled_page_stays_anchored_when_new_records_arrive(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    monkeypatch.setattr(
        "aespa.console.shutil.get_terminal_size", lambda fallback: (80, 8)
    )
    for index in range(12):
        handler.emit(
            _record(
                "uvicorn.access",
                logging.INFO,
                '%s - "%s %s HTTP/%s" %d',
                ("client", "GET", f"/request/{index}", "1.1", 200),
            )
        )
    handler.switch(HTTP)
    handler.start_screen()
    handler.page_up()

    for index in range(12, 18):
        handler.emit(
            _record(
                "uvicorn.access",
                logging.INFO,
                '%s - "%s %s HTTP/%s" %d',
                ("client", "GET", f"/request/{index}", "1.1", 200),
            )
        )

    frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert handler.page_indices[HTTP] == 1
    assert handler.follow_live[HTTP] is False
    assert "Page 2/4" in frame
    assert "/request/5" in frame
    assert "/request/9" in frame
    assert "/request/12" not in frame


def test_posix_page_key_sequences_are_handled(monkeypatch) -> None:
    console = InteractiveConsole(
        input_stream=io.StringIO(), output_stream=io.StringIO()
    )
    calls: list[str] = []
    monkeypatch.setattr(console.handler, "page_up", lambda: calls.append("up"))
    monkeypatch.setattr(console.handler, "page_down", lambda: calls.append("down"))
    monkeypatch.setattr(
        console.handler, "select_previous_llm", lambda: calls.append("previous")
    )
    monkeypatch.setattr(
        console.handler, "select_next_llm", lambda: calls.append("next")
    )
    monkeypatch.setattr(
        console.handler, "toggle_selected_llm", lambda: calls.append("toggle")
    )

    console._process_posix_keys(b"\x1b[5")
    assert calls == []
    console._process_posix_keys(b"~\x1b[6~\x1b[A\x1b[B\r")
    assert calls == ["up", "down", "previous", "next", "toggle"]


def test_posix_mouse_wheel_sequences_scroll_console_pages(monkeypatch) -> None:
    console = InteractiveConsole(
        input_stream=io.StringIO(), output_stream=io.StringIO()
    )
    calls: list[str] = []
    monkeypatch.setattr(console.handler, "page_up", lambda: calls.append("up"))
    monkeypatch.setattr(console.handler, "page_down", lambda: calls.append("down"))

    console._process_posix_keys(b"\x1b[<64;20")
    assert calls == []
    console._process_posix_keys(b";8M\x1b[<65;20;8M")
    console._process_posix_keys(b"\x1b[M`44\x1b[Ma44")

    assert calls == ["up", "down", "up", "down"]


def test_console_enables_and_restores_terminal_mouse_and_cursor_modes() -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)

    handler.start_screen()
    handler.stop_screen()

    rendered = output.getvalue()
    assert "\x1b[?1049h\x1b[?1000h\x1b[?1006h\x1b[?25l" in rendered
    assert rendered.endswith("\x1b[?1006l\x1b[?1000l\x1b[?1049l\x1b[?25h")


def test_terminal_resize_reflows_and_redraws_viewport(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    size = [80, 12]
    monkeypatch.setattr(
        "aespa.console.shutil.get_terminal_size", lambda fallback: tuple(size)
    )
    handler.emit(
        _record(
            "uvicorn.access",
            logging.INFO,
            '%s - "%s %s HTTP/%s" %d',
            ("client", "GET", "/a/long/path/that/will/reflow", "1.1", 200),
        )
    )
    handler.switch(HTTP)
    handler.start_screen()
    frames_before = output.getvalue().count("\x1b[2J\x1b[H")

    assert handler.refresh_for_resize() is False
    size[:] = [50, 9]
    assert handler.refresh_for_resize() is True

    rendered = output.getvalue()
    assert rendered.count("\x1b[2J\x1b[H") == frames_before + 1
    assert "\x1b[9;1H\x1b[2K[1-6] Views" in rendered
    assert "\x1b[3;50H" in rendered


def test_llm_calls_are_collapsed_navigable_and_expandable(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    monkeypatch.setattr(
        "aespa.console.shutil.get_terminal_size", lambda fallback: (120, 16)
    )
    handler.emit(
        _llm_record(10, "REQUEST", "first request", operation="api_docs.parse")
    )
    handler.emit(
        _llm_record(10, "RESPONSE", "first response", operation="api_docs.parse")
    )
    handler.emit(_llm_record(11, "REQUEST", "second request"))
    handler.start_screen()
    handler.switch(LLM)

    collapsed = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "2026-09-05 18:34:46 web run 7" in collapsed
    assert "#10 api_docs.parse [tools] COMPLETE" in collapsed
    assert "#11 scanner.thinking_scan [tools] PENDING" in collapsed
    assert "first request" not in collapsed
    assert "first response" not in collapsed
    assert "Call 2/2" in collapsed

    handler.select_previous_llm()
    assert handler.llm_selected == 0
    handler.toggle_selected_llm()
    expanded = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "Call 1/2" in expanded
    assert "--- REQUEST ---" in expanded
    assert "first request" in expanded
    assert "--- RESPONSE ---" in expanded
    assert "first response" in expanded

    handler.toggle_selected_llm()
    contracted = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "first request" not in contracted


def test_llm_call_header_identifies_calls_without_run_context(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    monkeypatch.setattr(
        "aespa.console.shutil.get_terminal_size", lambda fallback: (140, 12)
    )
    handler.emit(_llm_record(12, "REQUEST", "request", run_id=None))
    handler.start_screen()
    handler.switch(LLM)

    rendered = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "2026-09-05 18:34:46 no run #12" in rendered


def test_testing_traffic_is_collapsed_navigable_and_expandable(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    monkeypatch.setattr(
        "aespa.console.shutil.get_terminal_size", lambda fallback: (140, 20)
    )
    handler.emit(_testing_record(21, "POST", "https://target.test/login", 401))
    handler.emit(_testing_record(22, "GET", "https://target.test/admin", 200))
    handler.start_screen()
    handler.switch(TESTING)

    collapsed = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "#21 POST https://target.test/login [401 42ms]" in collapsed
    assert "#22 GET https://target.test/admin [200 42ms]" in collapsed
    assert '"payload":"test"' not in collapsed
    assert "Request 2/2" in collapsed

    handler.select_previous_llm()
    assert handler.testing_selected == 0
    handler.toggle_selected_llm()
    expanded = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "Request 1/2" in expanded
    assert "web run 7 · httpx · session alice-session · user alice" in expanded
    assert "--- REQUEST ---" in expanded
    assert '"payload":"test"' in expanded
    assert "--- RESPONSE ---" in expanded
    assert '"ok":true' in expanded

    handler.toggle_selected_llm()
    contracted = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert '"payload":"test"' not in contracted


def test_error_view_includes_traceback() -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    try:
        raise RuntimeError("broken")
    except RuntimeError:
        record = _record("aespa.service", logging.ERROR, "request crashed")
        record.exc_info = sys.exc_info()
        handler.emit(record)

    assert "RuntimeError: broken" in handler.buffers[ERRORS][0]


def test_settings_view_edits_persists_and_requests_port_restart(
    tmp_path, monkeypatch
) -> None:
    output = io.StringIO()
    env_path = tmp_path / ".env"
    env_path.write_text("AESPA_HOST=127.0.0.1\nKEEP_ME=yes\n", encoding="utf-8")
    requested: list[int] = []
    console = InteractiveConsole(
        input_stream=io.StringIO(),
        output_stream=output,
        port=8000,
        env_path=env_path,
        on_port_change=requested.append,
    )
    monkeypatch.setattr("aespa.console._port_available", lambda host, port: True)

    console.handler.start_screen()
    console._process_posix_keys(b"6\r\r8123\r")

    assert console.handler.mode == SETTINGS
    assert console.handler.configured_port == 8123
    assert requested == [8123]
    assert env_path.read_text(encoding="utf-8") == (
        "AESPA_HOST=127.0.0.1\nKEEP_ME=yes\nAESPA_PORT=8123\n"
    )
    frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "Saved port 8123" in frame
    assert "Listening address" in frame
    assert "[Enter] Change port" in frame


def test_settings_menu_hides_server_details_until_opened() -> None:
    output = io.StringIO()
    console = InteractiveConsole(input_stream=io.StringIO(), output_stream=output)

    console.handler.start_screen()
    console._process_posix_keys(b"6")

    frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "Server Settings" in frame
    assert "Database Operations" in frame
    assert "Console Log Database" in frame
    assert "Listening address" not in frame
    assert "Port                " not in frame

    console._process_posix_keys(b"\r")
    frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "Listening address" in frame
    assert "Port                8000" in frame


def test_console_log_database_is_disabled_by_default(tmp_path) -> None:
    log_db_path = tmp_path / "logs.db"
    handler = InteractiveConsoleHandler(io.StringIO(), log_db_path=log_db_path)

    handler.emit(_record("aespa.agent.activity", logging.INFO, "not persisted"))

    assert handler.log_store.enabled is False
    assert not log_db_path.exists()


def test_console_log_database_records_full_logs_except_testing_traffic(
    tmp_path,
) -> None:
    output = io.StringIO()
    log_db_path = tmp_path / "logs.db"
    console = InteractiveConsole(
        input_stream=io.StringIO(),
        output_stream=output,
        log_db_path=log_db_path,
    )
    console.handler.start_screen()

    console._process_posix_keys(b"6\x1b[B\x1b[B\r\r")

    assert console.handler.settings_section == "logging"
    assert console.handler.log_store.enabled is True
    assert log_db_path.is_file()
    frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "Status              Enabled" in frame
    assert "Testing Traffic is excluded" in frame
    assert "without truncation" in frame

    request = "request line one\nrequest line two\nsecret-token"
    response = "response line one\nresponse line two"
    console.handler.emit(_llm_record(41, "REQUEST", request))
    console.handler.emit(_llm_record(41, "RESPONSE", response))
    console.handler.emit(_record("aespa.agent.activity", logging.INFO, "agent detail"))
    console.handler.emit(_record("aespa.service", logging.ERROR, "error detail"))
    console.handler.emit(
        _record(
            "uvicorn.access",
            logging.INFO,
            '%s - "%s %s HTTP/%s" %d',
            ("127.0.0.1:1234", "GET", "/api/health", "1.1", 200),
        )
    )
    console.handler.emit(_testing_record(99, "POST", "https://target.test", 201))

    with sqlite3.connect(log_db_path) as connection:
        rows = connection.execute(
            """
            SELECT view, message, llm_direction, llm_payload
            FROM console_logs ORDER BY id
            """
        ).fetchall()

    assert [row[0] for row in rows] == [LLM, LLM, AGENT, ERRORS, HTTP]
    assert rows[0][2:] == ("REQUEST", request)
    assert rows[1][2:] == ("RESPONSE", response)
    assert rows[2][1] == "agent detail"
    assert rows[3][1] == "error detail"
    assert "/api/health" in rows[4][1]

    console._process_posix_keys(b"\r")
    console.handler.emit(
        _record("aespa.agent.activity", logging.INFO, "after disabling")
    )
    with sqlite3.connect(log_db_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM console_logs").fetchone()[0]
    assert count == 5
    assert (
        InteractiveConsoleHandler(
            io.StringIO(), log_db_path=log_db_path
        ).log_store.enabled
        is False
    )


def test_settings_rejects_invalid_or_occupied_ports(tmp_path, monkeypatch) -> None:
    output = io.StringIO()
    console = InteractiveConsole(
        input_stream=io.StringIO(),
        output_stream=output,
        env_path=tmp_path / ".env",
    )
    console.handler.start_screen()
    console._process_posix_keys(b"6\r\r70000\r")
    assert "between 1 and 65535" in output.getvalue()

    monkeypatch.setattr("aespa.console._port_available", lambda host, port: False)
    console._process_posix_keys(b"\x1b\r9000\r")
    assert "Port 9000 is already in use" in output.getvalue()
    assert not (tmp_path / ".env").exists()


def test_database_settings_backup_uses_default_home_path(tmp_path, monkeypatch) -> None:
    output = io.StringIO()
    console = InteractiveConsole(input_stream=io.StringIO(), output_stream=output)
    destination = tmp_path / "aespa-backup.db"
    saved_paths = []
    monkeypatch.setattr(
        "aespa.console._default_database_backup_path", lambda: destination
    )
    monkeypatch.setattr(
        "aespa.services.database_operations.backup_database",
        lambda path: saved_paths.append(path) or path,
    )

    console.handler.start_screen()
    console._process_posix_keys(b"6\x1b[B\r\r\r")

    assert saved_paths == [destination]
    assert console.handler.settings_section == "database"
    assert "Database backup saved" in output.getvalue()


def test_database_settings_clear_requires_exact_confirmation(monkeypatch) -> None:
    output = io.StringIO()
    console = InteractiveConsole(input_stream=io.StringIO(), output_stream=output)
    calls = []
    monkeypatch.setattr(
        "aespa.services.database_operations.clear_scans",
        lambda: calls.append("clear") or 4,
    )

    console.handler.start_screen()
    console._process_posix_keys(b"6\x1b[B\r\x1b[B\rclear\r")

    assert calls == []
    assert 'Type "CLEAR" exactly' in output.getvalue()

    console._process_posix_keys(b"CLEAR\r")

    assert calls == ["clear"]
    assert "Cleared 4 scan runs." in output.getvalue()


def test_database_settings_reset_requires_reset_confirmation(monkeypatch) -> None:
    output = io.StringIO()
    console = InteractiveConsole(input_stream=io.StringIO(), output_stream=output)
    calls = []
    monkeypatch.setattr(
        "aespa.services.database_operations.reset_database",
        lambda: calls.append("reset"),
    )

    console.handler.start_screen()
    console._process_posix_keys(b"6\x1b[B\r\x1b[B\x1b[B\rRESET\r")

    assert calls == ["reset"]
    assert "Database reset complete." in output.getvalue()


def test_write_port_setting_replaces_existing_value(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "OTHER=value\nexport AESPA_PORT = 8000\nAESPA_PORT=8200\n",
        encoding="utf-8",
    )

    _write_port_setting(env_path, 8100)

    assert env_path.read_text(encoding="utf-8") == (
        "OTHER=value\nAESPA_PORT=8100\nAESPA_PORT=8100\n"
    )


def test_console_removes_handlers_that_bypass_view_filter() -> None:
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level
    bypass = logging.StreamHandler(io.StringIO())
    root.addHandler(bypass)
    console = InteractiveConsole(
        input_stream=io.StringIO(), output_stream=io.StringIO()
    )
    try:
        console._configure_logging()
        assert root.handlers == [console.handler]
    finally:
        root.handlers.clear()
        root.handlers.extend(old_handlers)
        root.setLevel(old_level)


def test_crawler_import_does_not_configure_process_logging() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import logging; "
                "root = logging.getLogger(); "
                "level = root.level; "
                "handlers = list(root.handlers); "
                "import aespa.services.crawler; "
                "assert root.level == level; "
                "assert root.handlers == handlers"
            ),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_llm_traffic_delimiters_identify_operation_and_pair(
    caplog, monkeypatch
) -> None:
    from aespa.services import llm

    async def fake_call_impl(config, prompt, screenshot):  # noqa: ARG001
        llm._last_response_cache_telemetry_var.set(
            {
                "call_id": llm._traffic_call_id_var.get(),
                "cache_read_tokens": 2048,
                "system_fingerprint": "fp_test",
            }
        )
        return "model response"

    monkeypatch.setattr(llm, "_call_impl", fake_call_impl)
    caplog.set_level(logging.INFO, logger="aespa.llm.traffic")
    config = SimpleNamespace(provider="test-provider", model="test-model")

    async def console_operation():
        return await llm._call(config, "model prompt", None)

    llm.set_run_context(217, lambda event: None, run_kind="web")
    try:
        assert asyncio.run(console_operation()) == "model response"
    finally:
        llm.clear_run_context()

    assert len(caplog.messages) == 2
    request, response = caplog.messages
    assert "BEGIN LLM operation=test_console.console_operation" in request
    assert "direction=REQUEST" in request
    assert "model prompt" in request
    assert "END LLM operation=" in request
    assert "direction=RESPONSE" in response
    assert "model response" in response
    assert '"cache_telemetry"' in response
    assert '"cache_read_tokens": 2048' in response
    assert '"system_fingerprint": "fp_test"' in response
    request_call = request.split("call=", 1)[1].split(" |", 1)[0]
    response_call = response.split("call=", 1)[1].split(" |", 1)[0]
    assert request_call == response_call
    assert caplog.records[0].aespa_llm_run_id == 217
    assert caplog.records[0].aespa_llm_run_kind == "web"


def test_startup_pulse_reveals_logo_in_all_sizes() -> None:
    for width, options in ((40, {}), (98, {}), (120, {"large": True})):
        frames = [
            [
                _ANSI_SGR.sub("", line)
                for line in _aespa_logo_lines(
                    width, animation_frame=frame, reveal=True, **options
                )
            ]
            for frame in range(61)
        ]
        assert not "".join(frames[0]).strip()
        reference = [
            _ANSI_SGR.sub("", line)
            for line in _aespa_logo_lines(width, animation_frame=40, **options)
        ]
        counts = [
            sum(
                shown != " "
                for line, original in zip(lines, reference)
                for shown, glyph in zip(line, original)
                if glyph != " "
            )
            for lines in frames
        ]
        assert 0 < counts[7] < counts[-1]
        assert counts == sorted(counts)
        full = [
            _ANSI_SGR.sub("", line)
            for line in _aespa_logo_lines(width, animation_frame=40, **options)
        ]
        assert frames[-1] == full


def test_startup_strike_flashes_and_settles_without_moving_logo() -> None:
    for width, options in ((40, {}), (98, {}), (120, {"large": True})):
        impact = "".join(
            line
            for frame in range(1, 30)
            for line in _aespa_logo_lines(
                width, animation_frame=frame, reveal=True, **options
            )
        )
        assert "\x1b[38;5;255m" in impact
        assert "\x1b[38;5;217m" in impact
        settled = _aespa_logo_lines(width, animation_frame=60, reveal=True, **options)
        assert settled == _aespa_logo_lines(width, animation_frame=40, **options)


def test_startup_wave_crosses_terminal_then_fades_away() -> None:
    for width, options, row, art, path in (
        (40, {}, 9, _AESPA_LOGO_COMPACT, _AESPA_WAVE_PATH_COMPACT),
        (98, {}, 15, _AESPA_LOGO, _AESPA_WAVE_PATH),
        (120, {"large": True}, 27, _AESPA_LOGO_LARGE, _AESPA_WAVE_PATH_LARGE),
    ):
        *_, fade_end = _startup_wave_timing(width, art, path)

        def frame(seconds):
            return _aespa_logo_lines(
                width, animation_frame=math.ceil(seconds / 0.05), reveal=True, **options
            )[row]

        entering = _ANSI_SGR.sub("", frame(0.05))
        assert entering.startswith("o" if options else "s")
        assert len(entering) == width
        assert entering[-1] == " "
        exiting = _ANSI_SGR.sub("", frame(fade_end - 0.8))
        assert exiting[0] == exiting[-1] == ("o" if options else "s")
        early_colors = re.findall(
            r"\x1b\[38;2;(\d+);(\d+);(\d+)m", frame(fade_end - 0.35)
        )
        late_colors = re.findall(
            r"\x1b\[38;2;(\d+);(\d+);(\d+)m", frame(fade_end - 0.10)
        )
        assert max(int(c[0]) for c in late_colors) < max(
            int(c[0]) for c in early_colors
        )
        # Side lines hold their colour while the logo's afterglow settles.
        side_colors = r"\x1b\[38;2;(\d+);(\d+);(\d+)m"
        assert re.findall(side_colors, frame(fade_end - 0.7)) == re.findall(
            side_colors, frame(fade_end - 0.45)
        )
        settled = _aespa_logo_lines(width, animation_frame=40, **options)[row]
        assert frame(fade_end) == settled
        for offset, glyph in (
            ((-1, "s"), (0, "o")) if options else ((-1, "+"), (0, "s"), (1, "+"))
        ):
            line = _ANSI_SGR.sub(
                "",
                _aespa_logo_lines(
                    width,
                    animation_frame=math.ceil((fade_end - 0.45) / 0.05),
                    reveal=True,
                    **options,
                )[row + offset],
            )
            assert line[0] == line[-1] == glyph


def test_startup_holds_logo_after_side_lines_fade(monkeypatch) -> None:
    monkeypatch.setattr(
        "aespa.console._python_executor_runtime_status", lambda: "ready"
    )
    handler = InteractiveConsoleHandler(io.StringIO(), terminal_size=(100, 35))
    handler.start_screen()
    for _ in range(math.ceil(handler._startup_duration() / 0.05) - 10):
        handler.advance_logo_animation()
    assert handler._startup_logo_active
    assert handler._startup_fade_phase is None
    for _ in range(9):
        handler.advance_logo_animation()
        assert handler._startup_logo_active
        assert handler._startup_fade_phase is None
    handler.advance_logo_animation()
    assert not handler._startup_logo_active
    assert handler._startup_fade_phase == "console"
    assert handler._startup_fade_frame == 0


def test_completed_startup_leaves_no_pulse_highlights(monkeypatch) -> None:
    monkeypatch.setattr(
        "aespa.console._python_executor_runtime_status", lambda: "ready"
    )
    for size in ((40, 24), (100, 35), (120, 50)):
        output = io.StringIO()
        handler = InteractiveConsoleHandler(output, terminal_size=size)
        handler.start_screen()
        for _ in range(math.ceil(handler._startup_duration() / 0.05) + 4):
            assert handler.advance_logo_animation()
        assert not handler.advance_logo_animation()
        frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
        assert "[1 Agent]" in frame
        assert "\x1b[38;5;196m" in frame
        assert "\x1b[38;5;203m" in frame
        assert not re.search(r"\x1b\[38;5;(248|250|252|254|255)m", frame)


def test_wave_crosses_terminal_in_one_second_at_every_size() -> None:
    for width, options, art, path in (
        (40, {}, _AESPA_LOGO_COMPACT, _AESPA_WAVE_PATH_COMPACT),
        (98, {}, _AESPA_LOGO, _AESPA_WAVE_PATH),
        (180, {"large": True}, _AESPA_LOGO_LARGE, _AESPA_WAVE_PATH_LARGE),
        (340, {"large": True}, _AESPA_LOGO_LARGE, _AESPA_WAVE_PATH_LARGE),
    ):
        speed, _, _, exit_start, fade_end = _startup_wave_timing(width, art, path)
        padding = max(0, (width - max(map(len, art))) // 2)
        arrival = exit_start + (width - 1 - padding - path[-1][0]) / speed
        assert abs(arrival - 1.0) < 1e-9
        assert abs(fade_end - 1.9) < 1e-9
        before = _ANSI_SGR.sub(
            "",
            _aespa_logo_lines(width, animation_frame=19, reveal=True, **options)[
                path[0][1]
            ],
        )
        after = _ANSI_SGR.sub(
            "",
            _aespa_logo_lines(width, animation_frame=20, reveal=True, **options)[
                path[0][1]
            ],
        )
        assert before[-1] == " "
        assert after[-1] in "os"


def test_logo_view_wave_finishes_in_one_second(monkeypatch) -> None:
    # Isolate the travelling highlight from the independently expanding ring.
    monkeypatch.setattr("aespa.console._radial_pulse_radius", lambda *args: -100.0)
    monkeypatch.setattr(
        "aespa.console._python_executor_runtime_status", lambda: "ready"
    )
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output, terminal_size=(100, 35))
    handler.start_screen()
    handler.switch(LOGO)
    for _ in range(19):
        assert handler.advance_logo_animation()
    pulse = re.compile(r"\x1b\[38;5;(248|250|252|254|255)m")
    assert pulse.search(output.getvalue().split("\x1b[2J\x1b[H")[-1])
    assert handler.advance_logo_animation()
    # The travelling highlight has ended, but its warm afterglow can remain.
    frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert not re.search(r"\x1b\[38;5;(248|250|252|254)m", frame)
    for _ in range(7):
        assert handler.advance_logo_animation()
    settled = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert not pulse.search(settled)
    assert "\x1b[38;5;217m" not in settled


def test_startup_and_logo_view_share_warm_afterglow() -> None:
    for reveal in (False, True):
        for width, options in ((40, {}), (98, {}), (120, {"large": True})):
            frames = [
                "".join(
                    _aespa_logo_lines(
                        width, animation_frame=frame, reveal=reveal, **options
                    )
                )
                for frame in range(1, 30)
            ]
            assert any("\x1b[38;5;255m" in frame for frame in frames)
            assert any("\x1b[38;5;217m" in frame for frame in frames)
            assert any("\x1b[38;5;203m" in frame for frame in frames)
            settled = "".join(
                _aespa_logo_lines(width, animation_frame=40, reveal=reveal, **options)
            )
            assert "\x1b[38;5;217m" not in settled
            assert "\x1b[38;5;255m" not in settled
            assert "\x1b[38;5;196m" in settled
