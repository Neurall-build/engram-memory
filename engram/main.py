# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""ENGRAM — FastAPI app entry point."""

from fastapi import FastAPI
from database.schema import init_db
from api.v1.memories import router as memories_router
from config import settings

app = FastAPI(title="ENGRAM", version="0.1.0", docs_url="/docs")
app.include_router(memories_router, prefix=settings.api_prefix)


@app.on_event("startup")
async def startup():
    """Initialize the database on application startup."""
    init_db()


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
