"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Environment
    environment: str = "development"
    debug: bool = False

    # API
    api_host: str = "localhost"
    api_port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://talk:talk@localhost:5432/talk"

    # AT Protocol / Bluesky
    atproto_pds_url: str = "https://bsky.social"  # Public Data Server URL

    # External providers (legacy - can be removed if not needed)
    provider1_api_key: str = ""
    provider2_endpoint: str = ""
