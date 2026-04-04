# Prompt 02 — Config & Database Layer

**Context:** Read ENGRAM_BUILD_SPEC.md. Scaffold from Prompt 01 must exist.

**Task — config.py:**
Implement the Settings class using pydantic-settings.
Read all ENGRAM_ prefixed vars from .env.
Use Field aliases matching the .env keys.

**Task — database/connection.py:**
Implement `get_connection()`:
- Open SQLite at settings.db_path
- Load sqlite-vec extension via `sqlite_vec.load(conn)`
- Set row_factory, WAL mode, foreign keys

**Task — database/schema.py:**
Implement `init_db()` that calls helpers to CREATE TABLE IF NOT EXISTS for:
- working_memory
- episodic_memory
- semantic_memory + semantic_vectors (vec0 virtual table)
- hive_memory + hive_vectors (vec0 virtual table)

Use exact column definitions from the spec.
