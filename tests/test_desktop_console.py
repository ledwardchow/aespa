from __future__ import annotations

import io
import logging
import socket
import threading

from aespa import desktop_console
from aespa.console import AGENT, InteractiveConsole


def test_client_command_uses_module_when_running_from_source(monkeypatch) -> None:
    monkeypatch.delattr(desktop_console.sys, "frozen", raising=False)
    monkeypatch.setattr(desktop_console.sys, "executable", "/python")

    assert desktop_console._client_command(4321, "secret") == [
        "/python",
        "-m",
        "aespa.desktop_console",
        "--desktop-console",
        "4321",
        "secret",
    ]


def test_client_command_reuses_frozen_desktop_executable(monkeypatch) -> None:
    monkeypatch.setattr(desktop_console.sys, "frozen", True, raising=False)
    monkeypatch.setattr(desktop_console.sys, "executable", "/AESPA")

    assert desktop_console._client_command(4321, "secret") == [
        "/AESPA",
        "--desktop-console",
        "4321",
        "secret",
    ]


def test_console_captures_logs_while_detached_and_preserves_state() -> None:
    console = InteractiveConsole(
        input_stream=io.BytesIO(),
        output_stream=io.StringIO(),
        replace_logging_handlers=False,
    )
    logger = logging.getLogger("aespa.agent.activity")
    try:
        console.start_capture()
        logger.info("captured before first open")

        first_output = io.StringIO()
        console.attach(
            input_stream=io.BytesIO(),
            output_stream=first_output,
            terminal_size=(100, 20),
        )
        console.wait()
        console.detach()

        logger.info("captured while closed")
        second_output = io.StringIO()
        console.attach(
            input_stream=io.BytesIO(),
            output_stream=second_output,
            terminal_size=(100, 20),
        )
        console.wait()
        console.detach()

        assert console.handler.mode == AGENT
        assert "captured before first open" in second_output.getvalue()
        assert "captured while closed" in second_output.getvalue()
    finally:
        console.stop()


def test_console_bridge_attaches_console_to_authenticated_socket(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class FakeConsole:
        def __init__(self, **kwargs) -> None:
            calls.append(("init", kwargs))
            self.handler = type("Handler", (), {"stream": None})()

        def start_capture(self) -> None:
            calls.append(("start_capture", None))

        def attach(self, **kwargs) -> None:
            calls.append(("attach", kwargs))

        def wait(self) -> None:
            calls.append(("wait", None))

        def detach(self) -> None:
            calls.append(("detach", None))

    monkeypatch.setattr(desktop_console, "InteractiveConsole", FakeConsole)
    server = DesktopConsoleFixture(token="secret")
    client, accepted = socket.socketpair()
    worker = threading.Thread(target=server._serve_connection, args=(accepted,))
    worker.start()
    client.sendall(b"secret 90 24\n")
    client.shutdown(socket.SHUT_WR)
    worker.join(timeout=2)
    client.close()

    assert not worker.is_alive()
    assert [name for name, _value in calls] == [
        "init",
        "start_capture",
        "attach",
        "wait",
        "detach",
    ]
    options = calls[0][1]
    assert options["host"] == "127.0.0.1"
    assert options["port"] == 8123
    assert options["allow_port_change"] is False
    assert options["replace_logging_handlers"] is False
    attach_options = calls[2][1]
    assert attach_options["terminal_size"] == (90, 24)


class DesktopConsoleFixture(desktop_console.DesktopConsoleServer):
    def __init__(self, *, token: str) -> None:
        self.host = "127.0.0.1"
        self.port = 8123
        self.token = token
        self._active = threading.Lock()
        self._console = desktop_console.InteractiveConsole(
            input_stream=None,
            output_stream=None,
            host=self.host,
            port=self.port,
            allow_port_change=False,
            replace_logging_handlers=False,
        )
        self._console.start_capture()
