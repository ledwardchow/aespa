from __future__ import annotations

import asyncio
import socket
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

import uvicorn

from aespa.config import Settings
from aespa.extensions.api import ExtensionApiDispatcher
from aespa.local_auth import INTEGRATION_PREFIX, AuthManager, LocalAuthMiddleware


def running_in_docker(settings: Settings) -> bool:
    return (
        settings.running_in_docker
        or Path("/.dockerenv").exists()
        or Path("/run/.containerenv").exists()
    )


class IntegrationApi:
    def __init__(self, auth: AuthManager):
        self.dispatcher = LocalAuthMiddleware(ExtensionApiDispatcher(), auth)

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] != "http" or not (
            path == INTEGRATION_PREFIX or path.startswith(INTEGRATION_PREFIX + "/")
        ):
            return await ExtensionApiDispatcher._not_found(scope, receive, send)
        await self.dispatcher(scope, receive, send)


def integration_app(auth: AuthManager):
    return IntegrationApi(auth)


class IntegrationServer(uvicorn.Server):
    @contextmanager
    def capture_signals(self):
        yield


@asynccontextmanager
async def integration_listener(settings: Settings, auth: AuthManager):
    if settings.integration_port is None or running_in_docker(settings):
        yield None
        return
    family = socket.AF_INET6 if ":" in settings.integration_host else socket.AF_INET
    listener = socket.create_server(
        (settings.integration_host, settings.integration_port), family=family
    )
    server = IntegrationServer(
        uvicorn.Config(
            integration_app(auth),
            host=settings.integration_host,
            port=settings.integration_port,
            lifespan="off",
            log_config=None,
            proxy_headers=False,
            timeout_graceful_shutdown=2,
        )
    )
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(10):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("The integration server stopped during startup.")
                await asyncio.sleep(0.01)
        yield server
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5)
        except TimeoutError:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        finally:
            listener.close()
