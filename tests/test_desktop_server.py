from __future__ import annotations

import socket

import pytest

from aespa.desktop_server import LocalServerStartup


def test_reserved_port_cannot_be_taken_before_server_starts():
    startup = LocalServerStartup.reserve()
    competing_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(OSError):
            competing_socket.bind(("127.0.0.1", startup.port))
    finally:
        competing_socket.close()
        startup.listener.close()


def test_wait_until_ready_accepts_reserved_listener():
    startup = LocalServerStartup.reserve()
    try:
        startup.listener.listen()
        startup.wait_until_ready(timeout=0.5)
        assert startup.ready is True
    finally:
        startup.listener.close()


def test_wait_until_ready_reports_system_exit():
    startup = LocalServerStartup.reserve()
    try:
        startup.error = SystemExit(1)
        with pytest.raises(
            RuntimeError,
            match="Backend server failed to start: backend process exited with code 1",
        ):
            startup.wait_until_ready(timeout=0.5)
    finally:
        startup.listener.close()
