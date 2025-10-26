"""Unit tests for DPoP proof generation."""

import json
from base64 import urlsafe_b64decode
from hashlib import sha256

from jwcrypto import jwt

from talk.adapter.bluesky.dpop import DPoPKeyPair, create_dpop_proof


class TestDPoPKeyPair:
    """Tests for DPoPKeyPair class."""

    def test_generates_keypair(self):
        """Should generate ES256 keypair on initialization."""
        keypair = DPoPKeyPair()

        assert keypair.private_key is not None
        assert keypair.public_key is not None

    def test_public_jwk_has_required_fields(self):
        """Public JWK should have required fields for ES256."""
        keypair = DPoPKeyPair()
        jwk_dict = keypair.get_public_jwk()

        # Should have standard JWK fields for EC key
        assert "kty" in jwk_dict
        assert jwk_dict["kty"] == "EC"  # Elliptic Curve
        assert "crv" in jwk_dict
        assert jwk_dict["crv"] == "P-256"  # SECP256R1 curve
        assert "x" in jwk_dict  # X coordinate
        assert "y" in jwk_dict  # Y coordinate

    def test_generates_unique_keypairs(self):
        """Each instance should generate a different keypair."""
        keypair1 = DPoPKeyPair()
        keypair2 = DPoPKeyPair()

        jwk1 = keypair1.get_public_jwk()
        jwk2 = keypair2.get_public_jwk()

        # Public keys should be different
        assert jwk1["x"] != jwk2["x"]
        assert jwk1["y"] != jwk2["y"]


class TestCreateDPoPProof:
    """Tests for create_dpop_proof function."""

    def test_creates_valid_jwt(self):
        """Should create a valid JWT."""
        keypair = DPoPKeyPair()
        proof = create_dpop_proof("POST", "https://example.com/token", keypair)

        # Should be a JWT token object
        assert isinstance(proof, jwt.JWT)

        # Should serialize to valid JWT string (3 base64 parts separated by dots)
        serialized = proof.serialize()
        parts = serialized.split(".")
        assert len(parts) == 3

    def test_jwt_has_correct_header(self):
        """JWT header should have correct typ, alg, and jwk."""
        keypair = DPoPKeyPair()
        proof = create_dpop_proof("POST", "https://example.com/token", keypair)

        # Decode header from serialized token
        serialized = proof.serialize()
        header_b64 = serialized.split(".")[0]
        # Add padding if needed
        padding = "=" * (4 - len(header_b64) % 4)
        header_json = urlsafe_b64decode(header_b64 + padding).decode("utf-8")
        header = json.loads(header_json)

        assert header["typ"] == "dpop+jwt"
        assert header["alg"] == "ES256"
        assert "jwk" in header
        assert header["jwk"]["kty"] == "EC"

    def test_jwt_has_required_claims(self):
        """JWT claims should have jti, htm, htu, iat."""
        keypair = DPoPKeyPair()
        proof = create_dpop_proof("GET", "https://example.com/resource", keypair)

        # Decode JWT claims
        claims = json.loads(proof.claims)

        assert "jti" in claims  # Unique ID
        assert "htm" in claims  # HTTP method
        assert "htu" in claims  # HTTP URL
        assert "iat" in claims  # Issued at

        assert claims["htm"] == "GET"
        assert claims["htu"] == "https://example.com/resource"
        assert isinstance(claims["iat"], int)
        assert isinstance(claims["jti"], str)

    def test_includes_nonce_when_provided(self):
        """Should include nonce claim when provided."""
        keypair = DPoPKeyPair()
        proof = create_dpop_proof(
            "POST", "https://example.com/token", keypair, nonce="test-nonce-123"
        )

        # Decode claims
        claims = json.loads(proof.claims)

        assert "nonce" in claims
        assert claims["nonce"] == "test-nonce-123"

    def test_omits_nonce_when_not_provided(self):
        """Should not include nonce claim when not provided."""
        keypair = DPoPKeyPair()
        proof = create_dpop_proof("POST", "https://example.com/token", keypair)

        # Decode claims
        claims = json.loads(proof.claims)

        assert "nonce" not in claims

    def test_includes_ath_when_access_token_provided(self):
        """Should include ath (access token hash) when access token provided."""
        keypair = DPoPKeyPair()
        access_token = "test-access-token-123"
        proof = create_dpop_proof(
            "GET", "https://example.com/api", keypair, access_token=access_token
        )

        # Decode claims
        claims = json.loads(proof.claims)

        # Verify ath is SHA-256 hash of access token
        assert "ath" in claims
        expected_hash = sha256(access_token.encode("ascii")).digest()
        expected_ath = urlsafe_b64decode(claims["ath"] + "==")
        assert expected_ath == expected_hash

    def test_omits_ath_when_access_token_not_provided(self):
        """Should not include ath when access token not provided."""
        keypair = DPoPKeyPair()
        proof = create_dpop_proof("POST", "https://example.com/token", keypair)

        # Decode claims
        claims = json.loads(proof.claims)

        assert "ath" not in claims

    def test_signature_verifies_with_public_key(self):
        """JWT signature should verify with public key."""
        keypair = DPoPKeyPair()
        proof = create_dpop_proof("POST", "https://example.com/token", keypair)

        # Verification should succeed by deserializing and re-verifying
        serialized = proof.serialize()
        verified_token = jwt.JWT(jwt=serialized, key=keypair.public_key)
        # If verification fails, jwcrypto raises an exception

        # Should be able to read claims
        claims = json.loads(verified_token.claims)
        assert claims["htm"] == "POST"

    def test_generates_unique_jti_per_call(self):
        """Each proof should have a unique jti."""
        keypair = DPoPKeyPair()
        proof1 = create_dpop_proof("POST", "https://example.com/token", keypair)
        proof2 = create_dpop_proof("POST", "https://example.com/token", keypair)

        # Decode claims from both proofs
        claims1 = json.loads(proof1.claims)
        claims2 = json.loads(proof2.claims)

        # jti should be different
        assert claims1["jti"] != claims2["jti"]
