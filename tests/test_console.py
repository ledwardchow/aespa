from __future__ import annotations

import asyncio
import io
import logging
import sys
from types import SimpleNamespace

from aespa.console import (
    _ANSI_SGR,
    AGENT,
    ERRORS,
    HTTP,
    LLM,
    SETTINGS,
    TESTING,
    InteractiveConsole,
    InteractiveConsoleHandler,
    _aespa_logo_lines,
    _python_executor_image_present,
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
) -> logging.LogRecord:
    record = _record("aespa.llm.traffic", logging.INFO, "structured LLM traffic")
    record.aespa_llm_call_id = call_id
    record.aespa_llm_operation = operation
    record.aespa_llm_kind = "tools"
    record.aespa_llm_direction = direction
    record.aespa_llm_context = "openai/test-model - web run 7"
    record.aespa_llm_payload = payload
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
    assert "[1 Agent]" in output.getvalue()
    assert "Ready - listening on http://127.0.0.1:8000" in output.getvalue()
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


def test_agent_logo_is_colored_and_clears_on_first_agent_message(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output, terminal_size=(100, 35))
    monkeypatch.setattr("aespa.console._python_executor_image_present", lambda: True)

    handler.start_screen()

    initial_frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "+ooooooooooooooooooooooooo+" in _ANSI_SGR.sub("", initial_frame)
    assert "\x1b[38;5;196m" in initial_frame
    assert "\x1b[38;5;203m" in initial_frame
    assert "Ready - listening" in initial_frame

    handler.emit(_record("aespa.agent.activity", logging.INFO, "Scanner started"))

    agent_frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "+ooooooooooooooooooooooooo+" not in _ANSI_SGR.sub("", agent_frame)
    assert "Scanner started" in agent_frame


def test_agent_logo_has_a_compact_narrow_terminal_variant(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output, terminal_size=(40, 24))
    monkeypatch.setattr("aespa.console._python_executor_image_present", lambda: True)

    handler.start_screen()

    frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "A E S P A" in frame
    assert ".ossssssssssssso." in _ANSI_SGR.sub("", frame)

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
    monkeypatch.setattr("aespa.console._python_executor_image_present", lambda: True)

    handler.start_screen()
    handler.start_screen()

    assert list(handler.buffers[AGENT]) == ["Ready - listening on http://[::1]:8123"]


def test_console_warns_below_ready_line_when_python_executor_is_missing(
    monkeypatch,
) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    monkeypatch.setattr("aespa.console._python_executor_image_present", lambda: False)

    handler.start_screen()
    handler.start_screen()

    assert list(handler.buffers[AGENT]) == [
        "Ready - listening on http://127.0.0.1:8000",
        (
            "Python executor image is not installed - run docker pull "
            "ledwardchow/aespa-python-executor:0.1"
        ),
    ]


def test_python_executor_check_inspects_the_published_image(monkeypatch) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr("aespa.console.shutil.which", lambda command: "/bin/docker")

    def fake_run(command, **_kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr("aespa.console.subprocess.run", fake_run)

    assert _python_executor_image_present() is False
    assert commands == [
        [
            "docker",
            "image",
            "inspect",
            "ledwardchow/aespa-python-executor:0.1",
        ]
    ]


def test_legend_is_drawn_on_last_terminal_row(monkeypatch) -> None:
    output = io.StringIO()
    handler = InteractiveConsoleHandler(output)
    monkeypatch.setattr(
        "aespa.console.shutil.get_terminal_size", lambda fallback: (80, 12)
    )

    handler.start_screen()
    handler.emit(
        _record(
            "uvicorn.access",
            logging.INFO,
            '%s - "%s %s HTTP/%s" %d',
            ("127.0.0.1:1234", "GET", "/api/health", "1.1", 200),
        )
    )

    assert "\x1b[12;1H\x1b[2K[1-6] Views" in output.getvalue()


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
    assert "Listening address" not in frame
    assert "Port                " not in frame

    console._process_posix_keys(b"\r")
    frame = output.getvalue().split("\x1b[2J\x1b[H")[-1]
    assert "Listening address" in frame
    assert "Port                8000" in frame


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


def test_llm_traffic_delimiters_identify_operation_and_pair(
    caplog, monkeypatch
) -> None:
    from aespa.services import llm

    async def fake_call_impl(config, prompt, screenshot):  # noqa: ARG001
        return "model response"

    monkeypatch.setattr(llm, "_call_impl", fake_call_impl)
    caplog.set_level(logging.INFO, logger="aespa.llm.traffic")
    config = SimpleNamespace(provider="test-provider", model="test-model")

    async def console_operation():
        return await llm._call(config, "model prompt", None)

    assert asyncio.run(console_operation()) == "model response"

    assert len(caplog.messages) == 2
    request, response = caplog.messages
    assert "BEGIN LLM operation=test_console.console_operation" in request
    assert "direction=REQUEST" in request
    assert "model prompt" in request
    assert "END LLM operation=" in request
    assert "direction=RESPONSE" in response
    assert "model response" in response
    request_call = request.split("call=", 1)[1].split(" |", 1)[0]
    response_call = response.split("call=", 1)[1].split(" |", 1)[0]
    assert request_call == response_call
