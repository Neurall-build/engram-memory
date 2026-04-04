# ENGRAM

A local-first, persistent memory engine for AI agents. Stores, retrieves, and decays memories across 4 layers. OpenAI Memory API compatible.

## Quickstart

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run the server
uvicorn main:app --reload

# Open API docs
# http://127.0.0.1:8000/docs
```

## 4-Layer Memory Architecture

| Layer | Name | Description |
|-------|------|-------------|
| 1 | Working | Ephemeral, session-scoped. Auto-purged when expired. |
| 2 | Episodic | Time-stamped events. What happened, when, with whom. Decays over time. |
| 3 | Semantic | Distilled facts and patterns. Long-lived with vector search. |
| 4 | Hive | Shared cross-agent memory. Scoped by organization. |

Memories flow upward: Working → Episodic → Semantic based on access patterns and manual promotion.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/memories | Create or upsert a memory |
| GET | /v1/memories | List memories (filter by user_id, layer) |
| GET | /v1/memories/{id} | Get a single memory by ID |
| POST | /v1/memories/search | Vector similarity search |
| DELETE | /v1/memories/{id} | Delete a memory |

### Create Memory

```bash
curl -X POST http://127.0.0.1:8000/v1/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "The user prefers dark mode",
    "user_id": "user_abc",
    "layer": "episodic",
    "salience": 0.8
  }'
```

### Search Memories

```bash
curl -X POST http://127.0.0.1:8000/v1/memories/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "user UI preferences",
    "user_id": "user_abc",
    "layer": "semantic",
    "top_k": 10
  }'
```

## Decay Engine

Memories naturally fade over time. Each memory has a decay score that decreases based on how long it's been since last access and how often it's been used. Frequently accessed memories stay strong; forgotten ones fade and are eventually pruned. This mimics how biological memory works — use it or lose it.

## Configuration

All settings are read from environment variables (or `.env` file) with the `ENGRAM_` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `ENGRAM_DB_PATH` | `./engram.db` | Path to the SQLite database |
| `ENGRAM_ENV` | `development` | Environment name |
| `ENGRAM_EMBED_DIM` | `1536` | Embedding vector dimension |
| `ENGRAM_DECAY_LAMBDA` | `0.0001` | Decay rate parameter |
| `ENGRAM_DECAY_THRESHOLD` | `0.05` | Score below which memory is "dead" |
| `ENGRAM_API_PREFIX` | `/v1` | API route prefix |
| `ENGRAM_HOST` | `127.0.0.1` | Server bind address |
| `ENGRAM_PORT` | `8000` | Server port |
| `ENGRAM_HIVE_ENABLED` | `false` | Enable shared cross-agent memory |
| `ENGRAM_HIVE_ORG_ID` | | Organization ID for hive memory |

## Running Tests

```bash
pytest tests/ -v
```

## License

Business Source License 1.1 (BSL 1.1)

Copyright (c) 2026 Neurall. All rights reserved.

See the LICENSE file for full terms.
