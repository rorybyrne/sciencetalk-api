"""Application configuration."""

from typing import Literal
from pydantic import BaseModel, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    """Database configuration."""

    url: str = "postgresql+asyncpg://talk:talk@localhost:5432/talk"
    pool_size: int = 5
    max_overflow: int = 10


class BlueskyOAuthSettings(BaseModel):
    """Bluesky/AT Protocol OAuth configuration."""

    # Default PDS URL for handle resolution
    default_pds_url: str = "https://bsky.social"


class TwitterOAuthSettings(BaseModel):
    """Twitter OAuth 2.0 configuration."""

    # Twitter OAuth 2.0 client ID
    client_id: str = "CHANGE_ME_IN_PRODUCTION"

    # Twitter OAuth 2.0 client secret
    client_secret: str = "CHANGE_ME_IN_PRODUCTION"


class AuthSettings(BaseModel):
    """Authentication configuration."""

    # JWT settings
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"  # Must be overridden in production
    jwt_algorithm: str = "HS256"
    jwt_expiry_days: int = 30

    # OAuth callback URL (set by Settings validator from api.base_url)
    oauth_callback_url: str = "http://localhost:8000/auth/callback"

    # Provider-specific OAuth settings
    bluesky: BlueskyOAuthSettings = BlueskyOAuthSettings()
    twitter: TwitterOAuthSettings = TwitterOAuthSettings()


class InvitationSettings(BaseModel):
    """Invitation configuration."""

    # List of handles that can create accounts without invites and have unlimited invites
    # These are the founding/seed users who bootstrap the community
    # Format: provider handle (e.g., "alice.bsky.social", "bob@twitter.com")
    seed_users: list[str] = []


class APISettings(BaseModel):
    """API configuration."""

    host: str
    port: int
    protocol: Literal["http", "https"]
    frontend_host: str

    @computed_field
    @property
    def base_url(self) -> str:
        """Construct base URL from host.

        Returns base URL for this API server. Used for OAuth client metadata.
        In development: http://localhost:8000
        In production: https://api.talk.amacrin.com
        """
        if self.host == "localhost":
            return f"{self.protocol}://{self.host}:{self.port}"
        else:
            # Production uses standard ports (80/443)
            return f"{self.protocol}://{self.host}"

    @computed_field
    @property
    def frontend_url(self) -> str:
        """Frontend URL for post-login redirects.

        In development: http://localhost:3000
        In production: https://talk.amacrin.com (or separate domain)
        """
        # Frontend runs on port 3000 in development (localhost)
        if self.frontend_host == "localhost":
            return "http://localhost:3000"
        else:
            # Production: use protocol and frontend_host
            return f"{self.protocol}://{self.frontend_host}"


class ObservabilitySettings(BaseModel):
    """Observability configuration for Logfire."""

    # Logfire API token (optional - if not set, logs only go to console)
    # Can be set via OBSERVABILITY__LOGFIRE_TOKEN env var
    logfire_token: str | None = None

    # Whether to send telemetry to Logfire cloud
    # If None, will auto-determine: sends if token is present, otherwise console-only
    send_to_logfire: bool | None = None


class Settings(BaseSettings):
    """Application settings.

    Configuration is driven by environment and host values, with all URLs
    computed from them. Set environment variables to override:

    Development (default):
        HOST=localhost
        PORT=8000
        ENVIRONMENT=development
        -> API: http://localhost:8000
        -> OAuth callbacks: http://localhost:8000/auth/callback
        -> Frontend: http://localhost:3000

    Production:
        HOST=api.talk.amacrin.com
        ENVIRONMENT=production
        FRONTEND_HOST=talk.amacrin.com
        -> API: https://api.talk.amacrin.com
        -> OAuth callbacks: https://api.talk.amacrin.com/auth/callback
        -> Frontend: https://talk.amacrin.com
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # Allows DATABASE__URL syntax
    )

    # Environment determines protocol and defaults
    environment: Literal["test", "development", "staging", "production"] = "development"
    debug: bool = False

    # Host configuration (all URLs computed from these)
    host: str = "localhost"
    port: int = 8000
    frontend_host: str = (
        "localhost"  # Frontend domain (e.g., talk.amacrin.com in production)
    )

    # Nested settings
    database: DatabaseSettings = DatabaseSettings()
    auth: AuthSettings = AuthSettings()
    api: APISettings = APISettings(
        host="localhost", port=8000, protocol="http", frontend_host="localhost"
    )  # Overwritten in validator
    invitations: InvitationSettings = InvitationSettings()
    observability: ObservabilitySettings = ObservabilitySettings()

    @model_validator(mode="after")
    def initialize_api_settings(self) -> "Settings":
        """Initialize API settings from host and environment."""
        protocol: Literal["http", "https"] = (
            "http" if self.environment == "development" else "https"
        )

        self.api = APISettings(
            host=self.host,
            port=self.port,
            protocol=protocol,
            frontend_host=self.frontend_host,
        )

        # Set OAuth callback URL from api.base_url
        self.auth.oauth_callback_url = f"{self.api.base_url}/auth/callback"

        return self

    @property
    def database_url(self) -> str:
        """Backwards compatibility for database_url."""
        return self.database.url
