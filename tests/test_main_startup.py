from __future__ import annotations

import importlib
import socket

import pytest

from aespa.main import (
    _find_available_port,
    _port_available,
    _run_server,
    _server_startup_failure_message,
)

main_module = importlib.import_module("aespa.main")


def test_port_selection_uses_preferred_port_when_available(monkeypatch) -> None:
    checked = []
    monkeypatch.setattr(
        main_module,
        "_port_available",
        lambda host, port: checked.append(port) or True,
    )

    assert _find_available_port("127.0.0.1", 8000) == 8000
    assert checked == [8000]


def test_port_selection_skips_occupied_fallback_ports(monkeypatch) -> None:
    checked = []

    def available(host, port):
        checked.append(port)
        return port == 9002

    monkeypatch.setattr(main_module, "_port_available", available)

    assert _find_available_port("127.0.0.1", 8000) == 9002
    assert checked == [8000, 9000, 9001, 9002]


def test_port_selection_continues_after_custom_port(monkeypatch) -> None:
    checked = []

    def available(host, port):
        checked.append(port)
        return port == 9101

    monkeypatch.setattr(main_module, "_port_available", available)

    assert _find_available_port("127.0.0.1", 9100) == 9101
    assert checked == [9100, 9101]


def test_port_check_accepts_an_available_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as finder:
        finder.bind(("127.0.0.1", 0))
        port = finder.getsockname()[1]

    assert _port_available("127.0.0.1", port)


def test_port_check_detects_an_occupied_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        assert not _port_available("127.0.0.1", port)


def test_server_runner_treats_ctrl_c_as_a_clean_exit() -> None:
    class InterruptedServer:
        def run(self) -> None:
            raise KeyboardInterrupt

    assert _run_server(InterruptedServer()) is False


def test_server_runner_does_not_hide_other_errors() -> None:
    class FailedServer:
        def run(self) -> None:
            raise RuntimeError("startup failed")

    with pytest.raises(RuntimeError, match="startup failed"):
        _run_server(FailedServer())


def test_startup_failure_preserves_errors_captured_by_interactive_console() -> None:
    class FailedServer:
        started = False

    class Handler:
        buffers = {
            "errors": [
                "12:00:00  ERROR  uvicorn.error: Application startup failed\n"
                "sqlite3.IntegrityError: FOREIGN KEY constraint failed"
            ]
        }

    class Console:
        handler = Handler()

    message = _server_startup_failure_message(FailedServer(), Console())

    assert message is not None
    assert "Backend startup failed" in message
    assert "sqlite3.IntegrityError: FOREIGN KEY constraint failed" in message


def test_started_server_has_no_startup_failure_message() -> None:
    class StartedServer:
        started = True

    assert _server_startup_failure_message(StartedServer()) is None
