"""Unit tests for OAuth metadata endpoint."""

from talk.config import Settings
from talk.interface.api.routes.oauth_metadata import get_oauth_client_metadata


class TestGetOAuthClientMetadata:
    """Tests for get_oauth_client_metadata function."""

    def test_returns_valid_metadata_structure(self):
        """Should return valid OAuth client metadata."""
        # Arrange
        settings = Settings()
        settings.api.base_url = "https://talk.example.com"

        # Act
        metadata = get_oauth_client_metadata(settings)

        # Assert
        assert hasattr(metadata, "client_id")
        assert hasattr(metadata, "client_name")
        assert hasattr(metadata, "client_uri")
        assert hasattr(metadata, "logo_uri")
        assert hasattr(metadata, "redirect_uris")
        assert hasattr(metadata, "grant_types")
        assert hasattr(metadata, "response_types")
        assert hasattr(metadata, "scope")
        assert hasattr(metadata, "token_endpoint_auth_method")
        assert hasattr(metadata, "application_type")
        assert hasattr(metadata, "dpop_bound_access_tokens")

    def test_client_id_matches_metadata_endpoint(self):
        """Client ID should be the URL of the metadata endpoint."""
        settings = Settings()
        settings.api.base_url = "https://talk.example.com"

        metadata = get_oauth_client_metadata(settings)

        assert (
            metadata.client_id
            == "https://talk.example.com/.well-known/oauth-client-metadata"
        )

    def test_client_name_is_science_talk(self):
        """Client name should be Science Talk."""
        settings = Settings()

        metadata = get_oauth_client_metadata(settings)

        assert metadata.client_name == "Science Talk"

    def test_client_uri_matches_base_url(self):
        """Client URI should match base URL."""
        settings = Settings()
        settings.api.base_url = "https://talk.example.com"

        metadata = get_oauth_client_metadata(settings)

        assert metadata.client_uri == "https://talk.example.com"

    def test_logo_uri_points_to_amacrin_svg(self):
        """Logo URI should point to amacrin.svg."""
        settings = Settings()
        settings.api.base_url = "https://talk.example.com"

        metadata = get_oauth_client_metadata(settings)

        assert metadata.logo_uri == "https://talk.example.com/amacrin.svg"

    def test_redirect_uris_includes_callback(self):
        """Redirect URIs should include callback endpoint."""
        settings = Settings()
        settings.api.base_url = "https://talk.example.com"

        metadata = get_oauth_client_metadata(settings)

        assert metadata.redirect_uris == ["https://talk.example.com/auth/callback"]

    def test_grant_types_includes_authorization_code(self):
        """Grant types should include authorization_code."""
        settings = Settings()

        metadata = get_oauth_client_metadata(settings)

        assert "authorization_code" in metadata.grant_types

    def test_response_types_includes_code(self):
        """Response types should include code."""
        settings = Settings()

        metadata = get_oauth_client_metadata(settings)

        assert "code" in metadata.response_types

    def test_scope_is_atproto(self):
        """Scope should be atproto."""
        settings = Settings()

        metadata = get_oauth_client_metadata(settings)

        assert metadata.scope == "atproto"

    def test_token_endpoint_auth_method_is_none(self):
        """Token endpoint auth method should be none (public client)."""
        settings = Settings()

        metadata = get_oauth_client_metadata(settings)

        assert metadata.token_endpoint_auth_method == "none"

    def test_application_type_is_web(self):
        """Application type should be web."""
        settings = Settings()

        metadata = get_oauth_client_metadata(settings)

        assert metadata.application_type == "web"

    def test_dpop_bound_access_tokens_is_true(self):
        """DPoP bound access tokens must be true per AT Protocol spec."""
        settings = Settings()

        metadata = get_oauth_client_metadata(settings)

        assert metadata.dpop_bound_access_tokens is True

    def test_uses_localhost_in_development(self):
        """Should use localhost base URL in development."""
        settings = Settings()
        # Default base_url is http://localhost:8000

        metadata = get_oauth_client_metadata(settings)

        assert "localhost" in metadata.client_id
        assert "localhost" in metadata.client_uri
        assert all("localhost" in uri for uri in metadata.redirect_uris)
