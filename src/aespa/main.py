from __future__ import annotations

import mimetypes
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from aespa import cloudflare_access
from aespa.api.alice import router as alice_router
from aespa.api.api_collections import router as api_collections_router
from aespa.api.api_test_runs import router as api_test_runs_router
from aespa.api.events import router as events_router
from aespa.api.extensions import router as extensions_router
from aespa.api.report_leads import router as report_leads_router
from aespa.api.reporting_debug import router as reporting_debug_router
from aespa.api.sast_runs import router as sast_runs_router
from aespa.api.scan import router as scan_router
from aespa.api.settings import router as settings_router
from aespa.api.sites import router as sites_router
from aespa.api.statistics import router as statistics_router
from aespa.api.systems import router as systems_router
from aespa.api.test_runs import router as test_runs_router
from aespa.api.traffic import router as traffic_router
from aespa.config import Settings, get_settings, settings_env_path
from aespa.db import get_session, init_db
from aespa.extensions.api import ExtensionApiDispatcher
from aespa.integration_server import integration_listener
from aespa.local_auth import LocalAuthMiddleware, auth_router, get_auth
from aespa.services import alice_goals as alice_goals_svc
from aespa.services import antigravity_provider as antigravity_provider_svc
from aespa.services import campaigns as campaigns_svc
from aespa.services import codex_provider as codex_provider_svc
from aespa.services import copilot_provider as copilot_provider_svc
from aespa.services import droid_provider as droid_provider_svc
from aespa.services import sast_sources as sast_sources_svc
from aespa.services import validator as validator_svc
from aespa.services.run_cleanup import LegacyBenchmarkReferenceError
from aespa.services.settings import get_cloudflare_access_config
from aespa.storage_migration import migrate_legacy_storage


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    from aespa.extensions import get_extension_manager

    get_extension_manager().load_extensions()
    sast_sources_svc.reconcile_interrupted_source_preparations()
    alice_goals_svc.reconcile_interrupted_goals()
    await validator_svc.resume_interrupted_validations()
    campaigns_svc.reconcile_campaigns()
    try:
        async with integration_listener(app.state.settings, app.state.auth):
            yield
    finally:
        await copilot_provider_svc.close_clients()
        await droid_provider_svc.close_clients()
        await codex_provider_svc.close_clients()
        await antigravity_provider_svc.close_clients()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="AESPA", version=settings.app_version, lifespan=_lifespan)
    auth = get_auth(settings)
    app.state.auth = auth
    app.state.settings = settings
    app.add_middleware(LocalAuthMiddleware, auth=auth)
    app.include_router(auth_router(auth))

    @app.exception_handler(LegacyBenchmarkReferenceError)
    async def _legacy_benchmark_reference(
        _request: Request, exc: LegacyBenchmarkReferenceError
    ):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    app.include_router(sites_router)
    app.include_router(api_collections_router)
    app.include_router(api_test_runs_router)
    app.include_router(sast_runs_router)
    app.include_router(report_leads_router)
    app.include_router(extensions_router)
    app.include_router(settings_router)
    app.include_router(test_runs_router)
    app.include_router(events_router)
    app.include_router(scan_router)
    app.include_router(traffic_router)
    app.include_router(reporting_debug_router)
    app.include_router(alice_router)
    app.include_router(statistics_router)
    app.include_router(systems_router)
    app.mount("/extension", ExtensionApiDispatcher())

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/version")
    def version(
        request: Request, session: Session = Depends(get_session)
    ) -> dict[str, str | None]:
        # Extract JWT assertion header if present
        jwt_token = request.headers.get(cloudflare_access.JWT_HEADER)
        username = None
        if jwt_token:
            audience = get_cloudflare_access_config(session).audience
            claims = cloudflare_access.verify_jwt(jwt_token, audience)
            username = claims.get("email") if claims else None
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
    # Public assets and build configuration affect the output just as source does.
    import subprocess

    repo_root = Path(__file__).resolve().parents[2]
    frontend = repo_root / "frontend"
    built = get_settings().web_dir / "index.html"
    if not frontend.exists():
        return  # installed without sources; nothing to build
    inputs = [
        frontend / name
        for name in (
            "index.html",
            "package.json",
            "package-lock.json",
            "vite.config.js",
        )
    ]
    for directory in ("src", "public"):
        inputs.extend((frontend / directory).rglob("*"))
    newest_src = max((p.stat().st_mtime for p in inputs if p.is_file()), default=0)
    if built.exists() and built.stat().st_mtime >= newest_src:
        return
    print("[aespa] frontend changed — running npm run build...")
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    subprocess.run([npm, "run", "build"], cwd=frontend, check=True)


def _port_available(host: str, port: int) -> bool:
    """Check whether a listener can bind to the requested address."""
    import errno
    import socket

    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        # create_server mirrors a real listener and enables safe address reuse
        # on POSIX, avoiding false positives from recently closed connections.
        with socket.create_server((host, port), family=family):
            pass
        return True
    except OSError as exc:
        address_in_use = exc.errno in {errno.EADDRINUSE, 10048} or (
            getattr(exc, "winerror", None) == 10048
        )
        if address_in_use:
            return False
        raise SystemExit(f"[aespa] Cannot listen on {host}:{port}: {exc}") from exc


def _find_available_port(host: str, preferred_port: int) -> int:
    """Try the configured port, then 9000 and successive higher ports."""
    if _port_available(host, preferred_port):
        return preferred_port
    for port in range(max(9000, preferred_port + 1), 65536):
        if _port_available(host, port):
            return port
    raise SystemExit(f"[aespa] Cannot start: no available port for {host}.")


def _run_server(server) -> bool:
    """Run Uvicorn and return false for its expected Ctrl+C interrupt."""
    try:
        server.run()
    except KeyboardInterrupt:
        return False
    return True


def _server_startup_failure_message(server, console=None) -> str | None:
    """Return the captured startup error when Uvicorn exits before listening."""
    if bool(getattr(server, "started", False)):
        return None

    header = "[aespa] Backend startup failed."
    if console is None:
        return header
    errors = list(console.handler.buffers.get("errors", ()))
    if not errors:
        return header
    return f"{header}\n\n" + "\n\n".join(errors)


def main() -> None:
    import uvicorn

    from aespa.browser import ensure_chromium
    from aespa.console import InteractiveConsole, interactive_console_available

    settings = get_settings()
    migrate_legacy_storage(settings)
    port = _find_available_port(settings.host, settings.port)
    if port != settings.port:
        print(f"[aespa] Port {settings.port} is in use; using port {port}.")
    _build_frontend_if_stale()
    ensure_chromium()
    auth = get_auth(settings.model_copy(update={"port": port}))
    restart: dict[str, object | None] = {"port": None, "server": None, "quit": False}

    def change_port(port: int) -> None:
        restart["port"] = port
        server = restart["server"]
        if server is not None:
            server.should_exit = True

    def request_quit() -> None:
        if restart["quit"]:
            server = restart["server"]
            if server is not None:
                server.force_exit = True
            return
        restart["quit"] = True
        server = restart["server"]
        if server is not None:
            server.should_exit = True

    console = (
        InteractiveConsole(
            port=port,
            host=settings.host,
            env_path=settings_env_path(),
            on_port_change=change_port,
            on_rotate_key=lambda: get_auth(
                settings.model_copy(update={"port": port})
            ).rotate_key(),
            on_quit=request_quit,
            log_db_path=Path(settings.data_dir) / "logs.db",
            authentication_key=auth.key,
            login_url_factory=lambda base: get_auth(
                settings.model_copy(update={"port": int(urlsplit(base).port or port)})
            ).login_url(base),
        )
        if interactive_console_available()
        else None
    )
    if console:
        console.start()
        from aespa.runtime_capabilities import (
            NO_GRAPHICAL_DISPLAY_MESSAGE,
            graphical_display_available,
        )
        from aespa.services.events import agent_activity_log

        if not graphical_display_available():
            agent_activity_log.warning(NO_GRAPHICAL_DISPLAY_MESSAGE)
    startup_failure: str | None = None
    try:
        while True:
            if restart["quit"]:
                break
            available_port = _find_available_port(settings.host, port)
            if available_port != port:
                print(f"[aespa] Port {port} is in use; using port {available_port}.")
                port = available_port
            auth = get_auth(settings.model_copy(update={"port": port}))
            server = uvicorn.Server(
                uvicorn.Config(
                    create_app(settings.model_copy(update={"port": port})),
                    host=settings.host,
                    port=port,
                    reload=False,
                    timeout_graceful_shutdown=0.25 if sys.platform == "win32" else None,
                    log_config=None if console else uvicorn.config.LOGGING_CONFIG,
                )
            )
            restart["server"] = server
            if restart["quit"]:
                break
            if console:
                console.handler.set_runtime_port(port)
            else:
                print(f"[aespa] Listening on http://{settings.host}:{port}")
                print(f"[aespa] Authentication key: {auth.key}")
            if not _run_server(server):
                break
            if restart["quit"]:
                break
            startup_failure = _server_startup_failure_message(server, console)
            if startup_failure is not None:
                break
            next_port = restart["port"]
            if next_port is None:
                break
            port = int(next_port)
            restart["port"] = None
    finally:
        restart["server"] = None
        if console:
            console.stop()
    if startup_failure is not None:
        print(startup_failure, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
