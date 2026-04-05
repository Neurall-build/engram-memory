# ENGRAM Skill for OpenClaw

Persistent memory skill for OpenClaw agents. Connects your agent to ENGRAM's 4-layer memory system.

## Installation

### Prerequisites
- ENGRAM server running (see [ENGRAM README](../README.md))
- OpenClaw installed

### Install the Skill

```bash
# Copy this skill to your OpenClaw skills directory
cp -r skills/engram ~/.openclaw/skills/engram

# Or symlink for development
ln -s $(pwd)/skills/engram ~/.openclaw/skills/engram
```

### Configure

Edit `~/.openclaw/config.yaml` and add:

```yaml
skills:
  - name: engram
    config:
      server_url: http://127.0.0.1:8000
      api_key: engram_your_key_here  # Optional, if auth enabled
      user_id: your_user_id
```

## Usage

Once installed, your OpenClaw agent will automatically have access to these memory commands:

- `@engram remember <content>` — Store a memory
- `@engram recall <query>` — Search memories
- `@engram list` — List recent memories
- `@engram forget <memory_id>` — Delete a memory

## How It Works

This skill connects OpenClaw to ENGRAM's REST API:
1. Commands are translated to HTTP requests
2. ENGRAM stores/retrieves memories with decay scoring
3. Results are formatted for the agent's context

## Memory Layers

| Layer | Use Case |
|-------|----------|
| working | Temporary session data |
| episodic | Events and experiences |
| semantic | Facts and knowledge |

## Troubleshooting

- **Connection refused**: Make sure ENGRAM server is running (`uvicorn main:app`)
- **401 Unauthorized**: Check your API key in config
- **404 Not Found**: Verify the server URL is correct
