# Prompt 06 — Memory Layer CRUD

**Context:** Read ENGRAM_BUILD_SPEC.md → "4-Layer Memory Architecture" section.
Each layer file follows the same pattern but has layer-specific behavior.

**Task — layers/working.py:**
- `create(conn, req: MemoryCreateRequest) -> MemoryResponse`
- `get(conn, id: str) -> MemoryResponse | None`
- `list_by_user(conn, user_id: str) -> list[MemoryResponse]`
- `delete(conn, id: str) -> bool`
- `purge_expired(conn) -> int`  — deletes rows where expires_at < now(), returns count deleted

**Task — layers/episodic.py:**
Same CRUD plus:
- On every `get()` call → call `refresh_decay_score()` and UPDATE the row in DB
- `promote_to_semantic(conn, id: str) -> str`  — copies row to semantic_memory, sets promoted=1, returns new semantic id

**Task — layers/semantic.py:**
Same CRUD plus:
- On `create()` → call `embed(content)` and INSERT into `semantic_vectors` virtual table
- `search(conn, query: str, user_id: str, top_k: int) -> list[MemorySearchResult]`
  - Embed the query
  - Use sqlite-vec KNN syntax to find nearest neighbours
  - Return results with cosine similarity score

**Task — layers/hive.py:**
Same as semantic but scoped by `org_id` instead of `user_id`.
Only works if `settings.hive_enabled == True`, otherwise raise HTTP 403.

All functions use the raw sqlite3.Connection — no ORM.
Use `uuid.uuid4()` for IDs, `time.time()` for timestamps.
