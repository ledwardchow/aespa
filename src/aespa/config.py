from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "aespa.db"
DEFAULT_WEB_DIR = Path(__file__).resolve().parent / "web"


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


def get_settings() -> Settings:
    return Settings()
