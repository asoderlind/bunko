"""Application settings, read from the environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite keeps the self-hosted single-user deployment to one container.
    database_url: str = "sqlite:////data/bunko.sqlite3"

    # Session signing. Required in production; a dev default keeps `uvicorn`
    # startable without ceremony, but it is loudly overridden in deploy.
    # Dev-only fallback. Production is required to override it (see main.py
    # startup check), so this value never signs a real session cookie.
    secret_key: str = ""
    session_cookie: str = "bunko_session"
    session_max_age: int = 60 * 60 * 24 * 30

    debug: bool = True
    allowed_hosts: str = "localhost,127.0.0.1"

    # Built SvelteKit output, served by this app.
    spa_dir: Path = Path("/spa")

    # --- media ---
    # Persistent media lives on a Docker volume, served through the API.
    media_dir: Path = Path("/data/media")
    media_max_bytes: int = 15 * 1024 * 1024

    # --- tagging ---
    tagging_poll_seconds: float = 2.0
    tagging_stale_seconds: int = 600
    tagging_request_timeout: int = 120
    tagging_max_input_chars: int = 6000
    tagging_prompt_tag_limit: int = 50

    # Seeded into provider_profile on first run.
    ollama_base_url: str = ""
    ollama_model: str = "llama3.1:8b"

    @property
    def allowed_host_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return not self.debug


@lru_cache
def get_settings() -> Settings:
    return Settings()
