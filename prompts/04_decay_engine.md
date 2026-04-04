# Prompt 04 — Temporal Decay Engine

**Context:** Read ENGRAM_BUILD_SPEC.md → "Temporal Decay Engine" section.

**Task — engine/decay.py:**
Implement three functions:

1. `compute_decay(salience, last_accessed, access_count, now=None, lam=None) -> float`
   - Formula: salience × exp(−λ × elapsed) × (1 + log10(1 + access_count))
   - Clamp result to [0.0, 1.0]
   - `elapsed` = now - last_accessed in seconds

2. `is_decayed(decay_score) -> bool`
   - Returns True if decay_score < settings.decay_threshold

3. `refresh_decay_score(salience, access_count, increment_access=True) -> tuple[float, int, float]`
   - Bumps access_count if increment_access=True
   - Recomputes decay score treating last_accessed as NOW (memory was just accessed)
   - Returns (new_decay_score, new_access_count, new_last_accessed_timestamp)

Add clear docstrings with the formula written out.
Include a standalone test block at the bottom under `if __name__ == "__main__"`.
