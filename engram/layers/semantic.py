# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""Layer 3 — Semantic Memory CRUD.

Distilled facts and patterns with vector similarity search.
"""

import json
import time
import uuid

from engine.decay import refresh_decay_score
from engine.embeddings import embed
from models.memory import (
    MemoryCreateRequest,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResult,
    MemorySearchResponse,
)


def _row_to_response(row: dict) -> MemoryResponse:
    """Convert a database row to MemoryResponse."""
    return MemoryResponse(
        id=row["id"],
        content=row["content"],
        user_id=row["user_id"],
        agent_id=row.get("agent_id"),
        layer="semantic",
        metadata=json.loads(row.get("metadata", "{}") or "{}"),
        salience=row.get("salience", 0.5),
        decay_score=row.get("decay_score"),
        access_count=row.get("access_count", 0),
        created_at=row["created_at"],
        last_accessed=row.get("last_accessed"),
    )


def create(conn, req: MemoryCreateRequest) -> MemoryResponse:
    """Create a new semantic memory entry with embedding."""
    mem_id = str(uuid.uuid4())
    now = time.time()

    decay_score, access_count, last_accessed = refresh_decay_score(
        salience=req.salience, access_count=0, increment_access=False
    )

    conn.execute(
        """
        INSERT INTO semantic_memory
            (id, user_id, agent_id, content, metadata, salience, created_at,
             decay_score, access_count, last_accessed, source_episode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mem_id,
            req.user_id,
            req.agent_id,
            req.content,
            json.dumps(req.metadata),
            req.salience,
            now,
            decay_score,
            access_count,
            last_accessed,
            None,
        ),
    )

    # Generate and store embedding
    embedding = embed(req.content)
    embedding_blob = json.dumps(embedding)
    conn.execute(
        "INSERT INTO semantic_vectors (memory_id, embedding) VALUES (?, ?)",
        (mem_id, embedding_blob),
    )

    conn.commit()

    row = conn.execute("SELECT * FROM semantic_memory WHERE id = ?", (mem_id,)).fetchone()
    return _row_to_response(dict(row))


def get(conn, mem_id: str) -> MemoryResponse | None:
    """Get a semantic memory by ID."""
    row = conn.execute("SELECT * FROM semantic_memory WHERE id = ?", (mem_id,)).fetchone()
    if row is None:
        return None

    row_dict = dict(row)

    # Refresh decay score
    new_decay_score, new_access_count, new_last_accessed = refresh_decay_score(
        salience=row_dict["salience"],
        access_count=row_dict.get("access_count", 0),
        increment_access=True,
    )

    conn.execute(
        """
        UPDATE semantic_memory
        SET decay_score = ?, access_count = ?, last_accessed = ?
        WHERE id = ?
        """,
        (new_decay_score, new_access_count, new_last_accessed, mem_id),
    )
    conn.commit()

    row_dict["decay_score"] = new_decay_score
    row_dict["access_count"] = new_access_count
    row_dict["last_accessed"] = new_last_accessed

    return _row_to_response(row_dict)


def list_by_user(conn, user_id: str) -> list[MemoryResponse]:
    """List all semantic memories for a user."""
    rows = conn.execute(
        "SELECT * FROM semantic_memory WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [_row_to_response(dict(r)) for r in rows]


def delete(conn, mem_id: str) -> bool:
    """Delete a semantic memory by ID."""
    # Delete from virtual table first
    conn.execute("DELETE FROM semantic_vectors WHERE memory_id = ?", (mem_id,))
    cursor = conn.execute("DELETE FROM semantic_memory WHERE id = ?", (mem_id,))
    conn.commit()
    return cursor.rowcount > 0


def search(conn, query: str, user_id: str, top_k: int = 10, min_score: float = 0.0) -> MemorySearchResponse:
    """Vector similarity search for semantic memories.

    Embeds the query, uses sqlite-vec KNN to find nearest neighbours,
    returns results with cosine similarity score.
    """
    query_embedding = embed(query)
    embedding_blob = json.dumps(query_embedding)

    # sqlite-vec KNN syntax with k parameter
    rows = conn.execute(
        """
        SELECT sm.*, sv.distance
        FROM semantic_vectors sv
        JOIN semantic_memory sm ON sv.memory_id = sm.id
        WHERE sm.user_id = ?
        AND sv.embedding MATCH ?
        AND k = ?
        ORDER BY sv.distance
        """,
        (user_id, embedding_blob, top_k),
    ).fetchall()

    results = []
    for row in rows:
        row_dict = dict(row)
        # Convert distance to similarity score (1 - distance)
        score = 1.0 - row_dict.get("distance", 0.0)
        if score >= min_score:
            mem_response = _row_to_response(row_dict)
            results.append(MemorySearchResult(memory=mem_response, score=score))

    return MemorySearchResponse(data=results, total=len(results))
