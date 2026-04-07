# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""Layer 2 — Episodic Memory CRUD.

Time-stamped events with decay scoring and promotion to semantic memory.
Decay score is recalculated on every read.
"""

import json
import time
import uuid

from engine.decay import refresh_decay_score
from models.memory import MemoryCreateRequest, MemoryResponse


def _row_to_response(row: dict) -> MemoryResponse:
    """Convert a database row to MemoryResponse."""
    return MemoryResponse(
        id=row["id"],
        content=row["content"],
        user_id=row["user_id"],
        agent_id=row.get("agent_id"),
        layer="episodic",
        metadata=json.loads(row.get("metadata", "{}") or "{}"),
        salience=row.get("salience", 0.5),
        decay_score=row.get("decay_score"),
        access_count=row.get("access_count", 0),
        created_at=row["created_at"],
        last_accessed=row.get("last_accessed"),
        profile=row.get("profile"),
        emotion=row.get("emotion"),
        emotion_intensity=row.get("emotion_intensity"),
    )


def create(conn, req: MemoryCreateRequest) -> MemoryResponse:
    """Create a new episodic memory entry."""
    mem_id = str(uuid.uuid4())
    now = time.time()

    # Initial decay score calculation
    decay_score, access_count, last_accessed = refresh_decay_score(
        salience=req.salience, access_count=0, increment_access=False
    )

    conn.execute(
        """
        INSERT INTO episodic_memory
            (id, user_id, agent_id, content, metadata, salience, created_at, expires_at,
             decay_score, access_count, last_accessed, promoted, is_compressed, profile, emotion, emotion_intensity)
        VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, 0, 0, ?, ?, ?)
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
            req.profile,
            req.emotion.value if req.emotion else None,
            req.emotion_intensity,
        ),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM episodic_memory WHERE id = ?", (mem_id,)
    ).fetchone()
    return _row_to_response(dict(row))


def get(conn, mem_id: str) -> MemoryResponse | None:
    """Get an episodic memory by ID. Recalculates decay score on every access."""
    row = conn.execute(
        "SELECT * FROM episodic_memory WHERE id = ?", (mem_id,)
    ).fetchone()
    if row is None:
        return None

    row_dict = dict(row)

    # Refresh decay score — memory was just accessed
    new_decay_score, new_access_count, new_last_accessed = refresh_decay_score(
        salience=row_dict["salience"],
        access_count=row_dict.get("access_count", 0),
        increment_access=True,
    )

    # Update the row in DB
    conn.execute(
        """
        UPDATE episodic_memory
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


def list_by_user(conn, user_id: str, profile: str = None) -> list[MemoryResponse]:
    """List episodic memories for a user, optionally filtered by profile."""
    if profile:
        rows = conn.execute(
            "SELECT * FROM episodic_memory WHERE user_id = ? AND profile = ? ORDER BY created_at DESC",
            (user_id, profile),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM episodic_memory WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [_row_to_response(dict(r)) for r in rows]


def delete(conn, mem_id: str) -> bool:
    """Delete an episodic memory by ID."""
    cursor = conn.execute("DELETE FROM episodic_memory WHERE id = ?", (mem_id,))
    conn.commit()
    return cursor.rowcount > 0


def promote_to_semantic(conn, mem_id: str) -> str:
    """Promote an episodic memory to semantic memory.

    Copies the row to semantic_memory, sets promoted=1, returns new semantic id.
    """
    row = conn.execute(
        "SELECT * FROM episodic_memory WHERE id = ?", (mem_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Episodic memory {mem_id} not found")

    row_dict = dict(row)
    semantic_id = str(uuid.uuid4())

    conn.execute(
        """
        INSERT INTO semantic_memory
            (id, user_id, agent_id, content, metadata, salience, created_at,
             decay_score, access_count, last_accessed, source_episode, profile, emotion, emotion_intensity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            semantic_id,
            row_dict["user_id"],
            row_dict.get("agent_id"),
            row_dict["content"],
            row_dict.get("metadata", "{}"),
            row_dict["salience"],
            row_dict["created_at"],
            row_dict.get("decay_score", 1.0),
            row_dict.get("access_count", 0),
            row_dict.get("last_accessed"),
            mem_id,
            row_dict.get("profile"),
            row_dict.get("emotion"),
            row_dict.get("emotion_intensity"),
        ),
    )

    # Mark episodic as promoted
    conn.execute("UPDATE episodic_memory SET promoted = 1 WHERE id = ?", (mem_id,))
    conn.commit()

    return semantic_id
