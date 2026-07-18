from __future__ import annotations

import mimetypes
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import jwt
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from aespa.api.alice import router as alice_router
from aespa.api.api_collections import router as api_collections_router
from aespa.api.api_test_runs import router as api_test_runs_router
from aespa.api.events import router as events_router
from aespa.api.reporting_debug import router as reporting_debug_router
from aespa.api.sast_runs import router as sast_runs_router
from aespa.api.scan import router as scan_router
from aespa.api.settings import router as settings_router
from aespa.api.sites import router as sites_router
from aespa.api.test_runs import router as test_runs_router
from aespa.api.traffic import router as traffic_router
from aespa.config import Settings, get_settings
from aespa.db import get_session, init_db
from aespa.services import validator as validator_svc
from aespa.services.settings import get_cloudflare_access_config


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    await validator_svc.resume_interrupted_validations()
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


def _verify_cloudflare_jwt(token: str, audience: str | None = None) -> str | None:
    try:
        # 1. Unverified decode to extract the issuer
        unverified = jwt.decode(token, options={"verify_signature": False})
        issuer = unverified.get("iss")
        if (
            not issuer
            or not issuer.startswith("https://")
            or not issuer.endswith(".cloudflareaccess.com")
        ):
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

        # 5. Decode and cryptographically verify. When an Access application
        # audience (AUD) is configured, enforce it — otherwise any Cloudflare
        # Access tenant's token would pass the issuer check. With none configured
        # we preserve the prior behaviour and skip the audience check.
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
        if audience:
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=audience,
            )
        else:
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
    app.include_router(api_collections_router)
    app.include_router(api_test_runs_router)
    app.include_router(sast_runs_router)
    app.include_router(settings_router)
    app.include_router(test_runs_router)
    app.include_router(events_router)
    app.include_router(scan_router)
    app.include_router(traffic_router)
    app.include_router(reporting_debug_router)
    app.include_router(alice_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/version")
    def version(
        request: Request, session: Session = Depends(get_session)
    ) -> dict[str, str | None]:
        # Extract JWT assertion header if present
        jwt_token = request.headers.get(
            "cf-access-jwt-assertion"
        ) or request.headers.get("Cf-Access-Jwt-Assertion")
        username = None
        if jwt_token:
            audience = get_cloudflare_access_config(session).audience
            username = _verify_cloudflare_jwt(jwt_token, audience)
        return {"version": settings.app_version, "username": username}

    web_dir: Path = settings.web_dir
    if web_dir.exists() and (web_dir / "index.html").exists():
        # Ensure StaticFiles serves .js with a JS MIME type. On Windows the
        # registry can map .js to text/plain, which makes browsers reject
        # `<script type="module">` imports (e.g. the vendored libraries).
        mimetypes.add_type("application/javascript", ".js")

        _NO_CACHE = {"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"}

        def _index_html() -> HTMLResponse:
            html = (web_dir / "index.html").read_text(encoding="utf-8")
            html = html.replace("__AESPA_ASSET_VERSION__", settings.app_version)
            return HTMLResponse(html, headers=_NO_CACHE)

        app.add_api_route("/", _index_html, methods=["GET"], include_in_schema=False)
        app.add_api_route(
            "/index.html", _index_html, methods=["GET"], include_in_schema=False
        )

        # Serve key mutable assets as explicit routes so StaticFiles never gets
        # a chance to return a 304 Not Modified.  A 304 tells the browser to use
        # its cached copy even when Cache-Control: no-store is set on the 304
        # response — the browser has already committed to serving the old file.
        _JS_TYPE = "application/javascript; charset=utf-8"
        _CSS_TYPE = "text/css; charset=utf-8"
        for _fname, _ctype in [("app.js", _JS_TYPE), ("styles.css", _CSS_TYPE)]:
            _fpath = web_dir / _fname
            if _fpath.exists():

                def _make_handler(p: Path, ct: str):
                    def _handler() -> Response:
                        return Response(
                            content=p.read_bytes(), media_type=ct, headers=_NO_CACHE
                        )

                    return _handler

                app.add_api_route(
                    f"/{_fname}",
                    _make_handler(_fpath, _ctype),
                    methods=["GET"],
                    include_in_schema=False,
                )

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


def _build_frontend_if_stale() -> None:
    # ponytail: rebuild only when a src file is newer than the built index.html.
    # Skips the ~10-30s npm build on every start; full rebuild if triggered.
    import subprocess

    repo_root = Path(__file__).resolve().parents[2]
    frontend = repo_root / "frontend"
    built = get_settings().web_dir / "index.html"
    if not frontend.exists():
        return  # installed without sources; nothing to build
    src = frontend / "src"
    newest_src = max(
        (p.stat().st_mtime for p in src.rglob("*") if p.is_file()), default=0
    )
    if built.exists() and built.stat().st_mtime >= newest_src:
        return
    print("[aespa] frontend changed — running npm run build...")
    subprocess.run(["npm", "run", "build"], cwd=frontend, check=True)


def main() -> None:
    import uvicorn

    from aespa.browser import ensure_chromium

    _build_frontend_if_stale()
    ensure_chromium()
    settings = get_settings()
    uvicorn.run(
        "aespa.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
