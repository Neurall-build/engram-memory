# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""OpenAI-compatible memory API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from database.connection import get_connection
from layers.working import (
    create as working_create,
    get as working_get,
    list_by_user as working_list,
    delete as working_delete,
)
from layers.episodic import (
    create as episodic_create,
    get as episodic_get,
    list_by_user as episodic_list,
    delete as episodic_delete,
)
from layers.semantic import (
    create as semantic_create,
    get as semantic_get,
    list_by_user as semantic_list,
    delete as semantic_delete,
    search as semantic_search,
)
from layers.hive import (
    create as hive_create,
    get as hive_get,
    list_by_org as hive_list,
    delete as hive_delete,
    search as hive_search,
)
from models.memory import (
    MemoryCreateRequest,
    MemoryResponse,
    MemoryListResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryLayer,
)
from api.v1.auth import get_current_user, require_permission, AuthenticatedUser
from engine.compression import get_compression_engine
from engine.importance import get_importance_scorer

router = APIRouter(tags=["memories"])


def _get_db():
    """Dependency that yields a database connection.

    Note: Connections are not closed here because they may be
    singleton (for in-memory DBs). Cleanup is handled elsewhere.
    """
    conn = get_connection()
    yield conn


@router.post("/memories", status_code=201, response_model=MemoryResponse)
async def create_memory(
    req: MemoryCreateRequest,
    conn=Depends(_get_db),
    user: AuthenticatedUser = Depends(require_permission("write")),
):
    """Create or upsert a memory. Routes to the correct layer based on req.layer.

    The user_id is automatically set from the authenticated user context
    if not explicitly provided in the request body.
    """
    # Only override user_id if not explicitly set in the request
    if not req.user_id:
        req.user_id = user.user_id
    if not req.agent_id:
        req.agent_id = user.agent_id

    # Auto-score importance if not provided
    if req.salience is None:
        scorer = get_importance_scorer()
        req.salience = scorer.score(req.content)

    try:
        if req.layer == MemoryLayer.WORKING:
            return working_create(conn, req)
        elif req.layer == MemoryLayer.EPISODIC:
            return episodic_create(conn, req)
        elif req.layer == MemoryLayer.SEMANTIC:
            return semantic_create(conn, req)
        elif req.layer == MemoryLayer.HIVE:
            return hive_create(conn, req)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown layer: {req.layer}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories", response_model=MemoryListResponse)
async def list_memories(
    user_id: Optional[str] = Query(
        None,
        description="User ID to filter memories. If not provided, uses authenticated user.",
    ),
    layer: MemoryLayer = Query(
        default=MemoryLayer.EPISODIC, description="Memory layer to list"
    ),
    profile: Optional[str] = Query(
        None,
        description="Profile name for isolation (e.g., 'work', 'personal', 'project-x')",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    conn=Depends(_get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List memories, filterable by user_id, layer, and profile.

    The user_id is automatically set from the authenticated user context
    if not explicitly provided as a query parameter.
    """
    # Use explicit user_id if provided, otherwise use authenticated user
    effective_user_id = user_id if user_id else user.user_id
    try:
        if layer == MemoryLayer.WORKING:
            items = working_list(conn, effective_user_id, profile)
        elif layer == MemoryLayer.EPISODIC:
            items = episodic_list(conn, effective_user_id, profile)
        elif layer == MemoryLayer.SEMANTIC:
            items = semantic_list(conn, effective_user_id, profile)
        elif layer == MemoryLayer.HIVE:
            # Hive is org-scoped, not user-scoped
            from config import settings

            org_id = settings.hive_org_id
            if not org_id:
                raise HTTPException(
                    status_code=400, detail="Hive org_id not configured"
                )
            items = hive_list(conn, org_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown layer: {layer}")

        # Apply limit
        items = items[:limit]
        return MemoryListResponse(data=items, total=len(items))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: str, conn=Depends(_get_db)):
    """Get a single memory by ID. Tries all layers in order."""
    # Try each layer
    for getter in [working_get, episodic_get, semantic_get, hive_get]:
        try:
            result = getter(conn, memory_id)
            if result is not None:
                return result
        except Exception:
            # If this layer errors, try the next one
            continue

    raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")


@router.post("/memories/search", response_model=MemorySearchResponse)
async def search_memories(
    req: MemorySearchRequest,
    conn=Depends(_get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Vector similarity search. Only works for semantic and hive layers.

    The user_id is automatically set from the authenticated user context
    if not explicitly provided in the request body.
    """
    # Only override user_id if not explicitly set in the request
    if not req.user_id:
        req.user_id = user.user_id

    if req.layer not in (MemoryLayer.SEMANTIC, MemoryLayer.HIVE):
        raise HTTPException(
            status_code=400,
            detail=f"Search only supported for semantic and hive layers, not {req.layer}",
        )

    try:
        if req.layer == MemoryLayer.SEMANTIC:
            return semantic_search(
                conn, req.query, req.user_id, req.top_k, req.min_score
            )
        elif req.layer == MemoryLayer.HIVE:
            org_id = req.org_id
            if not org_id:
                from config import settings

                org_id = settings.hive_org_id
            if not org_id:
                raise HTTPException(
                    status_code=400, detail="org_id is required for hive search"
                )
            return hive_search(conn, req.query, org_id, req.top_k, req.min_score)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=400, detail="Invalid search request")


@router.delete("/memories/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str,
    conn=Depends(_get_db),
    user: AuthenticatedUser = Depends(require_permission("write")),
):
    """Delete a memory. Tries all layers in order."""
    for deleter in [working_delete, episodic_delete, semantic_delete, hive_delete]:
        try:
            if deleter(conn, memory_id):
                return Response(status_code=204)
        except Exception:
            # If this layer errors, try the next one
            continue

    raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")


@router.post("/memories/compress")
async def compress_memories(
    user_id: str = Query(..., description="User ID to compress memories for"),
    min_count: int = Query(10, description="Minimum episodes before compression"),
    max_facts: int = Query(5, description="Maximum facts to generate"),
    conn=Depends(_get_db),
    user: AuthenticatedUser = Depends(require_permission("write")),
):
    """Compress episodic memories into semantic facts."""
    try:
        engine = get_compression_engine()
        result = engine.compress_episodes(user_id, min_count, max_facts)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories/compression-stats")
async def get_compression_stats(
    user_id: str = Query(..., description="User ID to get stats for"),
    conn=Depends(_get_db),
    user: AuthenticatedUser = Depends(require_permission("read")),
):
    """Get compression statistics for a user."""
    try:
        engine = get_compression_engine()
        return engine.get_compression_stats(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
