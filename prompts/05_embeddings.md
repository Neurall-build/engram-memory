# Prompt 05 — Embedding Abstraction

**Context:** Read ENGRAM_BUILD_SPEC.md. Stealth mode applies — do not name the provider in any public-facing string.

**Task — engine/embeddings.py:**
Implement the embedding abstraction:

1. `embed(text: str) -> list[float]`
   - If ENGRAM_EMBED_MODEL env var is empty → return zero vector (dev mode)
   - If ENGRAM_EMBED_MODEL starts with "text-embedding" → use OpenAI embeddings
   - Vector dimension must match settings.embed_dim

2. `_zero_vector() -> list[float]`
   - Returns [0.0] * settings.embed_dim

3. Error handling: if the embedding call fails for any reason, log a WARNING and return zero vector. Never raise to the caller.

Keep provider logic inside private functions.
