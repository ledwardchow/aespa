from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import tempfile
import threading
import time
from collections import OrderedDict, deque
from urllib.parse import urlsplit

import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.datastructures import Headers
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse

from aespa.config import Settings

SESSION_SECONDS = 30 * 24 * 60 * 60
NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
INTEGRATION_PREFIX = "/extension/aespa.api/v1"
PUBLIC_AUTH = {"/api/auth/session", "/api/auth/login", "/api/auth/exchange"}


class AuthManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        state_file = settings.data_dir / "auth.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        if not state_file.exists():
            fd, temporary = tempfile.mkstemp(dir=state_file.parent, prefix=".auth-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump(
                        {
                            "key": secrets.token_urlsafe(32),
                            "secret": secrets.token_urlsafe(48),
                        },
                        stream,
                    )
                try:
                    os.link(temporary, state_file)
                except FileExistsError:
                    pass
            finally:
                os.unlink(temporary)
        if os.name != "nt":
            state_file.chmod(0o600)
        state = json.loads(state_file.read_text(encoding="utf-8"))
        self.key = (
            settings.auth_key_file.read_text(encoding="utf-8").strip()
            if settings.auth_key_file
            else state["key"]
        )
        if len(self.key) < 32:
            raise ValueError(
                "The authentication key must contain at least 32 characters."
            )
        self.secret = hmac.new(
            state["secret"].encode(), self.key.encode(), hashlib.sha256
        ).hexdigest()
        self.identity = hashlib.sha256(
            f"{self.secret}:{settings.port}".encode()
        ).hexdigest()[:24]
        self.cookie_name = f"aespa_session_{self.identity}"
        self._tickets: dict[str, float] = {}
        self._failures: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def login_url(self, base_url: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            now = time.time()
            self._tickets = {k: v for k, v in self._tickets.items() if v > now}
            self._tickets[token] = now + 120
        return f"{base_url.rstrip('/')}/#aespa-login={token}"

    def consume_ticket(self, token: str) -> bool:
        with self._lock:
            return self._tickets.pop(token, 0) > time.time()

    def session(self) -> str:
        return jwt.encode(
            {
                "aud": self.identity,
                "exp": int(time.time()) + SESSION_SECONDS,
                "nonce": secrets.token_urlsafe(32),
            },
            self.secret,
            algorithm="HS256",
        )

    def valid_session(self, token: str | None) -> bool:
        if not token:
            return False
        try:
            jwt.decode(
                token,
                self.secret,
                algorithms=["HS256"],
                audience=self.identity,
                options={"require": ["exp", "aud", "nonce"]},
            )
            return True
        except jwt.PyJWTError:
            return False

    def csrf_token(self, session: str) -> str:
        return hmac.new(
            self.secret.encode(), session.encode(), hashlib.sha256
        ).hexdigest()

    def check_attempt(self, client: str, *, failed: bool = False) -> None:
        with self._lock:
            now = time.time()
            attempts = self._failures.setdefault(client, deque())
            self._failures.move_to_end(client)
            while attempts and attempts[0] < now - 60:
                attempts.popleft()
            if len(attempts) >= 10:
                raise HTTPException(
                    429, "Too many sign-in attempts. Try again in a minute."
                )
            if failed:
                attempts.append(now)
            while len(self._failures) > 1024:
                self._failures.popitem(last=False)


_AUTH: dict[tuple, AuthManager] = {}
_AUTH_LOCK = threading.Lock()


def get_auth(settings: Settings) -> AuthManager:
    key_file = settings.auth_key_file
    key_version = key_file.read_bytes() if key_file else b""
    key = (
        settings.data_dir.resolve(),
        settings.port,
        key_file,
        key_version,
        tuple(settings.allowed_hosts),
        settings.auth_cookie_secure,
    )
    with _AUTH_LOCK:
        if key not in _AUTH:
            _AUTH[key] = AuthManager(settings)
        return _AUTH[key]


class LocalAuthMiddleware:
    def __init__(self, app, auth: AuthManager):
        self.app = app
        self.auth = auth

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)
        connection = HTTPConnection(scope)
        headers = Headers(scope=scope)
        try:
            host = urlsplit(f"//{headers.get('host', '')}").hostname
        except ValueError:
            host = None
        allowed = {"localhost", "127.0.0.1", "::1", *self.auth.settings.allowed_hosts}
        status, detail = 0, ""
        if host not in allowed:
            status, detail = 400, "This hostname is not allowed."
        path = scope["path"]
        integration = path == INTEGRATION_PREFIX or path.startswith(
            INTEGRATION_PREFIX + "/"
        )
        origin = headers.get("origin")
        if not integration and not status:
            scheme = {"ws": "http", "wss": "https"}.get(
                connection.url.scheme, connection.url.scheme
            )
            expected_origin = f"{scheme}://{connection.url.netloc}"
            if origin and origin.rstrip("/") != expected_origin:
                status, detail = 403, "Cross-site requests are not allowed."
            if headers.get("sec-fetch-site") == "cross-site":
                status, detail = 403, "Cross-site requests are not allowed."
        protected = (
            (
                path in {"/api", "/extension", "/docs", "/redoc", "/openapi.json"}
                or path.startswith(("/api/", "/extension/", "/docs/"))
                or scope["type"] == "websocket"
            )
            and path not in PUBLIC_AUTH
            and path != "/api/health"
            and not integration
        )
        token = connection.cookies.get(self.auth.cookie_name)
        if protected and not status:
            if not self.auth.valid_session(token):
                status, detail = 401, "Sign in with your AESPA authentication key."
            elif scope["type"] == "http" and scope["method"] not in {
                "GET",
                "HEAD",
                "OPTIONS",
            }:
                csrf = headers.get("x-aespa-csrf", "")
                if not hmac.compare_digest(
                    csrf.encode(), self.auth.csrf_token(token).encode()
                ):
                    status, detail = 403, "Refresh AESPA and try again."
        if status:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                await JSONResponse(
                    {"detail": detail}, status_code=status, headers=NO_STORE
                )(scope, receive, send)
            return
        await self.app(scope, receive, send)


class LoginInput(BaseModel):
    key: str = Field(max_length=1024)


class ExchangeInput(BaseModel):
    token: str = Field(max_length=1024)


def auth_router(auth: AuthManager) -> APIRouter:
    router = APIRouter(prefix="/api/auth", include_in_schema=False)

    def session_response(token: str, request: Request):
        response = JSONResponse(
            {"authenticated": True, "csrf_token": auth.csrf_token(token)},
            headers=NO_STORE,
        )
        response.set_cookie(
            auth.cookie_name,
            token,
            max_age=SESSION_SECONDS,
            httponly=True,
            samesite="strict",
            secure=auth.settings.auth_cookie_secure or request.url.scheme == "https",
        )
        return response

    @router.get("/session")
    def session(request: Request):
        token = request.cookies.get(auth.cookie_name)
        authenticated = auth.valid_session(token)
        return JSONResponse(
            {
                "authenticated": authenticated,
                "csrf_token": auth.csrf_token(token) if authenticated else None,
            },
            headers=NO_STORE,
        )

    @router.post("/login")
    def login(payload: LoginInput, request: Request):
        client = request.client.host if request.client else "unknown"
        auth.check_attempt(client)
        if not hmac.compare_digest(payload.key.encode(), auth.key.encode()):
            auth.check_attempt(client, failed=True)
            raise HTTPException(
                401, "The authentication key is not correct.", headers=NO_STORE
            )
        return session_response(auth.session(), request)

    @router.post("/exchange")
    def exchange(payload: ExchangeInput, request: Request):
        client = request.client.host if request.client else "unknown"
        auth.check_attempt(client)
        if not auth.consume_ticket(payload.token):
            auth.check_attempt(client, failed=True)
            raise HTTPException(
                401,
                "This sign-in link has expired or has already been used.",
                headers=NO_STORE,
            )
        return session_response(auth.session(), request)

    @router.get("/key")
    def key():
        return JSONResponse({"key": auth.key}, headers=NO_STORE)

    @router.post("/logout")
    def logout():
        response = JSONResponse({"authenticated": False}, headers=NO_STORE)
        response.delete_cookie(auth.cookie_name)
        return response

    return router
