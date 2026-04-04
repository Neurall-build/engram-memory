# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""Layer 4 — Hive Memory CRUD.

Shared cross-agent memory scoped by org_id.
Only available when ENGRAM_HIVE_ENABLED=true.
"""

import json
import time
import uuid

from fastapi import HTTPException

from config import settings
from engine.decay import refresh_decay_score
from engine.embeddings import embed
from models.memory import (
    MemoryCreateRequest,
    MemoryResponse,
    MemorySearchResult,
    MemorySearchResponse,
)


def _check_hive_enabled():
    """Raise HTTP 403 if hive is not enabled."""
    if not settings.hive_enabled:
        raise HTTPException(status_code=403, detail="Hive memory is not enabled")


def _row_to_response(row: dict) -> MemoryResponse:
    """Convert a database row to MemoryResponse."""
    return MemoryResponse(
        id=row["id"],
        content=row["content"],
        user_id=row["user_id"],
        agent_id=row.get("agent_id"),
        layer="hive",
        metadata=json.loads(row.get("metadata", "{}") or "{}"),
        salience=row.get("salience", 0.5),
        decay_score=row.get("decay_score"),
        access_count=row.get("access_count", 0),
        created_at=row["created_at"],
        last_accessed=row.get("last_accessed"),
        org_id=row.get("org_id"),
        visibility=row.get("visibility"),
    )


def create(conn, req: MemoryCreateRequest) -> MemoryResponse:
    """Create a new hive memory entry with embedding."""
    _check_hive_enabled()

    mem_id = str(uuid.uuid4())
    now = time.time()
    org_id = req.org_id or settings.hive_org_id

    decay_score, access_count, last_accessed = refresh_decay_score(
        salience=req.salience, access_count=0, increment_access=False
    )

    visibility = req.visibility.value if req.visibility else "org"

    conn.execute(
        """
        INSERT INTO hive_memory
            (id, user_id, agent_id, org_id, content, metadata, salience, created_at,
             decay_score, access_count, last_accessed, visibility)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mem_id,
            req.user_id,
            req.agent_id,
            org_id,
            req.content,
            json.dumps(req.metadata),
            req.salience,
            now,
            decay_score,
            access_count,
            last_accessed,
            visibility,
        ),
    )

    # Generate and store embedding
    embedding = embed(req.content)
    embedding_blob = json.dumps(embedding)
    conn.execute(
        "INSERT INTO hive_vectors (memory_id, embedding) VALUES (?, ?)",
        (mem_id, embedding_blob),
    )

    conn.commit()

    row = conn.execute("SELECT * FROM hive_memory WHERE id = ?", (mem_id,)).fetchone()
    return _row_to_response(dict(row))


def get(conn, mem_id: str) -> MemoryResponse | None:
    """Get a hive memory by ID."""
    _check_hive_enabled()

    row = conn.execute("SELECT * FROM hive_memory WHERE id = ?", (mem_id,)).fetchone()
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
        UPDATE hive_memory
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


def list_by_org(conn, org_id: str) -> list[MemoryResponse]:
    """List all hive memories for an org."""
    _check_hive_enabled()

    rows = conn.execute(
        "SELECT * FROM hive_memory WHERE org_id = ? ORDER BY created_at DESC",
        (org_id,),
    ).fetchall()
    return [_row_to_response(dict(r)) for r in rows]


def delete(conn, mem_id: str) -> bool:
    """Delete a hive memory by ID."""
    _check_hive_enabled()

    # Delete from virtual table first
    conn.execute("DELETE FROM hive_vectors WHERE memory_id = ?", (mem_id,))
    cursor = conn.execute("DELETE FROM hive_memory WHERE id = ?", (mem_id,))
    conn.commit()
    return cursor.rowcount > 0


def search(conn, query: str, org_id: str, top_k: int = 10, min_score: float = 0.0) -> MemorySearchResponse:
    """Vector similarity search for hive memories."""
    _check_hive_enabled()

    query_embedding = embed(query)
    embedding_blob = json.dumps(query_embedding)

    rows = conn.execute(
        """
        SELECT hm.*, hv.distance
        FROM hive_vectors hv
        JOIN hive_memory hm ON hv.memory_id = hm.id
        WHERE hm.org_id = ?
        AND hv.embedding MATCH ?
        ORDER BY hv.distance
        LIMIT ?
        """,
        (org_id, embedding_blob, top_k),
    ).fetchall()

    results = []
    for row in rows:
        row_dict = dict(row)
        score = 1.0 - row_dict.get("distance", 0.0)
        if score >= min_score:
            mem_response = _row_to_response(row_dict)
            results.append(MemorySearchResult(memory=mem_response, score=score))

    return MemorySearchResponse(data=results, total=len(results))
