# AGENTS.md — Telegram Expense Bot

## Working environment

| Parameter        | Value              |
| ---------------- | ------------------ |
| Operating System | Windows 11         |
| IDE              | Visual Studio Code |
| IDE Terminal     | PowerShell 7+      |

## Quick start

```powershell
# Start the bot
python main.py

# Generate & upload monthly reports (daily cron job)
python generate_daily_report.py

# Test Gemini parsing directly
python ai_parser.py
```

No test framework, linter, formatter, or typechecker is configured.

## Required env vars (`.env`)

| Var | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `GEMINI_API_KEY` | Google Gemini API key |
| `SUPABASE_URL` | Supabase REST endpoint (ends in `/rest/v1/`) |
| `SUPABASE_KEY` | Supabase anon/service key |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account JSON |
| `DRIVE_FOLDER_ID` | Google Drive folder ID for report uploads |

Each `*.py` module calls `load_dotenv()` independently — all must be run from the project root.

## Architecture

- **Flat module structure** — no packages, no `__init__.py`, just sibling `.py` files.
- `main.py` is the bot entrypoint (uses `python-telegram-bot` v20+, polling mode, not webhooks).
- `ai_parser.py` uses `google-genai` SDK with Gemini 2.5 Flash and **structured output** (`response_schema` JSON schema, not freeform text). Must return `{"intent": ..., "data": {"description", "amount", "date"}}`.
- `supabase_client.py` — hardcodes table name `expenses` with columns `user_id`, `description`, `amount`, `date`.
- `drive_uploader.py` — authenticates via GCP service account (not OAuth). Falls back silently if credentials file missing.
- `generate_daily_report.py` — generates Excel via `pandas` + `openpyxl`, uploads to Drive, deletes local `temp/` file. Meant to run via cron/Task Scheduler.
- `temp/` directory created at runtime by `generate_daily_report.py`.

## Avoid duplication

Check existing code before writing new code. Reuse and extend before creating. If a pattern already exists—same logic, same selector, same helper—use it rather than duplicating it. Extract shared logic into utilities or factories when you find yourself repeating yourself.


**Code readability priority** — Favor clarity and intent-revealing code over brevity or cleverness. Use descriptive names, avoid deeply nested logic, extract meaningful helper functions, and keep functions focused on a single responsibility. Readability is the default; optimize for the next reader, not the writer.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
