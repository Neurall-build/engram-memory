# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""ENGRAM - FastAPI app entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from database.schema import init_db
from api.v1.memories import router as memories_router
from api.v1.tools import router as tools_router
from api.v1.auth import router as auth_router
from config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup, cleanup on shutdown."""
    init_db()
    logger.info("ENGRAM started")
    yield
    logger.info("ENGRAM stopped")


app = FastAPI(title="ENGRAM", version="0.1.0", docs_url="/docs", lifespan=lifespan)
app.include_router(memories_router, prefix=settings.api_prefix)
app.include_router(tools_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
