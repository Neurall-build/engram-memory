# How to Use This Pack with Codex / Kilocode

## Setup (do this once)
1. Create a new folder: `engram/`
2. Open it in VS Code
3. Install Kilocode extension (or use Codex in your IDE)
4. Copy `ENGRAM_BUILD_SPEC.md` into the root of your `engram/` folder

---

## Build Order — Follow the Numbered Prompts

Run one prompt at a time. Wait for the AI to finish before moving to the next.

| Step | File | What gets built |
|------|------|-----------------|
| 01 | prompts/01_scaffold.md | Folder structure + empty stubs |
| 02 | prompts/02_config_and_db.md | Config, SQLite connection, schema |
| 03 | prompts/03_models.md | All Pydantic models |
| 04 | prompts/04_decay_engine.md | Temporal decay engine |
| 05 | prompts/05_embeddings.md | Embedding abstraction |
| 06 | prompts/06_layers.md | All 4 memory layer CRUDs |
| 07 | prompts/07_api.md | REST API endpoints |
| 08 | prompts/08_tests.md | Test suite |
| 09 | prompts/09_readme.md | README |

---

## How to Use Each Prompt

### In Kilocode (VS Code):
1. Open the prompt `.md` file
2. Select all text → copy
3. Open Kilocode chat
4. Paste the prompt and say: **"Use ENGRAM_BUILD_SPEC.md as context. Execute this prompt."**
5. Review the generated code before accepting

### In OpenAI Codex:
1. Start a new task
2. Attach `ENGRAM_BUILD_SPEC.md` as context
3. Paste the prompt content as the instruction
4. Run

---

## After Each Step — Quick Checks

After Prompt 02:
```bash
cd engram && pip install -r requirements.txt
python -c "from database.schema import init_db; init_db(); print('DB OK')"
```

After Prompt 07:
```bash
uvicorn main:app --reload
# Open http://127.0.0.1:8000/docs — you should see all 5 endpoints
```

After Prompt 08:
```bash
pytest tests/ -v
```

---

## When the AI Goes Off-Spec

If Codex/Kilocode generates something that contradicts the spec, say:
> "This violates the spec. Re-read ENGRAM_BUILD_SPEC.md section [X] and fix [Y]."

Common drift to watch for:
- Using Postgres or any cloud DB → **reject**, force SQLite only
- Adding an ORM (SQLAlchemy) → **reject**, raw sqlite3 only
- Naming the embedding provider in comments/logs → **reject**, keep it hidden
- Adding HIVE logic when ENGRAM_HIVE_ENABLED=false → **reject**, must 403
