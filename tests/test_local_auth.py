from __future__ import annotations

import json
import time
from urllib.parse import urlsplit

import jwt
import pytest
from fastapi.testclient import TestClient

from aespa import local_auth
from aespa.config import Settings
from aespa.main import create_app


def app_for(tmp_path, **updates):
    return create_app(
        Settings(
            _env_file=None, data_dir=tmp_path, allowed_hosts=["testserver"], **updates
        )
    )


def login(client, app):
    response = client.post("/api/auth/login", json={"key": app.state.auth.key})
    assert response.status_code == 200
    client.headers["X-AESPA-CSRF"] = response.json()["csrf_token"]
    return response


def test_management_requires_session_and_key_is_explicit(tmp_path):
    app = app_for(tmp_path)
    client = TestClient(app)
    assert client.get("/api/auth/session").json()["authenticated"] is False
    assert client.get("/api/sites").status_code == 401
    assert client.get("/api/auth/key").status_code == 401
    assert client.post("/api/auth/login", json={"key": "wrong"}).status_code == 401
    response = login(client, app)
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert "Max-Age=2592000" in response.headers["set-cookie"]
    assert client.get("/api/auth/key").json() == {"key": app.state.auth.key}
    assert client.get("/api/auth/key").headers["cache-control"] == "no-store"
    assert client.get("/api/sites").status_code == 200


def test_sessions_survive_restart_and_are_instance_and_port_bound(tmp_path):
    app = app_for(tmp_path / "one")
    client = TestClient(app)
    login(client, app)
    local_auth._AUTH.clear()
    restarted = app_for(tmp_path / "one")
    new_client = TestClient(restarted, cookies=client.cookies)
    assert new_client.get("/api/auth/session").json()["authenticated"] is True
    other = TestClient(app_for(tmp_path / "two"), cookies=client.cookies)
    assert other.get("/api/auth/session").json()["authenticated"] is False
    other_port = TestClient(
        app_for(tmp_path / "one", port=9000), cookies=client.cookies
    )
    assert other_port.get("/api/auth/session").json()["authenticated"] is False


def test_rotating_key_replaces_live_credentials_and_persists(tmp_path):
    app = app_for(tmp_path / "data")
    client = TestClient(app)
    old_key = app.state.auth.key
    login(client, app)
    old_cookie_name = app.state.auth.cookie_name
    old_cookie = client.cookies.get(old_cookie_name)
    other_port = app_for(tmp_path / "data", port=9000)
    old_ticket = urlsplit(app.state.auth.login_url("http://testserver")).fragment.split(
        "=", 1
    )[1]

    new_key = app.state.auth.rotate_key()

    assert new_key != old_key
    assert app.state.auth.key == new_key
    assert other_port.state.auth.key == new_key
    assert client.get("/api/auth/session").json()["authenticated"] is False
    assert (
        client.post("/api/auth/exchange", json={"token": old_ticket}).status_code == 401
    )
    assert client.post("/api/auth/login", json={"key": old_key}).status_code == 401
    assert client.post("/api/auth/login", json={"key": new_key}).status_code == 200
    assert (
        TestClient(app, cookies={old_cookie_name: old_cookie})
        .get("/api/auth/key")
        .status_code
        == 401
    )

    local_auth._AUTH.clear()
    restarted = app_for(tmp_path / "data")
    assert restarted.state.auth.key == new_key
    assert (
        TestClient(restarted).post("/api/auth/login", json={"key": new_key}).status_code
        == 200
    )


def test_managed_key_file_cannot_be_rotated_from_console(tmp_path):
    key_file = tmp_path / "key"
    key_file.write_text("a" * 40)
    app = app_for(tmp_path / "data", auth_key_file=key_file)

    with pytest.raises(ValueError, match="AESPA_AUTH_KEY_FILE"):
        app.state.auth.rotate_key()

    assert key_file.read_text() == "a" * 40
    assert app.state.auth.key == "a" * 40


def test_failed_key_rotation_keeps_current_key(tmp_path, monkeypatch):
    app = app_for(tmp_path / "data")
    old_key = app.state.auth.key

    def fail_replace(_source, _destination):
        raise OSError("disk unavailable")

    monkeypatch.setattr(local_auth.os, "replace", fail_replace)
    with pytest.raises(OSError, match="disk unavailable"):
        app.state.auth.rotate_key()

    assert app.state.auth.key == old_key
    local_auth._AUTH.clear()
    assert app_for(tmp_path / "data").state.auth.key == old_key


def test_csrf_origin_host_and_logout(tmp_path):
    app = app_for(tmp_path)
    client = TestClient(app)
    login(client, app)
    assert (
        client.post("/api/auth/logout", headers={"X-AESPA-CSRF": ""}).status_code == 403
    )
    assert (
        client.post(
            "/api/auth/logout", headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert (
        client.get("/api/auth/key", headers={"Host": "evil.example"}).status_code == 400
    )
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/key").status_code == 401


def test_cross_site_navigation_loads_page_but_other_requests_are_refused(tmp_path):
    app = app_for(tmp_path)
    client = TestClient(app)
    login(client, app)
    cross_site = {"Sec-Fetch-Site": "cross-site"}
    navigate = {**cross_site, "Sec-Fetch-Mode": "navigate"}
    assert client.get("/", headers=navigate).status_code != 403
    assert client.get("/api/auth/key", headers=navigate).status_code == 200
    cors = {**cross_site, "Sec-Fetch-Mode": "cors"}
    assert client.get("/api/auth/key", headers=cors).status_code == 403
    assert client.post("/api/auth/logout", headers=navigate).status_code == 403


def test_automatic_login_ticket_is_single_use_and_expires(tmp_path, monkeypatch):
    app = app_for(tmp_path)
    auth = app.state.auth
    client = TestClient(app)
    token = urlsplit(auth.login_url("http://testserver")).fragment.split("=", 1)[1]
    assert client.post("/api/auth/exchange", json={"token": token}).status_code == 200
    assert client.post("/api/auth/exchange", json={"token": token}).status_code == 401
    token = urlsplit(auth.login_url("http://testserver")).fragment.split("=", 1)[1]
    auth._tickets[token] = 0
    assert client.post("/api/auth/exchange", json={"token": token}).status_code == 401


def test_key_file_changes_invalidate_sessions_and_expired_sessions_fail(tmp_path):
    key_file = tmp_path / "key"
    key_file.write_text("a" * 40)
    app = app_for(tmp_path / "data", auth_key_file=key_file)
    client = TestClient(app)
    login(client, app)
    key_file.write_text("b" * 40)
    changed = TestClient(
        app_for(tmp_path / "data", auth_key_file=key_file), cookies=client.cookies
    )
    assert changed.get("/api/auth/key").status_code == 401
    auth = app.state.auth
    expired = jwt.encode(
        {"exp": 1, "aud": auth.identity, "nonce": "expired"},
        auth.secret,
        algorithm="HS256",
    )
    client.cookies.set(auth.cookie_name, expired)
    assert client.get("/api/auth/key").status_code == 401


def test_signin_is_rate_limited(tmp_path):
    client = TestClient(app_for(tmp_path))
    for _ in range(10):
        assert client.post("/api/auth/login", json={"key": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"key": "wrong"}).status_code == 429


def test_successful_signins_do_not_use_failed_attempt_limit(tmp_path):
    app = app_for(tmp_path)
    client = TestClient(app)
    for _ in range(15):
        response = client.post("/api/auth/login", json={"key": app.state.auth.key})
        assert response.status_code == 200


def test_websocket_requires_management_session(tmp_path):
    client = TestClient(app_for(tmp_path))
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/api/events"):
            pass
    assert error.value.code == 1008


def test_integration_exemption_is_precise(tmp_path, monkeypatch):
    app = app_for(tmp_path)
    from aespa.extensions.api import ExtensionApiDispatcher

    seen = []

    async def dispatch(self, scope, receive, send):
        from starlette.responses import JSONResponse

        seen.append(scope["path"])
        await JSONResponse({"detail": "Bearer token required"}, status_code=401)(
            scope, receive, send
        )

    monkeypatch.setattr(ExtensionApiDispatcher, "__call__", dispatch)
    client = TestClient(app)
    response = client.get("/extension/aespa.api/v1/sites")
    assert response.json()["detail"] == "Bearer token required"
    assert seen
    for path in [
        "/extension/aespa.api/admin/tokens",
        "/extension/other/v1/sites",
        "/extension/aespa.api/v1-admin",
    ]:
        assert (
            client.get(path).json()["detail"]
            == "Sign in with your AESPA authentication key."
        )


TEAM = "aespa-team.cloudflareaccess.com"
AUD = "staging-app-aud"


@pytest.fixture
def access_signer(monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import rsa

    from aespa import cloudflare_access

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk["kid"] = "k1"
    monkeypatch.setattr(cloudflare_access, "_get_jwks", lambda _issuer: {"keys": [jwk]})

    def sign(aud=AUD, iss=f"https://{TEAM}", expires_in=300):
        claims = {"aud": [aud], "iss": iss, "email": "dev@example.com"}
        claims["exp"] = int(time.time()) + expires_in
        token = jwt.encode(
            claims, private_key, algorithm="RS256", headers={"kid": "k1"}
        )
        return {"Cf-Access-Jwt-Assertion": token}

    return sign


def test_cloudflare_access_login_signs_in_without_key(tmp_path, access_signer):
    app = app_for(
        tmp_path, cloudflare_access_team_domain=TEAM, cloudflare_access_aud=AUD
    )
    client = TestClient(app)
    assert client.get("/api/sites").status_code == 401
    session = client.get("/api/auth/session", headers=access_signer()).json()
    assert session["authenticated"] is True
    assert client.get("/api/sites").status_code == 200
    client.headers["X-AESPA-CSRF"] = session["csrf_token"]
    assert client.post("/api/auth/logout").status_code == 200


@pytest.mark.parametrize(
    "token_args",
    [
        {"aud": "another-app"},
        {"iss": "https://other-team.cloudflareaccess.com"},
        {"expires_in": -60},
    ],
)
def test_cloudflare_access_rejects_other_apps_and_expired_tokens(
    tmp_path, access_signer, token_args
):
    app = app_for(
        tmp_path, cloudflare_access_team_domain=TEAM, cloudflare_access_aud=AUD
    )
    client = TestClient(app)
    headers = access_signer(**token_args)
    assert (
        client.get("/api/auth/session", headers=headers).json()["authenticated"]
        is False
    )
    assert client.get("/api/sites").status_code == 401


@pytest.mark.parametrize(
    "updates",
    [{}, {"cloudflare_access_team_domain": TEAM}, {"cloudflare_access_aud": AUD}],
)
def test_cloudflare_access_signin_needs_team_and_aud(tmp_path, access_signer, updates):
    client = TestClient(app_for(tmp_path, **updates))
    session = client.get("/api/auth/session", headers=access_signer()).json()
    assert session["authenticated"] is False
