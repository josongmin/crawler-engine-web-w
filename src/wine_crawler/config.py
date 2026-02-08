from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base directories (gitignored)
    data_dir: Path = Field(default=Path("data"))
    downloads_dir: Path = Field(default=Path("downloads"))
    traces_dir: Path = Field(default=Path("traces"))
    screenshots_dir: Path = Field(default=Path("screenshots"))
    storage_state_dir: Path = Field(default=Path("storage_state"))
    logs_dir: Path = Field(default=Path("logs"))

    # Playwright defaults
    headless: bool = True
    slow_mo_ms: int = 0
    navigation_timeout_ms: int = 30_000
    action_timeout_ms: int = 15_000
    locale: str = "en-US"

    # Concurrency / retries
    max_retries: int = 3

    # Site credentials (loaded from .env)
    burghound_email: str = ""
    burghound_password: str = ""

    # Proxy (optional)
    proxy_server: str = ""
    proxy_username: str = ""
    proxy_password: str = ""

    # Admin Web Tool
    admin_host: str = "127.0.0.1"
    admin_port: int = 8470
    admin_password: str = ""
    admin_secret_key: str = ""
    admin_db_path: Path = Field(default=Path("data/admin.db"))


def ensure_dirs(settings: Settings) -> None:
    for p in [
        settings.data_dir,
        settings.downloads_dir,
        settings.traces_dir,
        settings.screenshots_dir,
        settings.storage_state_dir,
        settings.logs_dir,
    ]:
        p.mkdir(parents=True, exist_ok=True)
