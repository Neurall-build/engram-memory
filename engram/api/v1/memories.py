# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""OpenAI-compatible memory API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from database.connection import get_connection
from layers.working import create as working_create, get as working_get, list_by_user as working_list, delete as working_delete
from layers.episodic import create as episodic_create, get as episodic_get, list_by_user as episodic_list, delete as episodic_delete
from layers.semantic import create as semantic_create, get as semantic_get, list_by_user as semantic_list, delete as semantic_delete, search as semantic_search
from layers.hive import create as hive_create, get as hive_get, list_by_org as hive_list, delete as hive_delete, search as hive_search
from models.memory import (
    MemoryCreateRequest,
    MemoryResponse,
    MemoryListResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryLayer,
)

router = APIRouter(tags=["memories"])


def _get_db():
    """Dependency that yields a database connection."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@router.post("/memories", status_code=201, response_model=MemoryResponse)
async def create_memory(req: MemoryCreateRequest, conn=Depends(_get_db)):
    """Create or upsert a memory. Routes to the correct layer based on req.layer."""
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
    user_id: str = Query(..., description="User ID to filter memories"),
    layer: MemoryLayer = Query(default=MemoryLayer.EPISODIC, description="Memory layer to list"),
    limit: int = Query(default=50, ge=1, le=200),
    conn=Depends(_get_db),
):
    """List memories, filterable by user_id and layer."""
    try:
        if layer == MemoryLayer.WORKING:
            items = working_list(conn, user_id)
        elif layer == MemoryLayer.EPISODIC:
            items = episodic_list(conn, user_id)
        elif layer == MemoryLayer.SEMANTIC:
            items = semantic_list(conn, user_id)
        elif layer == MemoryLayer.HIVE:
            # Hive is org-scoped, not user-scoped
            from config import settings
            org_id = settings.hive_org_id
            if not org_id:
                raise HTTPException(status_code=400, detail="Hive org_id not configured")
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
        result = getter(conn, memory_id)
        if result is not None:
            return result

    raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")


@router.post("/memories/search", response_model=MemorySearchResponse)
async def search_memories(req: MemorySearchRequest, conn=Depends(_get_db)):
    """Vector similarity search. Only works for semantic and hive layers."""
    if req.layer not in (MemoryLayer.SEMANTIC, MemoryLayer.HIVE):
        raise HTTPException(status_code=400, detail=f"Search only supported for semantic and hive layers, not {req.layer}")

    try:
        if req.layer == MemoryLayer.SEMANTIC:
            if not req.user_id:
                raise HTTPException(status_code=400, detail="user_id is required for semantic search")
            return semantic_search(conn, req.query, req.user_id, req.top_k, req.min_score)
        elif req.layer == MemoryLayer.HIVE:
            org_id = req.org_id
            if not org_id:
                from config import settings
                org_id = settings.hive_org_id
            if not org_id:
                raise HTTPException(status_code=400, detail="org_id is required for hive search")
            return hive_search(conn, req.query, org_id, req.top_k, req.min_score)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=400, detail="Invalid search request")


@router.delete("/memories/{memory_id}", status_code=204)
async def delete_memory(memory_id: str, conn=Depends(_get_db)):
    """Delete a memory. Tries all layers in order."""
    for deleter in [working_delete, episodic_delete, semantic_delete, hive_delete]:
        if deleter(conn, memory_id):
            return Response(status_code=204)

    raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
