"""Authorization server metadata discovery for AT Protocol OAuth."""

import httpx
from pydantic import BaseModel


class AuthServerMetadata(BaseModel):
    """OAuth authorization server metadata from AT Protocol PDS.

    Per AT Protocol spec, authorization servers must publish metadata
    at /.well-known/oauth-authorization-server endpoint.

    Attributes:
        issuer: Authorization server issuer URL
        pushed_authorization_request_endpoint: URL for PAR requests
        authorization_endpoint: URL for authorization requests
        token_endpoint: URL for token exchange
    """

    issuer: str
    pushed_authorization_request_endpoint: str
    authorization_endpoint: str
    token_endpoint: str


async def discover_auth_server(pds_url: str) -> AuthServerMetadata:
    """Discover authorization server metadata from PDS.

    Fetches OAuth authorization server metadata from the well-known
    endpoint. This metadata tells us where to send authorization
    requests, PAR requests, and token requests.

    For Bluesky network users whose PDS doesn't have OAuth configured,
    falls back to using bsky.social as the authorization server.

    Args:
        pds_url: PDS URL (e.g., "https://bsky.social")

    Returns:
        Parsed authorization server metadata

    Raises:
        httpx.HTTPError: If metadata discovery fails
        pydantic.ValidationError: If metadata format is invalid

    Example:
        >>> metadata = await discover_auth_server("https://bsky.social")
        >>> print(metadata.issuer)
        "https://bsky.social"
        >>> print(metadata.token_endpoint)
        "https://bsky.social/oauth/token"
    """
    metadata_url = f"{pds_url}/.well-known/oauth-authorization-server"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(metadata_url)

        # If PDS doesn't have OAuth configured, fallback to bsky.social for Bluesky network users
        if response.status_code == 404 and "bsky.network" in pds_url:
            fallback_url = "https://bsky.social/.well-known/oauth-authorization-server"
            response = await client.get(fallback_url)

        response.raise_for_status()

        return AuthServerMetadata(**response.json())
