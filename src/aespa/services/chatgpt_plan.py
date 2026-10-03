"""Sign in with ChatGPT for locally hosted, open-source installations."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import secrets
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
import jwt

AUTH_URL = "https://auth.openai.com/api/accounts/authorize"
TOKEN_URL = "https://auth.openai.com/api/accounts/oauth/token"
JWKS_URL = "https://auth.openai.com/.well-known/jwks.json"
ISSUER = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
_lock = asyncio.Lock()
_pending: dict[str, dict[str, Any]] = {}
_access_check_lock = asyncio.Lock()
_access_checks: dict[str, tuple[float, dict[str, Any]]] = {}

_ACCESS_CHECK_MODELS = (
    "gpt-6-sol",
    "gpt-6.1-sol",
    "gpt-6-luna",
    "gpt-daybreak-blue-latest",
    "gpt-daybreak-red-latest",
    "gpt-5.6-cyber",
)


def _lock_fd(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX)


def _unlock_fd(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)


@asynccontextmanager
async def _credential_lock():
    path = _storage_path().with_suffix(".lock")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    acquired = False
    try:
        await asyncio.to_thread(_lock_fd, fd)
        acquired = True
        yield
    finally:
        if acquired:
            _unlock_fd(fd)
        os.close(fd)


def _storage_path() -> Path:
    root = Path(os.environ.get("APPDATA") or Path.home() / ".config")
    return root / "aespa" / "chatgpt-plan.json"


def _read() -> dict[str, Any]:
    path = _storage_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"host_id": f"urn:uuid:{uuid.uuid4()}", "active": None, "accounts": {}}


def _write(data: dict[str, Any]) -> None:
    path = _storage_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd, temp_name = tempfile.mkstemp(prefix=".chatgpt-plan-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def status() -> dict[str, Any]:
    data = _read()
    active = data.get("active")
    accounts = data.get("accounts", {})
    return {
        "active": active,
        "accounts": [
            {
                "client_id": client_id,
                "email": account.get("email"),
                "signed_in": bool(account.get("refresh_token")),
                "active": client_id == active,
            }
            for client_id, account in accounts.items()
        ],
    }


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


async def start_login(client_id: str | None = None) -> dict[str, str]:
    async with _lock:
        async with _credential_lock():
            data = _read()
            if client_id and client_id not in data["accounts"]:
                raise ValueError("Saved ChatGPT account was not found")
            _write(data)  # Persist the host ID before opening the browser.
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        login_id = secrets.token_urlsafe(24)

        async def callback(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=15)
                if len(line) > 8192:
                    raise ValueError("Invalid callback")
                method, target, _ = line.decode("ascii").split(" ", 2)
                if method != "GET" or urlsplit(target).path != "/auth/callback":
                    raise ValueError("Invalid callback")
                params = parse_qs(urlsplit(target).query)
                if params.get("state", [None])[0] != state:
                    raise ValueError("Sign-in could not be verified")
                attempt = _pending.get(login_id)
                if (
                    not attempt
                    or attempt["status"] != "pending"
                    or time.time() > attempt["expires_at"]
                ):
                    raise ValueError("Sign-in expired")
                attempt["status"] = "processing"
                if params.get("error"):
                    raise ValueError("ChatGPT sign-in was cancelled")
                code = params.get("code", [None])[0]
                issued_id = params.get("client_id", [None])[0]
                if client_id and issued_id and issued_id != client_id:
                    raise ValueError(
                        "ChatGPT returned a different account registration"
                    )
                issued_id = client_id or issued_id
                if not code or not issued_id or issued_id == "dynamic_agent_client":
                    raise ValueError("ChatGPT did not complete registration")
                async with httpx.AsyncClient(timeout=20) as http:
                    response = await http.post(
                        TOKEN_URL,
                        data={
                            "grant_type": "authorization_code",
                            "code": code,
                            "client_id": issued_id,
                            "code_verifier": verifier,
                            "redirect_uri": attempt["redirect_uri"],
                            "resource": RESOURCE,
                        },
                    )
                    response.raise_for_status()
                    tokens = response.json()
                    claims = await _validate_id_token(
                        http, tokens["id_token"], issued_id, nonce
                    )
                scopes = set(tokens.get("scope", "").split())
                if "chatgpt.tokens.use.direct" not in scopes:
                    raise ValueError("ChatGPT plan usage was not granted")
                async with _lock:
                    async with _credential_lock():
                        stored = _read()
                        old = stored["accounts"].get(issued_id)
                        if old and old.get("subject") != claims["sub"]:
                            raise ValueError("A different ChatGPT account was selected")
                        stored["accounts"][issued_id] = {
                            "subject": claims["sub"],
                            "email": claims.get("email"),
                            "id_token": tokens["id_token"],
                            "access_token": tokens["access_token"],
                            "refresh_token": tokens["refresh_token"],
                            "expires_at": time.time()
                            + int(tokens.get("expires_in", 3600)),
                            "scopes": sorted(scopes),
                        }
                        stored["active"] = issued_id
                        _write(stored)
                        _access_checks.pop(issued_id, None)
                attempt["status"] = "complete"
            except Exception as exc:
                if login_id in _pending:
                    _pending[login_id]["status"] = "error"
                    _pending[login_id]["error"] = str(exc)[:200]
            finally:
                outcome = _pending.get(login_id, {}).get("status")
                body = (
                    "ChatGPT connected. You can close this window."
                    if outcome == "complete"
                    else "ChatGPT sign-in failed. Return to AESPA for details."
                )
                payload = body.encode("utf-8")
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\n"
                    + f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n".encode()
                    + payload
                )
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                if login_id in _pending:
                    _pending[login_id]["server"].close()

        server = await asyncio.start_server(callback, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        redirect_uri = f"http://127.0.0.1:{port}/auth/callback"
        _pending[login_id] = {
            "server": server,
            "redirect_uri": redirect_uri,
            "expires_at": time.time() + 600,
            "status": "pending",
        }

        async def expire() -> None:
            await asyncio.sleep(600)
            attempt = _pending.get(login_id)
            if attempt and attempt["status"] == "pending":
                attempt["status"] = "error"
                attempt["error"] = "Sign-in expired"
                server.close()

        asyncio.create_task(expire())
        args = {
            "client_id": client_id or "dynamic_agent_client",
            "ext_agent_host_id": data["host_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "resource": RESOURCE,
            "state": state,
            "nonce": nonce,
            "code_challenge_method": "S256",
            "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
        }
        if client_id:
            old = data["accounts"][client_id]
            if old.get("id_token"):
                args["id_token_hint"] = old["id_token"]
        else:
            args["agent_name_hint"] = "AESPA"
        return {"login_id": login_id, "url": f"{AUTH_URL}?{urlencode(args)}"}


async def _validate_id_token(
    http: httpx.AsyncClient, token: str, client_id: str, nonce: str
) -> dict[str, Any]:
    header = jwt.get_unverified_header(token)
    if header.get("alg") != "RS256":
        raise ValueError("Unexpected ChatGPT token signature")
    response = await http.get(JWKS_URL)
    response.raise_for_status()
    jwk = next(
        (
            key
            for key in response.json().get("keys", [])
            if key.get("kid") == header.get("kid")
        ),
        None,
    )
    if jwk is None:
        raise ValueError("ChatGPT token signing key was not found")
    claims = jwt.decode(
        token,
        jwt.algorithms.RSAAlgorithm.from_jwk(jwk),
        algorithms=["RS256"],
        audience=client_id,
        issuer=ISSUER,
        options={"require": ["sub", "exp", "iat", "iss", "aud"]},
    )
    if claims.get("nonce") != nonce:
        raise ValueError("ChatGPT token nonce did not match")
    return claims


def login_status(login_id: str) -> dict[str, str]:
    attempt = _pending.get(login_id)
    if attempt is None:
        raise KeyError(login_id)
    if attempt["status"] == "pending" and time.time() > attempt["expires_at"]:
        attempt["status"] = "error"
        attempt["error"] = "Sign-in expired"
        attempt["server"].close()
    return {"status": attempt["status"], "error": attempt.get("error", "")}


async def access_token(client_id: str | None = None) -> str:
    async with _lock:
        async with _credential_lock():
            data = _read()
            client_id = client_id or data.get("active")
            account = data.get("accounts", {}).get(client_id) if client_id else None
            if not account or not account.get("refresh_token"):
                raise RuntimeError(
                    "Sign in with ChatGPT in LLM settings before starting a scan"
                )
            if account.get("expires_at", 0) > time.time() + 120:
                return account["access_token"]
            async with httpx.AsyncClient(timeout=20) as http:
                response = await http.post(
                    TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": client_id,
                        "refresh_token": account["refresh_token"],
                        "resource": RESOURCE,
                    },
                )
                response.raise_for_status()
                tokens = response.json()
            scopes = set(tokens.get("scope", "").split()) or set(
                account.get("scopes", [])
            )
            if "chatgpt.tokens.use.direct" not in scopes:
                raise RuntimeError("ChatGPT plan permission is no longer available")
            account.update(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                expires_at=time.time() + int(tokens.get("expires_in", 3600)),
                scopes=sorted(scopes),
            )
            _write(data)
            return account["access_token"]


async def discover_models(client_id: str | None = None) -> list[str]:
    token = await access_token(client_id)
    async with httpx.AsyncClient(timeout=20) as http:
        response = await http.get(
            f"{RESOURCE}/models", headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        rows = response.json().get("models", [])
    return [
        str(row["slug"])
        for row in rows
        if row.get("visibility") == "list" and row.get("slug")
    ]


async def _probe_model(
    http: httpx.AsyncClient, token: str, model: str
) -> dict[str, Any]:
    """Make a minimal stateless turn because the catalog can omit usable models."""
    async with http.stream(
        "POST",
        f"{RESOURCE}/responses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "model": model,
            "input": [{"role": "user", "content": "Reply OK."}],
            "store": False,
            "stream": True,
        },
    ) as response:
        if response.status_code in {400, 403, 404}:
            try:
                body = json.loads(await response.aread())
            except ValueError:
                body = {}
            error = body.get("error") or {}
            code = error.get("code") if isinstance(error, dict) else None
            if code in {
                "subscription_sharing_usage_limit_exceeded",
                "subscription_sharing_usage_unavailable",
            }:
                raise RuntimeError("ChatGPT plan usage is unavailable")
            return {"available": False, "cyber": None}
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:])
            except ValueError:
                continue
            if event.get("type") == "response.completed":
                completed = event.get("response") or {}
                programs = completed.get("access_programs") or {}
                return {
                    "available": True,
                    "cyber": programs.get("cyber")
                    or (
                        "daybreak_blue"
                        if model == "gpt-daybreak-blue-latest"
                        else "daybreak_red"
                        if model == "gpt-daybreak-red-latest"
                        else None
                    ),
                }
            if event.get("type") == "response.failed":
                error = (event.get("response") or {}).get("error") or {}
                code = error.get("code") if isinstance(error, dict) else None
                if code in {
                    "model_not_found",
                    "model_access_denied",
                    "access_program_not_enabled",
                }:
                    return {"available": False, "cyber": None}
                raise RuntimeError(
                    f"ChatGPT model check failed: {code or 'unknown_error'}"
                )
            if event.get("type") == "response.incomplete":
                raise RuntimeError("ChatGPT model check was incomplete")
    raise RuntimeError("ChatGPT model check ended early")


async def check_access(client_id: str, *, force: bool = False) -> dict[str, Any]:
    """Verify model and Daybreak access with completed Responses turns."""
    if not client_id:
        raise ValueError("Select a signed-in ChatGPT account")
    async with _access_check_lock:
        cached = _access_checks.get(client_id)
        if cached and not force and cached[0] > time.time():
            return cached[1]
        token = await access_token(client_id)
        async with httpx.AsyncClient(timeout=30) as http:
            limit = asyncio.Semaphore(2)

            async def check(model: str) -> dict[str, Any]:
                async with limit:
                    return await _probe_model(http, token, model)

            results = await asyncio.gather(
                *(check(model) for model in _ACCESS_CHECK_MODELS)
            )
        checked = dict(zip(_ACCESS_CHECK_MODELS, results, strict=True))
        output = {
            "client_id": client_id,
            "models": [
                model for model, result in checked.items() if result["available"]
            ],
            "daybreak": {
                "blue": any(
                    result["available"] and result["cyber"] == "daybreak_blue"
                    for result in results
                ),
                "red": any(
                    result["available"] and result["cyber"] == "daybreak_red"
                    for result in results
                ),
            },
        }
        _access_checks[client_id] = (time.time() + 900, output)
        return output


async def daybreak_program(client_id: str, model: str) -> str | None:
    """Choose an approved cyber program for the requested model."""
    access = await check_access(client_id)
    daybreak = access["daybreak"]
    if model in {"gpt-daybreak-red-latest", "gpt-5.6-cyber"}:
        return "daybreak_red" if daybreak["red"] else None
    if model in {"gpt-6-astra", "gpt-6.1-sol"}:
        return "daybreak_blue" if daybreak["red"] else None
    if model in {"gpt-6-sol", "gpt-6-luna", "gpt-daybreak-blue-latest"}:
        return "daybreak_blue" if daybreak["blue"] else None
    return None


async def select_account(client_id: str) -> None:
    async with _lock:
        async with _credential_lock():
            data = _read()
            if client_id not in data["accounts"]:
                raise ValueError("Saved ChatGPT account was not found")
            data["active"] = client_id
            _write(data)


async def sign_out(client_id: str) -> None:
    async with _lock:
        async with _credential_lock():
            data = _read()
            account = data["accounts"].get(client_id)
            if not account:
                raise ValueError("Saved ChatGPT account was not found")
            refresh_token = account.get("refresh_token")
            if refresh_token:
                async with httpx.AsyncClient(timeout=20) as http:
                    discovery = await http.get(
                        f"{ISSUER}/.well-known/openid-configuration"
                    )
                    discovery.raise_for_status()
                    endpoint = discovery.json()["revocation_endpoint"]
                    if not endpoint.startswith(f"{ISSUER}/"):
                        raise ValueError("Unexpected ChatGPT revocation endpoint")
                    response = await http.post(
                        endpoint,
                        data={
                            "token": refresh_token,
                            "token_type_hint": "refresh_token",
                            "client_id": client_id,
                        },
                    )
                    response.raise_for_status()
            for key in ("access_token", "refresh_token", "id_token", "expires_at"):
                account.pop(key, None)
            if data.get("active") == client_id:
                data["active"] = None
            _write(data)
            _access_checks.pop(client_id, None)
