from __future__ import annotations

import socket

import pytest

from aespa.main import _ensure_port_available, _run_server


def test_port_check_accepts_an_available_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as finder:
        finder.bind(("127.0.0.1", 0))
        port = finder.getsockname()[1]

    _ensure_port_available("127.0.0.1", port)


def test_port_check_explains_how_to_resolve_an_occupied_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        with pytest.raises(SystemExit) as exc_info:
            _ensure_port_available("127.0.0.1", port)

    message = str(exc_info.value)
    assert f"127.0.0.1:{port} is already in use" in message
    assert f"AESPA_PORT={port + 1}" in message


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
