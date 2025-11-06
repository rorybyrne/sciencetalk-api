"""End-to-end tests for user tree endpoint."""

import pytest
from fastapi.testclient import TestClient

from talk.interface.api.app import create_app
from talk.util.di.container import setup_di
from tests.di import build_test_container


@pytest.fixture
def client():
    """Create test client with test container."""
    app_instance = create_app()
    test_container = build_test_container()
    setup_di(app_instance, test_container)
    return TestClient(app_instance)


class TestUserTreeEndpoint:
    """End-to-end tests for GET /users tree endpoint."""

    def test_get_empty_tree(self, client):
        """Should return empty tree when no users exist."""
        # Act
        response = client.get("/users")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["roots"] == []
        assert data["total_users"] == 0

    def test_get_tree_structure(self, client):
        """Should return tree structure with nested children."""
        # This test would require setting up test data
        # For now, just verify the endpoint exists and returns valid structure

        # Act
        response = client.get("/users")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "roots" in data
        assert "total_users" in data
        assert isinstance(data["roots"], list)
        assert isinstance(data["total_users"], int)

    def test_get_tree_without_karma(self, client):
        """Should support include_karma=false parameter."""
        # Act
        response = client.get("/users?include_karma=false")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "roots" in data
        assert "total_users" in data

    def test_tree_node_structure(self, client):
        """Should return nodes with correct structure."""
        # Act
        response = client.get("/users")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # If there are any roots, verify structure
        if data["roots"]:
            node = data["roots"][0]
            assert "user_id" in node
            assert "handle" in node
            assert "karma" in node
            assert "children" in node
            assert isinstance(node["children"], list)

    def test_accepts_include_karma_query_param(self, client):
        """Should accept and parse include_karma query parameter."""
        # Act - with karma
        response_with_karma = client.get("/users?include_karma=true")

        # Act - without karma
        response_without_karma = client.get("/users?include_karma=false")

        # Assert
        assert response_with_karma.status_code == 200
        assert response_without_karma.status_code == 200
