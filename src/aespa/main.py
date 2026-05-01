from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from aespa.api.settings import router as settings_router
from aespa.api.sites import router as sites_router
from aespa.config import Settings, get_settings
from aespa.db import init_db


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="AESPA", version="0.1.0", lifespan=_lifespan)

    app.include_router(sites_router)
    app.include_router(settings_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    web_dir: Path = settings.web_dir
    if web_dir.exists() and (web_dir / "index.html").exists():
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
