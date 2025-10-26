"""Identity resolution for AT Protocol (handle to DID, DID to PDS)."""

import httpx
from pydantic import BaseModel
import dns.resolver

from talk.domain.value.types import BlueskyDID


class DIDDocument(BaseModel):
    """DID Document from AT Protocol.

    Simplified model containing only fields needed for OAuth.
    Full spec: https://www.w3.org/TR/did-core/
    """

    id: str  # The DID (e.g., "did:plc:...")
    service: list[dict[str, str]]  # Service endpoints (includes PDS)


class IdentityResolutionError(Exception):
    """Failed to resolve identity (handle to DID or DID to document)."""

    pass


async def resolve_handle_to_did(handle: str) -> BlueskyDID:
    """Resolve AT Protocol handle to DID.

    Tries two methods in order:
    1. DNS TXT record at _atproto.{handle} (recommended for custom domains)
    2. HTTPS well-known endpoint at https://{handle}/.well-known/atproto-did

    Args:
        handle: AT Protocol handle (e.g., "alice.bsky.social" or "rory.bio")

    Returns:
        BlueskyDID value object

    Raises:
        IdentityResolutionError: If resolution fails

    Example:
        >>> did = await resolve_handle_to_did("alice.bsky.social")
        >>> print(did)  # BlueskyDID("did:plc:abc123...")
        >>> did = await resolve_handle_to_did("rory.bio")  # Works with custom domains!
    """
    # Remove @ prefix if present
    handle = handle.lstrip("@")

    # Try DNS TXT record first (recommended method)
    try:
        did_str = _resolve_handle_via_dns(handle)
        if did_str:
            return BlueskyDID(did_str)
    except Exception:
        # DNS resolution failed, try HTTPS
        pass

    # Fall back to HTTPS well-known endpoint
    try:
        did_str = await _resolve_handle_via_https(handle)
        return BlueskyDID(did_str)
    except IdentityResolutionError:
        raise
    except ValueError as e:
        # BlueskyDID validation error
        raise IdentityResolutionError(
            f"Invalid DID format from {handle}: {str(e)}"
        ) from e
    except Exception as e:
        # Both methods failed
        raise IdentityResolutionError(
            f"Failed to resolve handle {handle}: {str(e)}"
        ) from e


def _resolve_handle_via_dns(handle: str) -> str | None:
    """Resolve handle to DID via DNS TXT record.

    Looks for TXT record at _atproto.{handle} with format: did=did:plc:...

    Args:
        handle: Domain handle (e.g., "rory.bio")

    Returns:
        DID string if found, None otherwise

    Raises:
        Exception: If DNS query fails
    """
    try:
        # Query DNS TXT record for _atproto subdomain
        answers = dns.resolver.resolve(f"_atproto.{handle}", "TXT")

        # Look for record starting with "did="
        for rdata in answers:
            # TXT records are returned as a list of strings (for multi-line records)
            # Join them and decode
            txt_value = "".join(
                [s.decode() if isinstance(s, bytes) else s for s in rdata.strings]
            )

            if txt_value.startswith("did="):
                did_str = txt_value[4:]  # Remove "did=" prefix
                return did_str.strip()

        return None

    except dns.resolver.NXDOMAIN:
        # Domain doesn't exist
        return None
    except dns.resolver.NoAnswer:
        # No TXT records found
        return None
    except Exception:
        # Other DNS errors
        return None


async def _resolve_handle_via_https(handle: str) -> str:
    """Resolve handle to DID via HTTPS well-known endpoint.

    Args:
        handle: Domain handle

    Returns:
        DID string

    Raises:
        Exception: If HTTPS request fails
    """
    url = f"https://{handle}/.well-known/atproto-did"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()

        # Response is plain text DID
        return response.text.strip()


async def resolve_did_document(did: BlueskyDID) -> DIDDocument:
    """Resolve DID to DID document via PLC directory.

    For AT Protocol, DIDs are resolved via https://plc.directory/{did}

    Args:
        did: BlueskyDID value object to resolve

    Returns:
        DID document with service endpoints

    Raises:
        IdentityResolutionError: If resolution fails

    Example:
        >>> did = BlueskyDID("did:plc:abc123")
        >>> doc = await resolve_did_document(did)
        >>> pds_url = get_pds_endpoint(doc)
    """
    # Extract string value from BlueskyDID
    did_str = str(did)

    if not did_str.startswith("did:plc:"):
        raise IdentityResolutionError(f"Only did:plc: DIDs supported, got: {did_str}")

    url = f"https://plc.directory/{did_str}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Parse DID document
            return DIDDocument(**response.json())

    except IdentityResolutionError:
        # Re-raise our own errors
        raise
    except ValueError as e:
        # Pydantic validation errors
        raise IdentityResolutionError(
            f"Invalid DID document format for {did_str}: {str(e)}"
        ) from e
    except Exception as e:
        # Catch all HTTP errors and network issues
        raise IdentityResolutionError(
            f"Failed to resolve DID {did_str}: {str(e)}"
        ) from e


def get_pds_endpoint(did_document: DIDDocument) -> str:
    """Extract PDS endpoint URL from DID document.

    Args:
        did_document: Resolved DID document

    Returns:
        PDS endpoint URL (e.g., "https://bsky.social")

    Raises:
        IdentityResolutionError: If PDS endpoint not found

    Example:
        >>> doc = await resolve_did_document("did:plc:abc123")
        >>> pds_url = get_pds_endpoint(doc)
        >>> print(pds_url)  # "https://bsky.social"
    """
    # Look for service with type "AtprotoPersonalDataServer"
    for service in did_document.service:
        if service.get("type") == "AtprotoPersonalDataServer":
            endpoint = service.get("serviceEndpoint")
            if endpoint:
                return endpoint

    raise IdentityResolutionError(
        f"No PDS endpoint found in DID document for {did_document.id}"
    )
