# Prompt 08 — Tests

**Context:** Read ENGRAM_BUILD_SPEC.md. All prior files must exist.

**Task — tests/test_api.py:**
Write pytest tests using FastAPI TestClient (httpx) with an in-memory SQLite DB.

Cover:
1. `POST /v1/memories` — create episodic memory → assert 201 + returned fields
2. `GET /v1/memories` — list by user_id → assert correct count
3. `GET /v1/memories/{id}` — get by id → assert content matches
4. `DELETE /v1/memories/{id}` — delete → assert 204 → GET returns 404
5. Decay engine unit test — create a memory, mock time 1 hour later, assert decay_score < 1.0
6. `POST /v1/memories/search` — with zero-vector embeddings → assert returns list (no crash)

Use a pytest fixture that creates a fresh in-memory DB per test.
