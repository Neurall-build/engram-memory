# Prompt 03 — Pydantic Models

**Context:** Read ENGRAM_BUILD_SPEC.md.

**Task — models/memory.py:**
Implement all Pydantic v2 models:
- `MemoryLayer` (Enum: working, episodic, semantic, hive)
- `MemoryVisibility` (Enum: org, team, public)
- `MemoryCreateRequest` — matches POST /v1/memories body from spec
- `MemoryResponse` — matches the response shape from spec
- `MemoryListResponse` — wraps list with OpenAI-style {object, data, total}
- `MemorySearchRequest` — matches POST /v1/memories/search body
- `MemorySearchResult` — {memory: MemoryResponse, score: float}
- `MemorySearchResponse` — wraps list of results

All models use Pydantic v2 syntax (`model_config`, not `class Config`).
