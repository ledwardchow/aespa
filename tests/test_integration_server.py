from __future__ import annotations

import socket

import httpx
import pytest
from fastapi.testclient import TestClient

from aespa.config import Settings
from aespa.integration_server import integration_app, integration_listener
from aespa.local_auth import AuthManager


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_listener_has_only_integration_routes_and_checks_hosts(tmp_path, monkeypatch):
    from starlette.responses import JSONResponse

    from aespa.extensions.api import ExtensionApiDispatcher

    seen = []

    async def dispatch(self, scope, receive, send):
        seen.append(scope["path"])
        await JSONResponse({"bearer": "required"}, status_code=401)(
            scope, receive, send
        )

    monkeypatch.setattr(ExtensionApiDispatcher, "__call__", dispatch)
    auth = AuthManager(
        Settings(_env_file=None, data_dir=tmp_path, allowed_hosts=["testserver"])
    )
    client = TestClient(integration_app(auth))
    assert client.get("/extension/aespa.api/v1/sites").json() == {"bearer": "required"}
    assert seen == ["/extension/aespa.api/v1/sites"]
    for path in [
        "/",
        "/api/health",
        "/api/sites",
        "/api/auth/login",
        "/extension/aespa.api/admin/tokens",
        "/extension/other/v1/sites",
    ]:
        assert client.get(path).status_code == 404
    assert (
        client.get(
            "/extension/aespa.api/v1/sites", headers={"Host": "evil.example"}
        ).status_code
        == 400
    )


@pytest.mark.anyio
async def test_listener_is_disabled_inside_docker(tmp_path, monkeypatch):
    settings = Settings(
        _env_file=None, data_dir=tmp_path, integration_port=9001, running_in_docker=True
    )

    def no_socket(*args, **kwargs):
        raise AssertionError("Docker must not start an integration listener")

    monkeypatch.setattr(socket, "create_server", no_socket)
    async with integration_listener(settings, AuthManager(settings)) as server:
        assert server is None


@pytest.mark.anyio
async def test_listener_binds_stops_and_fails_if_port_is_busy(tmp_path, monkeypatch):
    monkeypatch.setattr("aespa.integration_server.running_in_docker", lambda _: False)
    with socket.create_server(("127.0.0.1", 0)) as reservation:
        port = reservation.getsockname()[1]
    settings = Settings(_env_file=None, data_dir=tmp_path, integration_port=port)
    auth = AuthManager(settings)
    async with integration_listener(settings, auth) as server:
        assert server.started
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://127.0.0.1:{port}/")
            assert response.status_code == 404
        with pytest.raises(OSError):
            async with integration_listener(settings, auth):
                pass
    with socket.create_server(("127.0.0.1", port)):
        pass
