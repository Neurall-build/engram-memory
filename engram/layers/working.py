# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""Layer 1 — Working Memory CRUD.

Ephemeral, session-scoped memory with no vector index.
Auto-purged when expired.
"""

import json
import time
import uuid

from models.memory import MemoryCreateRequest, MemoryResponse


def _row_to_response(row: dict) -> MemoryResponse:
    """Convert a database row to MemoryResponse."""
    return MemoryResponse(
        id=row["id"],
        content=row["content"],
        user_id=row["user_id"],
        agent_id=row.get("agent_id"),
        layer="working",
        metadata=json.loads(row.get("metadata", "{}") or "{}"),
        salience=row.get("salience", 0.5),
        decay_score=None,
        access_count=None,
        created_at=row["created_at"],
        last_accessed=None,
    )


def create(conn, req: MemoryCreateRequest) -> MemoryResponse:
    """Create a new working memory entry."""
    mem_id = str(uuid.uuid4())
    now = time.time()
    expires_at = now + 3600  # Default 1 hour TTL for working memory

    conn.execute(
        """
        INSERT INTO working_memory
            (id, user_id, agent_id, content, metadata, salience, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mem_id,
            req.user_id,
            req.agent_id,
            req.content,
            json.dumps(req.metadata),
            req.salience,
            now,
            expires_at,
        ),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM working_memory WHERE id = ?", (mem_id,)).fetchone()
    return _row_to_response(dict(row))


def get(conn, mem_id: str) -> MemoryResponse | None:
    """Get a working memory by ID."""
    row = conn.execute("SELECT * FROM working_memory WHERE id = ?", (mem_id,)).fetchone()
    if row is None:
        return None
    return _row_to_response(dict(row))


def list_by_user(conn, user_id: str) -> list[MemoryResponse]:
    """List all working memories for a user."""
    rows = conn.execute(
        "SELECT * FROM working_memory WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [_row_to_response(dict(r)) for r in rows]


def delete(conn, mem_id: str) -> bool:
    """Delete a working memory by ID."""
    cursor = conn.execute("DELETE FROM working_memory WHERE id = ?", (mem_id,))
    conn.commit()
    return cursor.rowcount > 0


def purge_expired(conn) -> int:
    """Delete all expired working memories. Returns count deleted."""
    now = time.time()
    cursor = conn.execute(
        "DELETE FROM working_memory WHERE expires_at IS NOT NULL AND expires_at < ?",
        (now,),
    )
    conn.commit()
    return cursor.rowcount
