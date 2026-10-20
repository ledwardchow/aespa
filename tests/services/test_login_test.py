from __future__ import annotations

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import pytest
from sqlmodel import Session

from aespa.db import get_engine
from aespa.models import Credential, Site
from aespa.schemas import CredentialIn
from aespa.services import login_test

LOGIN_FORM = """<!doctype html><title>Login</title>
<form method="post" action="/login">
  {error}
  <label>Email <input name="email" type="email"></label>
  <label>Password <input name="password" type="password"></label>
  <button type="submit">Log in</button>
</form>"""


class _LoginHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _send(self, body: str, status: int = 200, headers: dict | None = None):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/home"):
            self._send("<!doctype html><title>Home</title><h1>Welcome back</h1>")
        else:
            self._send(LOGIN_FORM.format(error=""))

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        form = parse_qs(self.rfile.read(length).decode())
        if form.get("email") == ["admin@test.local"] and form.get("password") == [
            "right"
        ]:
            self._send("", 303, {"Location": "/home"})
        else:
            error = '<div role="alert">Invalid email or password.</div>'
            self._send(LOGIN_FORM.format(error=error))


@pytest.fixture
def login_site():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _LoginHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _credential(password: str, **kw) -> CredentialIn:
    return CredentialIn(
        login_fields=[
            {"key": "email", "label": "Email", "value": "admin@test.local"},
            {
                "key": "password",
                "label": "Password",
                "value": password,
                "sensitive": True,
            },
        ],
        **kw,
    )


def _run(base_url: str, password: str):
    try:
        return asyncio.run(
            login_test.run_login_test(
                base_url=base_url,
                login_url=f"{base_url}/login",
                credential=_credential(password),
            )
        )
    except Exception as exc:  # pragma: no cover - depends on local browser setup
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Playwright Chromium is not installed")
        raise


def test_login_test_reports_a_working_login(login_site):
    result = _run(login_site, "right")

    assert result.status == "logged_in"
    assert result.final_url == f"{login_site}/home"
    assert result.page_message is None
    assert result.screenshot.startswith("data:image/jpeg;base64,")


def test_login_test_reports_the_page_error_for_a_wrong_password(login_site):
    result = _run(login_site, "wrong")

    assert result.status == "failed"
    assert result.message == "Still on the login page."
    assert result.page_message == "Invalid email or password."
    assert result.screenshot


def test_login_test_uses_the_saved_totp_seed_only_for_the_same_site():
    with Session(get_engine()) as s:
        site = Site(name="A", base_url="http://a.test")
        other = Site(name="B", base_url="http://b.test")
        s.add_all([site, other])
        s.commit()
        cred = Credential(
            site_id=site.id,
            username="u",
            password="p",
            auth_mode="totp",
            totp_seed="JBSWY3DPEHPK3PXP",
        )
        s.add(cred)
        s.commit()
        cred_id, site_id, other_id = cred.id, site.id, other.id

    form = _credential("p", id=cred_id, auth_mode="totp")
    assert (
        login_test._credential_for_test(form, site_id).totp_seed == "JBSWY3DPEHPK3PXP"
    )
    assert login_test._credential_for_test(form, other_id).totp_seed is None
    typed = _credential("p", id=cred_id, auth_mode="totp", totp_seed="NEWSEED")
    assert login_test._credential_for_test(typed, site_id).totp_seed == "NEWSEED"


def test_login_test_endpoint_rejects_guided_login(client):
    response = client.post(
        "/api/sites/login-test",
        json={
            "base_url": "http://target.test",
            "credential": {
                "auth_mode": "guided",
                "login_fields": [{"key": "username", "label": "Username", "value": "u"}],
            },
        },
    )

    assert response.status_code == 400
    assert "when a crawl starts" in response.json()["detail"]
