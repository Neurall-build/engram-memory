# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""Embedding abstraction for ENGRAM — provider hidden.

If no model is configured, returns zero vectors (dev mode).
If a text-embedding model is configured, uses the appropriate provider.
All errors are caught, logged as WARNING, and return zero vectors.
"""

import logging
import os

from config import settings

logger = logging.getLogger(__name__)


def _zero_vector() -> list[float]:
    """Return a zero vector of the configured embedding dimension.

    Returns:
        list[float]: Zero vector [0.0] * embed_dim.
    """
    return [0.0] * settings.embed_dim


def _embed_openai(text: str) -> list[float]:
    """Generate an embedding using the OpenAI-style API.

    Args:
        text: The text to embed.

    Returns:
        list[float]: Embedding vector.
    """
    from openai import OpenAI

    client = OpenAI()
    response = client.embeddings.create(
        model=os.environ.get("ENGRAM_EMBED_MODEL", "text-embedding-3-small"),
        input=text,
    )
    return response.data[0].embedding


def embed(text: str) -> list[float]:
    """Generate an embedding vector for the given text.

    If ENGRAM_EMBED_MODEL env var is empty → returns zero vector (dev mode).
    If ENGRAM_EMBED_MODEL starts with "text-embedding" → uses OpenAI embeddings.
    On any error → logs WARNING and returns zero vector.

    Args:
        text: The text to embed.

    Returns:
        list[float]: Embedding vector of dimension settings.embed_dim.
    """
    model = os.environ.get("ENGRAM_EMBED_MODEL", "")

    # Dev mode: no model configured
    if not model:
        return _zero_vector()

    try:
        if model.startswith("text-embedding"):
            return _embed_openai(text)
        else:
            # Unknown model type — fall back to zero vector
            logger.warning("Unknown embedding model: %s, using zero vector", model)
            return _zero_vector()
    except Exception:
        logger.warning("Embedding call failed for text (length=%d), returning zero vector", len(text))
        return _zero_vector()
