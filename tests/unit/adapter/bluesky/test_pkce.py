"""Unit tests for PKCE utilities."""

import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from hashlib import sha256


from talk.adapter.bluesky.pkce import generate_pkce_pair


class TestGeneratePkcePair:
    """Tests for generate_pkce_pair function."""

    def test_generates_valid_pair(self):
        """Should generate valid verifier and challenge pair."""
        verifier, challenge = generate_pkce_pair()

        # Both should be non-empty strings
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)
        assert len(verifier) > 0
        assert len(challenge) > 0

    def test_verifier_is_base64url_encoded(self):
        """Verifier should be valid base64url encoded string."""
        verifier, _ = generate_pkce_pair()

        # Should only contain base64url characters (no padding)
        assert re.match(r"^[A-Za-z0-9_-]+$", verifier)

        # Should be decodable
        decoded = urlsafe_b64decode(verifier + "==")
        assert len(decoded) == 64  # 64 bytes as specified

    def test_challenge_is_sha256_of_verifier(self):
        """Challenge should be SHA-256 hash of verifier."""
        verifier, challenge = generate_pkce_pair()

        # Compute expected challenge manually
        expected_hash = sha256(verifier.encode("ascii")).digest()
        expected_challenge = (
            urlsafe_b64encode(expected_hash).rstrip(b"=").decode("ascii")
        )

        assert challenge == expected_challenge

    def test_challenge_is_base64url_encoded(self):
        """Challenge should be valid base64url encoded string."""
        _, challenge = generate_pkce_pair()

        # Should only contain base64url characters (no padding)
        assert re.match(r"^[A-Za-z0-9_-]+$", challenge)

        # Should be decodable to 32 bytes (SHA-256 output)
        decoded = urlsafe_b64decode(challenge + "==")
        assert len(decoded) == 32

    def test_generates_unique_pairs(self):
        """Each call should generate a different verifier."""
        verifier1, challenge1 = generate_pkce_pair()
        verifier2, challenge2 = generate_pkce_pair()

        # Verifiers should be different (extremely unlikely to collide)
        assert verifier1 != verifier2
        assert challenge1 != challenge2

    def test_verifier_length_within_spec(self):
        """Verifier should be within PKCE spec (32-96 bytes)."""
        verifier, _ = generate_pkce_pair()

        # Decode to get byte length
        decoded = urlsafe_b64decode(verifier + "==")
        byte_length = len(decoded)

        # Should be 64 bytes (our chosen length)
        assert 32 <= byte_length <= 96
        assert byte_length == 64
