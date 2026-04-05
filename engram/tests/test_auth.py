# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""API tests for ENGRAM authentication endpoints.

NOTE: These tests run with auth ENABLED. Because settings are cached
at import time, we need to reload the modules after setting env vars.
"""

import importlib
import os
import sys
import time

import pytest

# Add project root to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set test env vars with auth ENABLED BEFORE any imports
os.environ["ENGRAM_DB_PATH"] = ":memory:"
os.environ["ENGRAM_ENV"] = "test"
os.environ["ENGRAM_EMBED_DIM"] = "1536"
os.environ["ENGRAM_DECAY_LAMBDA"] = "0.0001"
os.environ["ENGRAM_DECAY_THRESHOLD"] = "0.05"
os.environ["ENGRAM_API_PREFIX"] = "/v1"
os.environ["ENGRAM_HIVE_ENABLED"] = "false"
os.environ["ENGRAM_HIVE_ORG_ID"] = ""
os.environ["ENGRAM_AUTH_ENABLED"] = "true"
os.environ["ENGRAM_DEFAULT_API_KEY"] = "engram_test_bootstrap_key"

# Reload modules that may have been imported by test_api.py
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith(("config", "main", "database", "api", "layers", "models", "engine")):
        del sys.modules[mod_name]

from fastapi.testclient import TestClient
from main import app
from database.schema import init_db
from database.connection import get_connection, reset_connection
from config import settings, reload_settings

# Reload settings to pick up env vars
reload_settings()

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh in-memory DB for each test."""
    reset_connection()
    init_db()
    yield
    # Cleanup: reset the singleton connection for the next test
    reset_connection()


def test_bootstrap_key_seeded():
    """Verify the default API key is seeded on init_db."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM api_keys WHERE key = ?", ("engram_test_bootstrap_key",)
    ).fetchone()
    assert row is not None
    assert dict(row)["agent_id"] == "bootstrap"
    assert dict(row)["user_id"] == "admin"
    assert dict(row)["permissions"] == "read,write"


def test_create_api_key_with_bootstrap():
    """POST /v1/keys — create a new API key using the bootstrap key."""
    response = client.post(
        "/v1/keys",
        json={"agent_id": "test-agent", "label": "test key"},
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["agent_id"] == "test-agent"
    assert data["user_id"] == "admin"
    assert data["label"] == "test key"
    assert data["key"].startswith("engram_")
    assert data["permissions"] == "read,write"
    assert data["expires_at"] is None  # No TTL set


def test_create_api_key_with_ttl():
    """POST /v1/keys — create a new API key with expiration TTL."""
    response = client.post(
        "/v1/keys",
        json={"agent_id": "test-agent", "label": "expiring key", "ttl_seconds": 3600},
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["expires_at"] is not None
    assert data["expires_at"] > data["created_at"]


def test_list_api_keys():
    """GET /v1/keys — list all API keys for the current user."""
    # Create a key first
    client.post(
        "/v1/keys",
        json={"agent_id": "test-agent", "label": "key 1"},
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    client.post(
        "/v1/keys",
        json={"agent_id": "test-agent", "label": "key 2"},
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )

    response = client.get(
        "/v1/keys",
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    assert response.status_code == 200
    data = response.json()
    # Should have bootstrap key + 2 created keys = 3
    assert len(data) == 3


def test_revoke_api_key():
    """DELETE /v1/keys/{key} — revoke an API key."""
    # Create a key
    create_resp = client.post(
        "/v1/keys",
        json={"agent_id": "test-agent", "label": "to revoke"},
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    key_to_revoke = create_resp.json()["key"]

    # Revoke it
    response = client.delete(
        f"/v1/keys/{key_to_revoke}",
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "API key revoked"

    # Verify it's gone
    response = client.get(
        "/v1/keys",
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    data = response.json()
    assert not any(k["key"] == key_to_revoke for k in data)


def test_revoke_nonexistent_key():
    """DELETE /v1/keys/{key} — nonexistent key → assert 404."""
    response = client.delete(
        "/v1/keys/engram_nonexistent_key",
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    assert response.status_code == 404


def test_unauthorized_request():
    """Request without API key → assert 401."""
    response = client.post(
        "/v1/keys",
        json={"agent_id": "test-agent"},
    )
    assert response.status_code == 401


def test_invalid_api_key():
    """Request with invalid API key → assert 401."""
    response = client.post(
        "/v1/keys",
        json={"agent_id": "test-agent"},
        headers={"Authorization": "Bearer engram_invalid_key"},
    )
    assert response.status_code == 401


def test_memory_creation_with_auth():
    """POST /v1/memories — create memory with auth → user_id injected from auth context."""
    response = client.post(
        "/v1/memories",
        json={
            "content": "Auth test memory",
            "layer": "episodic",
        },
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    assert response.status_code == 201
    data = response.json()
    # user_id should be "admin" from the bootstrap key
    assert data["user_id"] == "admin"


def test_memory_listing_with_auth():
    """GET /v1/memories — list memories with auth → filtered by authenticated user."""
    # Create a memory
    client.post(
        "/v1/memories",
        json={
            "content": "List test memory",
            "layer": "episodic",
        },
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )

    response = client.get(
        "/v1/memories",
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


def test_memory_search_with_auth():
    """POST /v1/memories/search — search with auth → user_id injected from auth context."""
    # Create a semantic memory
    client.post(
        "/v1/memories",
        json={
            "content": "User likes Python programming",
            "layer": "semantic",
        },
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )

    response = client.post(
        "/v1/memories/search",
        json={
            "query": "Python programming",
            "layer": "semantic",
            "top_k": 10,
        },
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert isinstance(data["data"], list)


def test_memory_deletion_with_auth():
    """DELETE /v1/memories/{id} — delete memory with auth."""
    # Create a memory
    create_resp = client.post(
        "/v1/memories",
        json={
            "content": "Delete test memory",
            "layer": "episodic",
        },
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    mem_id = create_resp.json()["id"]

    # Delete it
    response = client.delete(
        f"/v1/memories/{mem_id}",
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(
        f"/v1/memories/{mem_id}",
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    assert response.status_code == 404


def test_api_key_via_query_param():
    """Test API key can be passed via query param instead of header."""
    response = client.get(
        "/v1/keys",
        params={"api_key": "engram_test_bootstrap_key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1  # At least the bootstrap key


def test_expired_api_key():
    """Test that an expired API key is rejected."""
    # Create a key that expires immediately (TTL = 0)
    create_resp = client.post(
        "/v1/keys",
        json={"agent_id": "test-agent", "label": "expiring key", "ttl_seconds": 0.001},
        headers={"Authorization": "Bearer engram_test_bootstrap_key"},
    )
    short_lived_key = create_resp.json()["key"]

    # Wait for it to expire
    time.sleep(0.01)

    # Try to use it
    response = client.get(
        "/v1/keys",
        headers={"Authorization": f"Bearer {short_lived_key}"},
    )
    assert response.status_code == 401
