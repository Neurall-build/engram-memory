# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""Authentication middleware for ENGRAM API."""

import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel

from config import settings
from database.connection import get_connection, execute_write

router = APIRouter(tags=["auth"])


class APIKeyInfo(BaseModel):
    """Information about an API key."""
    key: str
    agent_id: str
    user_id: str
    label: str = ""
    created_at: float
    expires_at: Optional[float] = None
    permissions: str = "read,write"


class APIKeyCreateRequest(BaseModel):
    """Request to create a new API key."""
    agent_id: str
    label: str = ""
    permissions: str = "read,write"
    ttl_seconds: Optional[float] = None  # Optional expiration TTL


class APIKeyResponse(BaseModel):
    """Response containing API key info."""
    key: str
    agent_id: str
    user_id: str
    label: str
    created_at: float
    expires_at: Optional[float] = None
    permissions: str


class AuthenticatedUser(BaseModel):
    """Authenticated user context injected into endpoints."""
    user_id: str
    agent_id: str
    permissions: list[str]


def _validate_api_key(conn, api_key: str) -> Optional[APIKeyInfo]:
    """Validate an API key and return its info, or None if invalid."""
    row = conn.execute(
        "SELECT * FROM api_keys WHERE key = ?", (api_key,)
    ).fetchone()
    if row is None:
        return None

    row_dict = dict(row)

    # Check if key is expired
    if row_dict.get("expires_at") and row_dict["expires_at"] < time.time():
        return None

    return APIKeyInfo(
        key=row_dict["key"],
        agent_id=row_dict["agent_id"],
        user_id=row_dict["user_id"],
        label=row_dict.get("label", ""),
        created_at=row_dict["created_at"],
        expires_at=row_dict.get("expires_at"),
        permissions=row_dict.get("permissions", "read,write"),
    )


def _get_api_key(
    authorization: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None, alias="api_key"),
) -> Optional[str]:
    """Extract API key from Authorization header or query param."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    if api_key:
        return api_key
    return None


def get_current_user(
    api_key: Optional[str] = Depends(_get_api_key),
) -> AuthenticatedUser:
    """Dependency that authenticates the request and returns user context.

    If auth is disabled (ENGRAM_AUTH_ENABLED=false), returns a default user.
    If auth is enabled, validates the API key and returns the associated user.
    """
    # If auth is disabled, allow all requests with a default context
    if not settings.auth_enabled:
        return AuthenticatedUser(
            user_id="anonymous",
            agent_id="default",
            permissions=["read", "write"],
        )

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via 'Authorization: Bearer <key>' header or '?api_key=<key>' query param.",
        )

    conn = get_connection()
    key_info = _validate_api_key(conn, api_key)

    if key_info is None:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")

    return AuthenticatedUser(
        user_id=key_info.user_id,
        agent_id=key_info.agent_id,
        permissions=key_info.permissions.split(","),
    )


def require_permission(permission: str):
    """Dependency factory that requires a specific permission."""
    def _check(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if permission not in user.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' required",
            )
        return user
    return _check


@router.post("/keys", status_code=201, response_model=APIKeyResponse)
async def create_api_key_endpoint(
    req: APIKeyCreateRequest,
    user: AuthenticatedUser = Depends(require_permission("write")),
) -> APIKeyResponse:
    """Create a new API key for an agent."""
    conn = get_connection()
    new_key = f"engram_{uuid.uuid4().hex}"
    now = time.time()
    expires_at = now + req.ttl_seconds if req.ttl_seconds else None

    execute_write(
        conn,
        """
        INSERT INTO api_keys (key, agent_id, user_id, label, created_at, expires_at, permissions)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_key,
            req.agent_id,
            user.user_id,
            req.label,
            now,
            expires_at,
            req.permissions,
        ),
    )
    conn.commit()

    return APIKeyResponse(
        key=new_key,
        agent_id=req.agent_id,
        user_id=user.user_id,
        label=req.label,
        created_at=now,
        expires_at=expires_at,
        permissions=req.permissions,
    )


@router.get("/keys", response_model=list[APIKeyResponse])
async def list_api_keys_endpoint(
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[APIKeyResponse]:
    """List all API keys for the current user."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
        (user.user_id,),
    ).fetchall()

    return [
        APIKeyResponse(
            key=row["key"],
            agent_id=row["agent_id"],
            user_id=row["user_id"],
            label=dict(row).get("label", ""),
            created_at=row["created_at"],
            expires_at=dict(row).get("expires_at"),
            permissions=dict(row).get("permissions", "read,write"),
        )
        for row in rows
    ]


@router.delete("/keys/{key}")
async def revoke_api_key_endpoint(
    key: str,
    user: AuthenticatedUser = Depends(require_permission("write")),
) -> dict:
    """Revoke an API key."""
    conn = get_connection()
    cursor = execute_write(
        conn,
        "DELETE FROM api_keys WHERE key = ? AND user_id = ?",
        (key, user.user_id),
    )
    conn.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"message": "API key revoked"}
