"""Unit tests for authorization server metadata discovery."""

import pytest
from httpx import Response
from unittest.mock import AsyncMock, patch

from talk.adapter.bluesky.metadata import AuthServerMetadata, discover_auth_server


class TestAuthServerMetadata:
    """Tests for AuthServerMetadata model."""

    def test_creates_metadata_with_required_fields(self):
        """Should create metadata with all required fields."""
        metadata = AuthServerMetadata(
            issuer="https://bsky.social",
            pushed_authorization_request_endpoint="https://bsky.social/oauth/par",
            authorization_endpoint="https://bsky.social/oauth/authorize",
            token_endpoint="https://bsky.social/oauth/token",
        )

        assert metadata.issuer == "https://bsky.social"
        assert (
            metadata.pushed_authorization_request_endpoint
            == "https://bsky.social/oauth/par"
        )
        assert metadata.authorization_endpoint == "https://bsky.social/oauth/authorize"
        assert metadata.token_endpoint == "https://bsky.social/oauth/token"


class TestDiscoverAuthServer:
    """Tests for discover_auth_server function."""

    @pytest.mark.asyncio
    async def test_discovers_metadata_successfully(self):
        """Should fetch and parse metadata from PDS."""
        # Mock response data
        mock_response_data = {
            "issuer": "https://bsky.social",
            "pushed_authorization_request_endpoint": "https://bsky.social/oauth/par",
            "authorization_endpoint": "https://bsky.social/oauth/authorize",
            "token_endpoint": "https://bsky.social/oauth/token",
        }

        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Setup mock response
            mock_response = AsyncMock(spec=Response)
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response

            # Act
            metadata = await discover_auth_server("https://bsky.social")

            # Assert
            assert metadata.issuer == "https://bsky.social"
            assert (
                metadata.pushed_authorization_request_endpoint
                == "https://bsky.social/oauth/par"
            )
            assert (
                metadata.authorization_endpoint == "https://bsky.social/oauth/authorize"
            )
            assert metadata.token_endpoint == "https://bsky.social/oauth/token"

            # Verify correct URL was called
            mock_client.get.assert_called_once_with(
                "https://bsky.social/.well-known/oauth-authorization-server"
            )

    @pytest.mark.asyncio
    async def test_uses_correct_well_known_url(self):
        """Should construct correct well-known URL."""
        mock_response_data = {
            "issuer": "https://custom.pds.example",
            "pushed_authorization_request_endpoint": "https://custom.pds.example/oauth/par",
            "authorization_endpoint": "https://custom.pds.example/oauth/authorize",
            "token_endpoint": "https://custom.pds.example/oauth/token",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock(spec=Response)
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response

            # Act
            await discover_auth_server("https://custom.pds.example")

            # Assert
            mock_client.get.assert_called_once_with(
                "https://custom.pds.example/.well-known/oauth-authorization-server"
            )

    @pytest.mark.asyncio
    async def test_sets_timeout(self):
        """Should configure HTTP client with timeout."""
        mock_response_data = {
            "issuer": "https://bsky.social",
            "pushed_authorization_request_endpoint": "https://bsky.social/oauth/par",
            "authorization_endpoint": "https://bsky.social/oauth/authorize",
            "token_endpoint": "https://bsky.social/oauth/token",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock(spec=Response)
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response

            # Act
            await discover_auth_server("https://bsky.social")

            # Assert - client was created with timeout
            mock_client_class.assert_called_once_with(timeout=10.0)
