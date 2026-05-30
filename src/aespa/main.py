from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import jwt
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from aespa.api.events import router as events_router
from aespa.api.reporting_debug import router as reporting_debug_router
from aespa.api.scan import router as scan_router
from aespa.api.settings import router as settings_router
from aespa.api.sites import router as sites_router
from aespa.api.test_runs import router as test_runs_router
from aespa.api.traffic import router as traffic_router
from aespa.config import Settings, get_settings
from aespa.db import init_db


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    yield


_JWKS_CACHE: dict[str, tuple[dict, float]] = {}
JWKS_CACHE_TTL = 3600.0


def _get_cloudflare_jwks(issuer: str) -> dict:
    now = time.time()
    if issuer in _JWKS_CACHE:
        keys, expiry = _JWKS_CACHE[issuer]
        if now < expiry:
            return keys

    resp = httpx.get(f"{issuer.rstrip('/')}/cdn-cgi/access/certs")
    resp.raise_for_status()
    keys = resp.json()
    _JWKS_CACHE[issuer] = (keys, now + JWKS_CACHE_TTL)
    return keys


def _verify_cloudflare_jwt(token: str) -> str | None:
    try:
        # 1. Unverified decode to extract the issuer
        unverified = jwt.decode(token, options={"verify_signature": False})
        issuer = unverified.get("iss")
        if not issuer or not issuer.startswith("https://") or not issuer.endswith(".cloudflareaccess.com"):
            return None

        # 2. Get JWKS dynamically from verified issuer
        jwks = _get_cloudflare_jwks(issuer)

        # 3. Get Key ID (kid) from header
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")
        if not kid:
            return None

        # 4. Find matching key
        jwk = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not jwk:
            return None

        # 5. Decode and cryptographically verify
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return decoded.get("email")
    except Exception:
        return None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="AESPA", version=settings.app_version, lifespan=_lifespan)

    app.include_router(sites_router)
    app.include_router(settings_router)
    app.include_router(test_runs_router)
    app.include_router(events_router)
    app.include_router(scan_router)
    app.include_router(traffic_router)
    app.include_router(reporting_debug_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/version")
    def version(request: Request) -> dict[str, str | None]:
        # Extract JWT assertion header if present
        jwt_token = request.headers.get("cf-access-jwt-assertion") or request.headers.get("Cf-Access-Jwt-Assertion")
        username = None
        if jwt_token:
            username = _verify_cloudflare_jwt(jwt_token)
        return {"version": settings.app_version, "username": username}

    web_dir: Path = settings.web_dir
    if web_dir.exists() and (web_dir / "index.html").exists():
        @app.middleware("http")
        async def _no_cache_web_assets(request, call_next):
            response = await call_next(request)
            if request.url.path in {"/", "/index.html", "/app.js", "/styles.css", "/sw.js", "/manifest.json"}:
                response.headers["Cache-Control"] = "no-store, max-age=0"
                response.headers["Pragma"] = "no-cache"
            return response

        def _index_html() -> HTMLResponse:
            html = (web_dir / "index.html").read_text(encoding="utf-8")
            html = html.replace("__AESPA_ASSET_VERSION__", settings.app_version)
            return HTMLResponse(
                html,
                headers={
                    "Cache-Control": "no-store, max-age=0",
                    "Pragma": "no-cache",
                },
            )

        app.add_api_route("/", _index_html, methods=["GET"], include_in_schema=False)
        app.add_api_route("/index.html", _index_html, methods=["GET"], include_in_schema=False)
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    else:
        @app.get("/")
        def _no_spa() -> JSONResponse:
            return JSONResponse(
                {
                    "detail": (
                        f"SPA assets not found at {web_dir}. Build the frontend "
                        "(see frontend/README) or place an index.html there."
                    )
                },
                status_code=503,
            )

    return app


app = create_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "aespa.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
