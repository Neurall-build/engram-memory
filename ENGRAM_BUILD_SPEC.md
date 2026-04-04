# ENGRAM — Master Build Specification
> Feed this file to Codex / Kilocode as the root context for every session.

## What is ENGRAM?
ENGRAM is a local-first, persistent memory engine for AI agents.
It stores, retrieves, and decays memories across 4 layers.
It is built with Python + FastAPI and is OpenAI Memory API compatible.

---

## Hard Constraints (never violate these)
- Storage: SQLite + sqlite-vec ONLY. No Postgres, no Redis, no cloud DBs.
- Language: Python 3.11+
- Framework: FastAPI
- License: BSL 1.1 — include header in every file
- Do NOT reveal embedding model or runtime internals in docs, logs, or comments
- No external services required for core operations (local-first)

---

## Project Structure
```
engram/
├── main.py                  # FastAPI app entry point
├── config.py                # Pydantic settings from .env
├── requirements.txt
├── .env.example
├── database/
│   ├── connection.py        # SQLite connection + sqlite-vec loader
│   └── schema.py            # CREATE TABLE statements for all 4 layers
├── models/
│   └── memory.py            # Pydantic request/response models
├── engine/
│   ├── decay.py             # Temporal decay scoring engine
│   └── embeddings.py        # Embedding abstraction (provider hidden)
├── layers/
│   ├── working.py           # Layer 1 CRUD
│   ├── episodic.py          # Layer 2 CRUD + decay update on access
│   ├── semantic.py          # Layer 3 CRUD + vector insert/search
│   └── hive.py              # Layer 4 CRUD + vector insert/search
├── api/
│   └── v1/
│       └── memories.py      # OpenAI-compatible REST endpoints
└── tests/
    └── test_api.py
```

---

## 4-Layer Memory Architecture

### Layer 1 — Working Memory
- Ephemeral. Session-scoped. No vector index.
- Has `expires_at` field. Auto-purged when expired.
- Promote to Episodic by calling `promote_to_episodic(id)`.

### Layer 2 — Episodic Memory
- Time-stamped events. What happened, when, with whom.
- Has `decay_score`, `access_count`, `last_accessed`.
- Decay score recalculated on every read.
- Promote to Semantic when `access_count >= 5` or manually.

### Layer 3 — Semantic Memory
- Distilled facts and patterns. Long-lived.
- MUST have an embedding vector stored in `semantic_vectors` (sqlite-vec virtual table).
- Supports vector similarity search via sqlite-vec.
- Has `source_episode` FK back to the originating episodic memory.

### Layer 4 — Hive Memory
- Shared cross-agent memory. Scoped by `org_id`.
- Only available when `ENGRAM_HIVE_ENABLED=true`.
- Has `visibility` field: "org" | "team" | "public".
- Vector search via `hive_vectors` virtual table.

---

## Temporal Decay Engine (engine/decay.py)

Formula:
```
decay_score = salience × exp(−λ × seconds_since_last_access) × (1 + log10(1 + access_count))
```
Clamped to [0.0, 1.0].

- `λ` (lambda) = ENGRAM_DECAY_LAMBDA from config (default 0.0001)
- Memories with `decay_score < ENGRAM_DECAY_THRESHOLD` are "dead" — mark for pruning
- Call `refresh_decay_score()` on every memory retrieval — updates score, access_count, last_accessed in DB

---

## SQLite Schema

### working_memory
| column | type | notes |
|---|---|---|
| id | TEXT PK | UUID |
| user_id | TEXT | required |
| agent_id | TEXT | optional |
| content | TEXT | the memory text |
| metadata | TEXT | JSON string |
| salience | REAL | 0.0–1.0 |
| created_at | REAL | Unix timestamp |
| expires_at | REAL | Unix timestamp, nullable |

### episodic_memory
Same as working + adds:
| decay_score | REAL | default 1.0 |
| access_count | INTEGER | default 0 |
| last_accessed | REAL | Unix timestamp |
| promoted | INTEGER | 0 or 1 |

### semantic_memory
Same as episodic + adds:
| source_episode | TEXT | FK to episodic_memory.id, nullable |

Virtual table: `semantic_vectors` using sqlite-vec vec0:
```sql
CREATE VIRTUAL TABLE semantic_vectors USING vec0(
    memory_id TEXT PRIMARY KEY,
    embedding float[{EMBED_DIM}]
);
```

### hive_memory
Same as episodic + adds:
| org_id | TEXT | required |
| visibility | TEXT | "org" | "team" | "public" |

Virtual table: `hive_vectors` (same pattern as semantic_vectors)

---

## REST API — OpenAI Memory API Compatible

Base prefix: `/v1`

| Method | Path | Description |
|---|---|---|
| POST | /v1/memories | Create or upsert a memory |
| GET | /v1/memories | List memories (filter by user_id, layer) |
| GET | /v1/memories/{id} | Get a single memory by ID |
| POST | /v1/memories/search | Vector similarity search |
| DELETE | /v1/memories/{id} | Delete a memory |

### POST /v1/memories — Request body
```json
{
  "content": "The user prefers dark mode",
  "user_id": "user_abc",
  "agent_id": "agent_xyz",
  "layer": "episodic",
  "metadata": {},
  "salience": 0.8
}
```

### POST /v1/memories/search — Request body
```json
{
  "query": "user UI preferences",
  "user_id": "user_abc",
  "layer": "semantic",
  "top_k": 10,
  "min_score": 0.0
}
```

### Response shape (all endpoints)
```json
{
  "id": "mem_uuid",
  "content": "...",
  "user_id": "...",
  "layer": "episodic",
  "metadata": {},
  "salience": 0.8,
  "decay_score": 0.94,
  "access_count": 3,
  "created_at": 1712100000.0,
  "last_accessed": 1712180000.0
}
```

---

## Config (config.py — Pydantic Settings)
Read all values from `.env` file:
```
ENGRAM_DB_PATH=./engram.db
ENGRAM_ENV=development
ENGRAM_EMBED_DIM=1536
ENGRAM_DECAY_LAMBDA=0.0001
ENGRAM_DECAY_THRESHOLD=0.05
ENGRAM_API_PREFIX=/v1
ENGRAM_HOST=127.0.0.1
ENGRAM_PORT=8000
ENGRAM_HIVE_ENABLED=false
ENGRAM_HIVE_ORG_ID=
```

---

## main.py — Entry Point
```python
from fastapi import FastAPI
from database.schema import init_db
from api.v1.memories import router as memories_router
from config import settings

app = FastAPI(title="ENGRAM", version="0.1.0", docs_url="/docs")
app.include_router(memories_router, prefix=settings.api_prefix)

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
```

---

## BSL 1.1 License Header
Add to the top of every `.py` file:
```python
# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.
```
