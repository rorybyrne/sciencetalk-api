"""DPoP (Demonstrating Proof-of-Possession) implementation for AT Protocol OAuth."""

import time
from base64 import urlsafe_b64encode
from hashlib import sha256
from typing import Any
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ec
from jwcrypto import jwk, jwt


class DPoPKeyPair:
    """ES256 keypair for DPoP proof signing.

    DPoP binds access tokens to a specific cryptographic key pair,
    preventing token theft. Even if someone intercepts the access token,
    they cannot use it without the corresponding private key.

    IMPORTANT: Generate a new keypair for each OAuth session.
    The keypair is discarded after authentication completes.

    Attributes:
        private_key: JWK private key for signing DPoP proofs
        public_key: JWK public key included in DPoP proof headers
    """

    def __init__(self) -> None:
        """Generate new ES256 (ECDSA with P-256 curve) keypair."""
        # Generate ECDSA key with P-256 curve (required by AT Protocol)
        private_key_obj = ec.generate_private_key(ec.SECP256R1())
        self.private_key = jwk.JWK.from_pyca(private_key_obj)

        # Extract public key
        public_key_obj = private_key_obj.public_key()
        self.public_key = jwk.JWK.from_pyca(public_key_obj)

    def get_public_jwk(self) -> dict[str, Any]:
        """Get public key as JWK for inclusion in DPoP proof header.

        Returns:
            JWK dict with kty, crv, x, y fields
        """
        return self.public_key.export(as_dict=True)


def create_dpop_proof(
    http_method: str,
    http_url: str,
    keypair: DPoPKeyPair,
    nonce: str | None = None,
    access_token: str | None = None,
) -> jwt.JWT:
    """Create DPoP proof JWT for HTTP request.

    DPoP proofs are signed JWTs that prove possession of the private key
    associated with an access token. They must be sent with every request
    to OAuth endpoints and protected resources.

    Args:
        http_method: HTTP method of the request (e.g., "POST", "GET")
        http_url: Full URL of the request (e.g., "https://bsky.social/oauth/token")
        keypair: DPoP keypair for signing the proof
        nonce: Server-provided nonce from DPoP-Nonce response header (optional)
        access_token: Access token for computing ath hash (required for PDS requests)

    Returns:
        Signed DPoP proof JWT token object (call .serialize() to get string)

    Example:
        >>> keypair = DPoPKeyPair()
        >>> proof = create_dpop_proof("POST", "https://bsky.social/oauth/token", keypair)
        >>> headers = {"DPoP": proof.serialize(), "Content-Type": "application/json"}
    """
    # JWT header with DPoP type and public key
    header = {
        "typ": "dpop+jwt",
        "alg": "ES256",
        "jwk": keypair.get_public_jwk(),
    }

    # JWT claims
    claims = {
        "jti": str(uuid4()),  # Unique ID per request (prevents replay attacks)
        "htm": http_method,  # HTTP method
        "htu": http_url,  # HTTP URL (without query/fragment)
        "iat": int(time.time()),  # Issued at timestamp
    }

    # Include server nonce if provided (required for retries after 401)
    if nonce:
        claims["nonce"] = nonce

    # Compute access token hash for PDS requests
    if access_token:
        ath_bytes = sha256(access_token.encode("ascii")).digest()
        ath = urlsafe_b64encode(ath_bytes).rstrip(b"=").decode("ascii")
        claims["ath"] = ath

    # Sign JWT with private key
    token = jwt.JWT(header=header, claims=claims)
    token.make_signed_token(keypair.private_key)

    return token
