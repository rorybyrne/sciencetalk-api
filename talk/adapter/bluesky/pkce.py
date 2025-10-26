"""PKCE (Proof Key for Code Exchange) utilities for OAuth security."""

import secrets
from base64 import urlsafe_b64encode
from hashlib import sha256


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE verifier and challenge for OAuth authorization.

    PKCE prevents authorization code interception attacks by requiring
    the client to prove possession of a secret (verifier) during token
    exchange. The challenge is sent during authorization, and the verifier
    is sent during token exchange.

    Returns:
        Tuple of (verifier, challenge), both base64url encoded strings
        - verifier: Random secret kept by client (64 bytes)
        - challenge: SHA-256 hash of verifier for authorization request

    Example:
        >>> verifier, challenge = generate_pkce_pair()
        >>> # Send challenge in authorization request
        >>> # Send verifier in token exchange request
    """
    # Generate 64 random bytes (within PKCE 32-96 byte requirement)
    verifier_bytes = secrets.token_bytes(64)
    verifier = urlsafe_b64encode(verifier_bytes).rstrip(b"=").decode("ascii")

    # Create S256 challenge: SHA-256 hash of verifier
    challenge_bytes = sha256(verifier.encode("ascii")).digest()
    challenge = urlsafe_b64encode(challenge_bytes).rstrip(b"=").decode("ascii")

    return (verifier, challenge)
