"""Unit tests for AT Protocol identity resolution."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from talk.adapter.bluesky.identity import (
    DIDDocument,
    IdentityResolutionError,
    get_pds_endpoint,
    resolve_did_document,
    resolve_handle_to_did,
    _resolve_handle_via_dns,
)
from talk.domain.value.types import BlueskyDID


class TestDIDDocument:
    """Tests for DIDDocument model."""

    def test_creates_did_document_with_required_fields(self):
        """Should create DID document with id and service."""
        doc = DIDDocument(
            id="did:plc:abc123",
            service=[
                {
                    "id": "#atproto_pds",
                    "type": "AtprotoPersonalDataServer",
                    "serviceEndpoint": "https://bsky.social",
                }
            ],
        )

        assert doc.id == "did:plc:abc123"
        assert len(doc.service) == 1
        assert doc.service[0]["type"] == "AtprotoPersonalDataServer"


class TestResolveHandleToDID:
    """Tests for resolve_handle_to_did function."""

    @pytest.mark.asyncio
    async def test_resolves_handle_successfully(self):
        """Should resolve handle to DID via HTTPS endpoint."""
        mock_response = MagicMock()
        mock_response.text = "did:plc:abc123xyz"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await resolve_handle_to_did("alice.bsky.social")

            assert isinstance(result, BlueskyDID)
            assert str(result) == "did:plc:abc123xyz"
            mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
                "https://alice.bsky.social/.well-known/atproto-did"
            )

    @pytest.mark.asyncio
    async def test_strips_at_prefix_from_handle(self):
        """Should remove @ prefix if present."""
        mock_response = MagicMock()
        mock_response.text = "did:plc:abc123"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            await resolve_handle_to_did("@alice.bsky.social")

            mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
                "https://alice.bsky.social/.well-known/atproto-did"
            )

    @pytest.mark.asyncio
    async def test_strips_whitespace_from_response(self):
        """Should strip whitespace from DID response."""
        mock_response = MagicMock()
        mock_response.text = "  did:plc:abc123  \n"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await resolve_handle_to_did("alice.bsky.social")

            assert isinstance(result, BlueskyDID)
            assert str(result) == "did:plc:abc123"

    @pytest.mark.asyncio
    async def test_validates_did_format(self):
        """Should validate that response starts with 'did:'."""
        mock_response = MagicMock()
        mock_response.text = "invalid-response"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(IdentityResolutionError, match="Invalid DID format"):
                await resolve_handle_to_did("alice.bsky.social")

    @pytest.mark.asyncio
    async def test_sets_10_second_timeout(self):
        """Should use 10 second timeout for HTTPS request."""
        mock_response = MagicMock()
        mock_response.text = "did:plc:abc123"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            await resolve_handle_to_did("alice.bsky.social")

            # Check timeout was set to 10.0
            mock_client.assert_called_once_with(timeout=10.0)

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self):
        """Should raise IdentityResolutionError on HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("HTTP 404")
            )

            with pytest.raises(
                IdentityResolutionError, match="Failed to resolve handle"
            ):
                await resolve_handle_to_did("nonexistent.handle")


class TestResolveDIDDocument:
    """Tests for resolve_did_document function."""

    @pytest.mark.asyncio
    async def test_resolves_did_document_successfully(self):
        """Should resolve DID to document via PLC directory."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "id": "did:plc:abc123",
                "service": [
                    {
                        "id": "#atproto_pds",
                        "type": "AtprotoPersonalDataServer",
                        "serviceEndpoint": "https://bsky.social",
                    }
                ],
            }
        )
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            did = BlueskyDID("did:plc:abc123")
            result = await resolve_did_document(did)

            assert isinstance(result, DIDDocument)
            assert result.id == "did:plc:abc123"
            assert len(result.service) == 1
            mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
                "https://plc.directory/did:plc:abc123"
            )

    @pytest.mark.asyncio
    async def test_only_supports_plc_dids(self):
        """Should reject non-PLC DIDs."""
        did = BlueskyDID("did:web:example.com")
        with pytest.raises(IdentityResolutionError, match="Only did:plc: DIDs"):
            await resolve_did_document(did)

    @pytest.mark.asyncio
    async def test_sets_10_second_timeout(self):
        """Should use 10 second timeout for request."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "id": "did:plc:abc123",
                "service": [],
            }
        )
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            did = BlueskyDID("did:plc:abc123")
            await resolve_did_document(did)

            mock_client.assert_called_once_with(timeout=10.0)

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self):
        """Should raise IdentityResolutionError on HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("HTTP 404")
            )

            did = BlueskyDID("did:plc:nonexistent")
            with pytest.raises(IdentityResolutionError, match="Failed to resolve DID"):
                await resolve_did_document(did)

    @pytest.mark.asyncio
    async def test_raises_on_invalid_json(self):
        """Should raise IdentityResolutionError on invalid JSON."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(side_effect=ValueError("Invalid JSON"))
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            did = BlueskyDID("did:plc:abc123")
            with pytest.raises(
                IdentityResolutionError, match="Invalid DID document format"
            ):
                await resolve_did_document(did)


class TestGetPDSEndpoint:
    """Tests for get_pds_endpoint function."""

    def test_extracts_pds_endpoint_from_service(self):
        """Should extract PDS endpoint from service list."""
        doc = DIDDocument(
            id="did:plc:abc123",
            service=[
                {
                    "id": "#atproto_pds",
                    "type": "AtprotoPersonalDataServer",
                    "serviceEndpoint": "https://bsky.social",
                }
            ],
        )

        result = get_pds_endpoint(doc)

        assert result == "https://bsky.social"

    def test_finds_pds_among_multiple_services(self):
        """Should find PDS service among multiple services."""
        doc = DIDDocument(
            id="did:plc:abc123",
            service=[
                {
                    "id": "#other",
                    "type": "OtherService",
                    "serviceEndpoint": "https://other.com",
                },
                {
                    "id": "#atproto_pds",
                    "type": "AtprotoPersonalDataServer",
                    "serviceEndpoint": "https://bsky.social",
                },
            ],
        )

        result = get_pds_endpoint(doc)

        assert result == "https://bsky.social"

    def test_raises_when_no_pds_service(self):
        """Should raise error when no PDS service found."""
        doc = DIDDocument(
            id="did:plc:abc123",
            service=[
                {
                    "id": "#other",
                    "type": "OtherService",
                    "serviceEndpoint": "https://other.com",
                }
            ],
        )

        with pytest.raises(IdentityResolutionError, match="No PDS endpoint found"):
            get_pds_endpoint(doc)

    def test_raises_when_service_missing_endpoint(self):
        """Should raise error when PDS service has no endpoint."""
        doc = DIDDocument(
            id="did:plc:abc123",
            service=[
                {
                    "id": "#atproto_pds",
                    "type": "AtprotoPersonalDataServer",
                    # Missing serviceEndpoint
                }
            ],
        )

        with pytest.raises(IdentityResolutionError, match="No PDS endpoint found"):
            get_pds_endpoint(doc)

    def test_raises_when_empty_service_list(self):
        """Should raise error when service list is empty."""
        doc = DIDDocument(id="did:plc:abc123", service=[])

        with pytest.raises(IdentityResolutionError, match="No PDS endpoint found"):
            get_pds_endpoint(doc)


class TestDNSResolution:
    """Tests for DNS TXT record resolution."""

    def test_resolves_handle_via_dns_successfully(self):
        """Should resolve handle via DNS TXT record."""
        # Mock DNS response
        mock_rdata = Mock()
        mock_rdata.strings = [b"did=did:plc:abc123"]

        with patch("dns.resolver.resolve") as mock_resolve:
            mock_resolve.return_value = [mock_rdata]

            result = _resolve_handle_via_dns("rory.bio")

            assert result == "did:plc:abc123"
            mock_resolve.assert_called_once_with("_atproto.rory.bio", "TXT")

    def test_strips_did_prefix_from_txt_record(self):
        """Should remove 'did=' prefix from TXT record value."""
        mock_rdata = Mock()
        mock_rdata.strings = [b"did=did:plc:xyz789"]

        with patch("dns.resolver.resolve") as mock_resolve:
            mock_resolve.return_value = [mock_rdata]

            result = _resolve_handle_via_dns("example.com")

            assert result == "did:plc:xyz789"
            assert not result.startswith("did=")

    def test_returns_none_when_domain_not_found(self):
        """Should return None when domain doesn't exist."""
        import dns.resolver

        with patch("dns.resolver.resolve") as mock_resolve:
            mock_resolve.side_effect = dns.resolver.NXDOMAIN()

            result = _resolve_handle_via_dns("nonexistent.domain")

            assert result is None

    def test_returns_none_when_no_txt_records(self):
        """Should return None when no TXT records found."""
        import dns.resolver

        with patch("dns.resolver.resolve") as mock_resolve:
            mock_resolve.side_effect = dns.resolver.NoAnswer()

            result = _resolve_handle_via_dns("example.com")

            assert result is None

    def test_returns_none_when_txt_record_missing_did(self):
        """Should return None when TXT record doesn't contain 'did='."""
        mock_rdata = Mock()
        mock_rdata.strings = [b"some-other-value"]

        with patch("dns.resolver.resolve") as mock_resolve:
            mock_resolve.return_value = [mock_rdata]

            result = _resolve_handle_via_dns("example.com")

            assert result is None

    @pytest.mark.asyncio
    async def test_resolve_handle_tries_dns_first(self):
        """Should try DNS resolution before HTTPS."""
        # Mock DNS to succeed
        mock_rdata = Mock()
        mock_rdata.strings = [b"did=did:plc:dns123"]

        with patch("dns.resolver.resolve") as mock_resolve:
            mock_resolve.return_value = [mock_rdata]

            # Mock HTTPS to fail (shouldn't be called)
            with patch("httpx.AsyncClient") as mock_client:
                result = await resolve_handle_to_did("rory.bio")

                # Should use DNS result
                assert str(result) == "did:plc:dns123"

                # HTTPS client should not be called
                mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolve_handle_falls_back_to_https(self):
        """Should fall back to HTTPS when DNS fails."""
        # Mock DNS to fail
        import dns.resolver

        with patch("dns.resolver.resolve") as mock_dns:
            mock_dns.side_effect = dns.resolver.NXDOMAIN()

            # Mock HTTPS to succeed
            mock_response = MagicMock()
            mock_response.text = "did:plc:https456"
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )

                result = await resolve_handle_to_did("alice.bsky.social")

                # Should use HTTPS result
                assert str(result) == "did:plc:https456"

                # HTTPS should have been called
                mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
                    "https://alice.bsky.social/.well-known/atproto-did"
                )
