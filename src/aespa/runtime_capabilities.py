"""Runtime capability checks that do not depend on saved AESPA settings."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

NO_GRAPHICAL_DISPLAY_MESSAGE = (
    "No graphical display is available. Guided login and visible browser mode "
    "are disabled. Set DISPLAY or WAYLAND_DISPLAY, then restart AESPA."
)


def graphical_display_available() -> bool:
    """Return whether this process can connect to a Linux X11 or Wayland display."""
    if not sys.platform.startswith("linux"):
        return True
    return _wayland_display_available() or _x11_display_available()


def _wayland_display_available() -> bool:
    display = os.environ.get("WAYLAND_DISPLAY")
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if not display:
        return False

    path = Path(display)
    if not path.is_absolute():
        if not runtime_dir:
            return False
        path = Path(runtime_dir) / path
    return _unix_socket_available(path)


def _x11_display_available() -> bool:
    display = os.environ.get("DISPLAY")
    if not display:
        return False

    host, separator, display_part = display.rpartition(":")
    if not separator:
        return False
    display_number = display_part.partition(".")[0]
    if not display_number.isdigit():
        return False

    number = int(display_number)
    if host in {"", "unix"} or host.startswith("unix/"):
        return _unix_socket_available(Path(f"/tmp/.X11-unix/X{number}"))

    host = host.removeprefix("tcp/")
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        with socket.create_connection((host, 6000 + number), timeout=0.25):
            return True
    except OSError:
        return False


def _unix_socket_available(path: Path) -> bool:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(0.25)
            connection.connect(str(path))
        return True
    except OSError:
        return False
