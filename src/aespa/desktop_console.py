"""Attach an external terminal to a running AESPA desktop process."""

from __future__ import annotations

import io
import os
import secrets
import select
import shlex
import shutil
import socket
import subprocess
import sys
import threading

from aespa.console import InteractiveConsole


class DesktopConsoleServer:
    """Serve one authenticated, loopback-only console at a time."""

    def __init__(self, *, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.token = secrets.token_urlsafe(32)
        self._active = threading.Lock()
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(2)
        self.bridge_port = self._listener.getsockname()[1]
        self._console = InteractiveConsole(
            input_stream=io.BytesIO(),
            output_stream=io.StringIO(),
            host=self.host,
            port=self.port,
            allow_port_change=False,
            replace_logging_handlers=False,
        )
        self._console.start_capture()
        threading.Thread(
            target=self._accept_connections,
            name="aespa-desktop-console",
            daemon=True,
        ).start()

    def open(self) -> None:
        """Open the platform terminal and connect it to this desktop process."""
        command = _client_command(self.bridge_port, self.token)
        if sys.platform == "darwin":
            _open_macos_terminal(command)
        elif os.name == "nt":
            subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(command)

    def _accept_connections(self) -> None:
        while True:
            connection, _address = self._listener.accept()
            threading.Thread(
                target=self._serve_connection,
                args=(connection,),
                name="aespa-desktop-console-session",
                daemon=True,
            ).start()

    def _serve_connection(self, connection: socket.socket) -> None:
        with connection:
            reader = connection.makefile("rb", buffering=0)
            writer = connection.makefile("w", encoding="utf-8", newline="")
            header = reader.readline(512).decode("utf-8", errors="replace").strip()
            parts = header.split()
            if len(parts) != 3 or not secrets.compare_digest(parts[0], self.token):
                writer.write("Unable to connect to the AESPA desktop console.\n")
                writer.flush()
                return
            if not self._active.acquire(blocking=False):
                writer.write("The AESPA console is already open in another terminal.\n")
                writer.flush()
                return
            try:
                try:
                    size = (max(20, int(parts[1])), max(5, int(parts[2])))
                except ValueError:
                    size = (120, 30)
                self._console.attach(
                    input_stream=reader,
                    output_stream=writer,
                    terminal_size=size,
                )
                try:
                    self._console.wait()
                finally:
                    try:
                        self._console.detach()
                    finally:
                        self._console.handler.stream = io.StringIO()
            except (BrokenPipeError, ConnectionError, OSError):
                pass
            finally:
                self._active.release()


def _client_command(port: int, token: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--desktop-console", str(port), token]
    return [
        sys.executable,
        "-m",
        "aespa.desktop_console",
        "--desktop-console",
        str(port),
        token,
    ]


def _open_macos_terminal(command: list[str]) -> None:
    shell_command = " ".join(shlex.quote(part) for part in command)
    script = (
        "on run argv\n"
        'tell application "Terminal"\n'
        "activate\n"
        "do script (item 1 of argv)\n"
        "end tell\n"
        "end run"
    )
    subprocess.Popen(["osascript", "-e", script, "--", shell_command])


def _prepare_windows_console() -> None:
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return
    import ctypes

    ctypes.windll.kernel32.AllocConsole()
    sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
    sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
    sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")


def _prepare_posix_terminal() -> None:
    """Restore stdio hidden by a windowed PyInstaller executable."""
    if os.name == "nt" or (sys.stdin is not None and sys.stdin.isatty()):
        return
    sys.stdin = open("/dev/tty", "r", encoding="utf-8", errors="replace")
    sys.stdout = open("/dev/tty", "w", encoding="utf-8", errors="replace")
    sys.stderr = open("/dev/tty", "w", encoding="utf-8", errors="replace")


def run_client(port: int, token: str) -> None:
    _prepare_windows_console()
    _prepare_posix_terminal()
    size = shutil.get_terminal_size(fallback=(120, 30))
    with socket.create_connection(("127.0.0.1", port), timeout=10) as connection:
        connection.settimeout(None)
        connection.sendall(f"{token} {size.columns} {size.lines}\n".encode())
        disconnected = threading.Event()
        output = threading.Thread(
            target=_copy_console_output,
            args=(connection, disconnected),
            daemon=True,
        )
        output.start()
        try:
            _copy_console_input(connection, disconnected)
        except (BrokenPipeError, KeyboardInterrupt, OSError):
            pass
        finally:
            try:
                connection.shutdown(socket.SHUT_WR)
            except OSError:
                pass
        output.join(timeout=1)


def _copy_console_output(
    connection: socket.socket, disconnected: threading.Event
) -> None:
    try:
        while True:
            data = connection.recv(65536)
            if not data:
                return
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
    except OSError:
        pass
    finally:
        disconnected.set()


def _copy_console_input(
    connection: socket.socket, disconnected: threading.Event
) -> None:
    if os.name == "nt":
        _copy_windows_console_input(connection, disconnected)
        return
    import termios
    import tty

    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while not disconnected.is_set():
            readable, _, _ = select.select([fd], [], [], 0.2)
            if not readable:
                continue
            data = os.read(fd, 32)
            if not data:
                return
            connection.sendall(data)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)


def _copy_windows_console_input(
    connection: socket.socket, disconnected: threading.Event
) -> None:
    import msvcrt
    import time

    special_keys = {
        "I": b"\x1b[5~",
        "Q": b"\x1b[6~",
        "H": b"\x1b[A",
        "P": b"\x1b[B",
    }
    while not disconnected.is_set():
        if not msvcrt.kbhit():
            time.sleep(0.05)
            continue
        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            encoded = special_keys.get(msvcrt.getwch())
            if encoded:
                connection.sendall(encoded)
        else:
            connection.sendall(key.encode("utf-8"))


def main() -> None:
    try:
        marker = sys.argv.index("--desktop-console")
        port = int(sys.argv[marker + 1])
        token = sys.argv[marker + 2]
    except (ValueError, IndexError):
        raise SystemExit("Usage: desktop_console --desktop-console PORT TOKEN")
    run_client(port, token)


if __name__ == "__main__":
    main()
