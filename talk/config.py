"""Application configuration."""

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from talk.domain.value.types import Handle


class DatabaseSettings(BaseModel):
    """Database configuration."""

    url: str = "postgresql+asyncpg://talk:talk@localhost:5432/talk"
    pool_size: int = 5
    max_overflow: int = 10


class AuthSettings(BaseModel):
    """Authentication configuration."""

    # JWT settings
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"  # Must be overridden in production
    jwt_algorithm: str = "HS256"
    jwt_expiry_days: int = 30

    # AT Protocol OAuth
    default_pds_url: str = "https://bsky.social"  # Default PDS for handle resolution

    # OAuth client configuration
    # client_id is the URL where client metadata is hosted
    # For AT Protocol, this should be: https://your-api-domain.com/client-metadata.json
    oauth_client_id: str | None = None
    oauth_redirect_uri: str | None = None


class InvitationSettings(BaseModel):
    """Invitation configuration."""

    # List of Bluesky handles (e.g., Handle(root="user.bsky.social")) that can invite without limits
    unlimited_inviters: list[Handle] = []


class APISettings(BaseModel):
    """API configuration."""

    host: str = "localhost"
    port: int = 8000
    frontend_url: str = "http://localhost:3000"  # For post-login redirect
    base_url: str = "http://localhost:8000"  # Base URL for OAuth client metadata (HTTPS in production)


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # Allows DATABASE__URL syntax
    )

    # Environment
    environment: str = "development"
    debug: bool = False

    # Nested settings
    database: DatabaseSettings = DatabaseSettings()
    auth: AuthSettings = AuthSettings()
    api: APISettings = APISettings()
    invitations: InvitationSettings = InvitationSettings()

    @property
    def database_url(self) -> str:
        """Backwards compatibility for database_url."""
        return self.database.url
