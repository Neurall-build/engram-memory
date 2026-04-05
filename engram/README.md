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
| GET | /v1/tools | OpenAI-compatible tool definitions |
| POST | /v1/keys | Create an API key |
| GET | /v1/keys | List API keys |
| DELETE | /v1/keys/{key} | Revoke an API key |

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

## Agent Integration

ENGRAM is designed to pair with AI agent platforms. Here's how to connect your agent:

### OpenAI Function Calling

1. **Fetch tool definitions** from `GET /v1/tools`
2. **Pass them to your agent** as the `tools` parameter
3. **Handle function calls** by calling the corresponding ENGRAM endpoints

```python
import openai
import requests

# 1. Get tool definitions
tools = requests.get("http://127.0.0.1:8000/v1/tools").json()["tools"]

# 2. Call OpenAI with tools
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Remember that I like Python"}],
    tools=tools,
)

# 3. Handle tool calls
for tool_call in response.choices[0].message.tool_calls:
    if tool_call.function.name == "engram_create_memory":
        args = json.loads(tool_call.function.arguments)
        result = requests.post(
            "http://127.0.0.1:8000/v1/memories",
            json=args,
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
```

### Direct HTTP API

Any agent that can make HTTP requests can use ENGRAM directly:

```python
# Store a memory
requests.post("http://127.0.0.1:8000/v1/memories", json={
    "content": "User's name is Alice",
    "user_id": "alice",
    "layer": "semantic",
    "salience": 0.9
})

# Search memories before responding
results = requests.post("http://127.0.0.1:8000/v1/memories/search", json={
    "query": "user name",
    "user_id": "alice",
    "layer": "semantic"
})
```

### Authentication (Optional)

By default, ENGRAM runs without authentication. To enable multi-tenant mode:

```bash
# Enable auth
ENGRAM_AUTH_ENABLED=true

# Generate your first API key (one-time setup)
curl -X POST http://127.0.0.1:8000/v1/keys \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "my-agent", "label": "primary key"}'

# Use the key in requests
curl -X POST http://127.0.0.1:8000/v1/memories \
  -H "Authorization: Bearer engram_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"content": "...", "user_id": "user_1"}'
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
| `ENGRAM_AUTH_ENABLED` | `false` | Enable API key authentication |
| `ENGRAM_DEFAULT_API_KEY` | | Pre-seeded API key for first setup |

## Running Tests

```bash
pytest tests/ -v
```

## License

MIT License - Non-Commercial Use

Copyright (c) 2026 Neurall. All rights reserved.

Free for personal/individual use. Commercial use requires a license. Contact: neurall.company@gmail.com
