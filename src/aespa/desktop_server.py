"""Shared local server startup support for desktop launchers."""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass, field


@dataclass
class LocalServerStartup:
    """Own a reserved loopback socket until Uvicorn starts using it."""

    listener: socket.socket
    error: BaseException | None = None
    ready: bool = False
    port: int = field(init=False)

    def __post_init__(self) -> None:
        self.port = self.listener.getsockname()[1]

    @classmethod
    def reserve(cls) -> LocalServerStartup:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.bind(("127.0.0.1", 0))
        except BaseException:
            listener.close()
            raise
        return cls(listener)

    def serve(self) -> None:
        try:
            import uvicorn

            from aespa.main import app

            server = uvicorn.Server(
                uvicorn.Config(
                    app,
                    host="127.0.0.1",
                    port=self.port,
                    log_level="info",
                )
            )
            server.run(sockets=[self.listener])
            if not self.ready:
                self.error = RuntimeError("Backend server stopped during startup")
        except BaseException as exc:
            # Uvicorn uses SystemExit for startup failures such as bind errors.
            # Store BaseException so the GUI can report those failures promptly.
            self.error = exc
        finally:
            self.listener.close()

    def wait_until_ready(self, timeout: float = 60.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.raise_if_failed()
            try:
                with socket.create_connection(("127.0.0.1", self.port), 0.25):
                    self.ready = True
                    return
            except OSError:
                time.sleep(0.1)
        self.raise_if_failed()
        raise TimeoutError(
            f"Backend server did not become ready on port {self.port} "
            f"within {timeout:g}s"
        )

    def raise_if_failed(self) -> None:
        if self.error is None:
            return
        if isinstance(self.error, SystemExit):
            detail = f"backend process exited with code {self.error.code}"
        else:
            detail = str(self.error) or type(self.error).__name__
        raise RuntimeError(f"Backend server failed to start: {detail}") from self.error


def start_local_server(timeout: float = 60.0) -> int:
    startup = LocalServerStartup.reserve()
    threading.Thread(target=startup.serve, daemon=True).start()
    startup.wait_until_ready(timeout)
    return startup.port
