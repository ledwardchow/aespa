from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from aespa.browser import _bundled, app_data_dir

try:
    _pkg_version = version("aespa")
except PackageNotFoundError:
    _pkg_version = "unknown"


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEB_DIR = Path(__file__).resolve().parent / "web"

# Packaged .app: the bundle is read-only, so db + uploads live in a per-user
# Application Support dir. Plain `uv run aespa` keeps them at the repo root.
if _bundled():
    _DATA_ROOT = app_data_dir()
    _DATA_ROOT.mkdir(parents=True, exist_ok=True)
else:
    _DATA_ROOT = PROJECT_ROOT

DEFAULT_DB_PATH = _DATA_ROOT / "aespa.db"
DEFAULT_DATA_DIR = _DATA_ROOT / "aespa_data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AESPA_",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{DEFAULT_DB_PATH}"
    host: str = "127.0.0.1"
    port: int = 8000
    web_dir: Path = DEFAULT_WEB_DIR
    data_dir: Path = DEFAULT_DATA_DIR
    app_version: str = _pkg_version


def get_settings() -> Settings:
    return Settings()
