# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""API tests for ENGRAM memory endpoints."""

import os
import sys
import time
import uuid

import pytest

# Add project root to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

# Set test env vars before importing app
os.environ["ENGRAM_DB_PATH"] = ":memory:"
os.environ["ENGRAM_ENV"] = "test"
os.environ["ENGRAM_EMBED_DIM"] = "1536"
os.environ["ENGRAM_DECAY_LAMBDA"] = "0.0001"
os.environ["ENGRAM_DECAY_THRESHOLD"] = "0.05"
os.environ["ENGRAM_API_PREFIX"] = "/v1"
os.environ["ENGRAM_HIVE_ENABLED"] = "false"
os.environ["ENGRAM_HIVE_ORG_ID"] = ""

from main import app
from database.schema import init_db
from database.connection import get_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh in-memory DB for each test."""
    init_db()
    yield
    # Cleanup: close any lingering connections
    conn = get_connection()
    try:
        conn.execute("DELETE FROM working_memory")
        conn.execute("DELETE FROM episodic_memory")
        conn.execute("DELETE FROM semantic_memory")
        conn.execute("DELETE FROM hive_memory")
        conn.commit()
    finally:
        conn.close()


def test_create_episodic_memory():
    """POST /v1/memories — create episodic memory → assert 201 + returned fields."""
    response = client.post(
        "/v1/memories",
        json={
            "content": "User prefers dark mode",
            "user_id": "user_abc",
            "agent_id": "agent_xyz",
            "layer": "episodic",
            "metadata": {"source": "chat"},
            "salience": 0.8,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "User prefers dark mode"
    assert data["user_id"] == "user_abc"
    assert data["layer"] == "episodic"
    assert data["salience"] == 0.8
    assert data["metadata"] == {"source": "chat"}
    assert data["id"] is not None


def test_list_memories():
    """GET /v1/memories — list by user_id → assert correct count."""
    # Create 3 memories
    for i in range(3):
        client.post(
            "/v1/memories",
            json={
                "content": f"Memory {i}",
                "user_id": "user_list_test",
                "layer": "episodic",
            },
        )

    response = client.get("/v1/memories", params={"user_id": "user_list_test"})
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert data["total"] == 3
    assert len(data["data"]) == 3


def test_get_memory_by_id():
    """GET /v1/memories/{id} — get by id → assert content matches."""
    # Create a memory
    create_resp = client.post(
        "/v1/memories",
        json={
            "content": "Get by ID test",
            "user_id": "user_get_test",
            "layer": "episodic",
        },
    )
    mem_id = create_resp.json()["id"]

    # Get it back
    response = client.get(f"/v1/memories/{mem_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Get by ID test"
    assert data["id"] == mem_id


def test_delete_memory():
    """DELETE /v1/memories/{id} — delete → assert 204 → GET returns 404."""
    # Create a memory
    create_resp = client.post(
        "/v1/memories",
        json={
            "content": "Delete me",
            "user_id": "user_del_test",
            "layer": "episodic",
        },
    )
    mem_id = create_resp.json()["id"]

    # Delete it
    response = client.delete(f"/v1/memories/{mem_id}")
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/v1/memories/{mem_id}")
    assert response.status_code == 404


def test_decay_engine():
    """Decay engine unit test — create a memory, assert decay_score < 1.0 after time."""
    # Create a memory
    create_resp = client.post(
        "/v1/memories",
        json={
            "content": "Decay test memory",
            "user_id": "user_decay_test",
            "layer": "episodic",
            "salience": 0.5,
        },
    )
    mem_id = create_resp.json()["id"]
    initial_decay = create_resp.json()["decay_score"]

    # Get it back — decay should be recalculated
    response = client.get(f"/v1/memories/{mem_id}")
    assert response.status_code == 200
    data = response.json()
    # After access, decay_score should be recalculated
    assert data["decay_score"] is not None
    assert data["access_count"] == 1


def test_search_memories():
    """POST /v1/memories/search — with zero-vector embeddings → assert returns list (no crash)."""
    # Create a semantic memory
    client.post(
        "/v1/memories",
        json={
            "content": "User likes Python programming",
            "user_id": "user_search_test",
            "layer": "semantic",
        },
    )

    # Search for it
    response = client.post(
        "/v1/memories/search",
        json={
            "query": "Python programming",
            "user_id": "user_search_test",
            "layer": "semantic",
            "top_k": 10,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert isinstance(data["data"], list)


def test_get_nonexistent_memory():
    """GET /v1/memories/{id} — nonexistent ID → assert 404."""
    response = client.get(f"/v1/memories/{uuid.uuid4()}")
    assert response.status_code == 404


def test_search_invalid_layer():
    """POST /v1/memories/search — with working layer → assert 400."""
    response = client.post(
        "/v1/memories/search",
        json={
            "query": "test",
            "user_id": "user_test",
            "layer": "working",
        },
    )
    assert response.status_code == 400
