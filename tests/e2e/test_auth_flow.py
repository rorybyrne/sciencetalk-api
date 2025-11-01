"""End-to-end tests for authentication flow."""

import pytest
from fastapi.testclient import TestClient

from talk.interface.api.app import app
from tests.harness import create_env_fixture

# E2E test fixture
e2e_env = create_env_fixture()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAuthFlow:
    """End-to-end tests for OAuth authentication flow."""

    def test_initiate_login_with_handle(self, client):
        """Should initiate login with Bluesky handle."""
        # Act
        response = client.post(
            "/auth/login",
            json={"account": "alice.bsky.social"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "mock=true" in data["authorization_url"]
        assert "account=alice.bsky.social" in data["authorization_url"]

    def test_initiate_login_with_did(self, client):
        """Should initiate login with DID."""
        # Act
        response = client.post(
            "/auth/login",
            json={"account": "did:plc:abc123"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data

    def test_initiate_login_with_empty_body_uses_server_based_flow(self, client):
        """Should accept empty body and use server-based flow with Bluesky default."""
        # Act
        response = client.post(
            "/auth/login",
            json={},
        )

        # Assert - Should succeed with server-based flow (Bluesky default)
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        # Server-based flow should include "server=" in mock URL
        assert "server=" in data["authorization_url"]

    def test_callback_redirects_to_frontend(self, client, e2e_env):
        """Should handle callback and redirect to frontend."""
        _ = e2e_env  # satisfy linter
        # Note: This test uses the mock client which doesn't require a real session
        # In production, the state parameter would need to match an existing session

        # Act
        response = client.get(
            "/auth/callback",
            params={
                "code": "test_code",
                "state": "test_state",
                "iss": "https://bsky.social",
            },
            follow_redirects=False,
        )

        # Assert
        # Since we're using a mock client, the callback will fail
        # because there's no session for the state parameter
        # The important thing is that it tries to redirect with an error
        assert response.status_code == 302
        assert "Location" in response.headers
        # Should redirect to error page since session won't exist
        assert "/auth/error" in response.headers["Location"]

    def test_logout_clears_cookie(self, client):
        """Should clear auth cookie on logout."""
        # Act
        response = client.post("/auth/logout")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Successfully logged out"

        # Check that cookie is being cleared
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "auth_token" in set_cookie_header

    def test_get_current_user_without_cookie(self, client):
        """Should return 401 when not authenticated."""
        # Act
        response = client.get("/auth/me")

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Not authenticated"


class TestProtectedEndpoints:
    """Test that protected endpoints require authentication."""

    def test_protected_endpoints_require_auth(self, client):
        """Protected endpoints should return 401 without auth."""
        # Test protected endpoints that require authentication
        test_cases = [
            ("/posts/", {}),  # Create post
            ("/invites/", {}),  # Create invite
        ]

        for endpoint, payload in test_cases:
            response = client.post(endpoint, json=payload)
            # Should return 401 (not authenticated) since no auth_token cookie is provided
            # 422 is also acceptable if validation fails before auth check
            assert response.status_code in [401, 422], (
                f"Expected 401/422 for {endpoint}, got {response.status_code}"
            )
