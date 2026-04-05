# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""Pydantic models for memory requests and responses."""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class MemoryLayer(str, Enum):
    """Memory layer types."""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    HIVE = "hive"


class MemoryVisibility(str, Enum):
    """Memory visibility levels for hive memory."""
    ORG = "org"
    TEAM = "team"
    PUBLIC = "public"


class MemoryCreateRequest(BaseModel):
    """Request body for creating a memory."""
    content: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    layer: MemoryLayer = MemoryLayer.EPISODIC
    metadata: dict[str, Any] = Field(default_factory=dict)
    salience: float = Field(default=0.5, ge=0.0, le=1.0)
    org_id: Optional[str] = None
    visibility: Optional[MemoryVisibility] = None


class MemoryResponse(BaseModel):
    """Response body for a single memory."""
    id: str
    content: str
    user_id: str
    agent_id: Optional[str] = None
    layer: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    salience: float
    decay_score: Optional[float] = None
    access_count: Optional[int] = None
    created_at: float
    last_accessed: Optional[float] = None
    org_id: Optional[str] = None
    visibility: Optional[str] = None


class MemoryListResponse(BaseModel):
    """Response body for listing memories — OpenAI style."""
    object: str = "list"
    data: list[MemoryResponse]
    total: int


class MemorySearchRequest(BaseModel):
    """Request body for searching memories."""
    query: str
    user_id: Optional[str] = None
    layer: MemoryLayer = MemoryLayer.SEMANTIC
    top_k: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    org_id: Optional[str] = None


class MemorySearchResult(BaseModel):
    """A single search result."""
    memory: MemoryResponse
    score: float


class MemorySearchResponse(BaseModel):
    """Response body for search results."""
    object: str = "list"
    data: list[MemorySearchResult]
    total: int
