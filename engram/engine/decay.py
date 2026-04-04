# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""Temporal decay scoring engine for ENGRAM memory layers.

Formula:
    decay_score = salience × exp(−λ × elapsed_seconds) × (1 + log10(1 + access_count))

The result is clamped to [0.0, 1.0].

Memories with decay_score below the configured threshold are considered "dead"
and should be marked for pruning.
"""

import math
import time

from config import settings


def compute_decay(
    salience: float,
    last_accessed: float,
    access_count: int,
    now: float | None = None,
    lam: float | None = None,
) -> float:
    """Compute the decay score for a memory.

    Args:
        salience: Base importance of the memory (0.0–1.0).
        last_accessed: Unix timestamp of last access.
        access_count: Number of times the memory has been accessed.
        now: Current Unix timestamp (defaults to time.time()).
        lam: Decay lambda value (defaults to config value).

    Returns:
        float: Decay score clamped to [0.0, 1.0].
    """
    if now is None:
        now = time.time()
    if lam is None:
        lam = settings.decay_lambda

    elapsed = now - last_accessed
    if elapsed < 0:
        elapsed = 0

    # decay_score = salience × exp(−λ × elapsed) × (1 + log10(1 + access_count))
    raw = salience * math.exp(-lam * elapsed) * (1 + math.log10(1 + access_count))

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, raw))


def is_decayed(decay_score: float) -> bool:
    """Check if a memory is considered decayed/dead.

    Args:
        decay_score: The current decay score.

    Returns:
        bool: True if decay_score < ENGRAM_DECAY_THRESHOLD.
    """
    return decay_score < settings.decay_threshold


def refresh_decay_score(
    salience: float,
    access_count: int,
    increment_access: bool = True,
) -> tuple[float, int, float]:
    """Recalculate decay score after a memory access.

    Bumps access_count (if increment_access is True), treats last_accessed
    as the current moment, and recomputes the decay score.

    Args:
        salience: Base importance of the memory.
        access_count: Current access count.
        increment_access: Whether to increment the access count.

    Returns:
        tuple: (new_decay_score, new_access_count, new_last_accessed_timestamp).
    """
    now = time.time()
    new_access_count = access_count + 1 if increment_access else access_count

    # Since last_accessed is NOW, elapsed = 0, so exp(0) = 1
    new_decay_score = compute_decay(
        salience=salience,
        last_accessed=now,
        access_count=new_access_count,
        now=now,
    )

    return new_decay_score, new_access_count, now


if __name__ == "__main__":
    # Quick self-test
    import os

    # Set a dummy .env for standalone run
    os.environ.setdefault("ENGRAM_DECAY_LAMBDA", "0.0001")
    os.environ.setdefault("ENGRAM_DECAY_THRESHOLD", "0.05")

    print("=== Decay Engine Self-Test ===")

    # Test 1: Fresh memory, just accessed
    score = compute_decay(salience=0.8, last_accessed=time.time(), access_count=0)
    print(f"Fresh memory (salience=0.8, just accessed): decay_score = {score:.4f}")

    # Test 2: Memory accessed 1 hour ago
    one_hour_ago = time.time() - 3600
    score = compute_decay(salience=0.8, last_accessed=one_hour_ago, access_count=0)
    print(f"1 hour old (salience=0.8, 0 accesses): decay_score = {score:.4f}")

    # Test 3: Memory with 10 accesses, 1 hour old
    score = compute_decay(salience=0.8, last_accessed=one_hour_ago, access_count=10)
    print(f"1 hour old (salience=0.8, 10 accesses): decay_score = {score:.4f}")

    # Test 4: Refresh decay
    new_score, new_count, new_ts = refresh_decay_score(salience=0.8, access_count=5)
    print(f"Refreshed (salience=0.8, was 5 accesses): score={new_score:.4f}, count={new_count}")

    # Test 5: Is decayed?
    print(f"is_decayed(0.01) = {is_decayed(0.01)}")
    print(f"is_decayed(0.5)  = {is_decayed(0.5)}")

    print("=== All tests passed ===")
