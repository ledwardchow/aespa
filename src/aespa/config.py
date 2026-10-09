from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic import model_validator
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

DEFAULT_DATA_DIR = _DATA_ROOT / "aespa_data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "aespa.db"
DEFAULT_LOG_DB_PATH = DEFAULT_DATA_DIR / "logs.db"
DEFAULT_EXTENSIONS_DIR = _DATA_ROOT / "extensions"
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BUNDLED_EXTENSIONS_DIR = Path(sys._MEIPASS) / "extensions"
else:
    BUNDLED_EXTENSIONS_DIR = PROJECT_ROOT / "extensions"


def settings_env_path() -> Path:
    """Writable console settings file for this launch mode."""
    if _bundled():
        return app_data_dir() / "settings.env"
    return Path.cwd() / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AESPA_",
        extra="ignore",
    )

    database_url: str = ""
    host: str = "127.0.0.1"
    port: int = 8000
    web_dir: Path = DEFAULT_WEB_DIR
    data_dir: Path = DEFAULT_DATA_DIR
    extensions_dir: Path = DEFAULT_EXTENSIONS_DIR
    app_version: str = _pkg_version

    @model_validator(mode="after")
    def use_data_dir_for_legacy_database_url(self) -> Settings:
        # Older .env files explicitly set the former default. Keep those
        # installations on the new portable path without changing custom URLs.
        if self.database_url in {
            "",
            "sqlite:///./aespa.db",
            "sqlite:///./aespa_data/aespa.db",
        }:
            self.database_url = f"sqlite:///{self.data_dir / 'aespa.db'}"
        return self


def get_settings() -> Settings:
    if _bundled():
        return Settings(_env_file=(Path.cwd() / ".env", settings_env_path()))
    return Settings(_env_file=settings_env_path())
