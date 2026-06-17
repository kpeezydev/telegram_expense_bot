# AGENTS.md — Telegram Expense Bot

**Keep this file up to date** — When you add, rename, or remove source files, update the `## Project Structure` section. When you change the tech stack, update the `## Tech Stack` table. Keeping AGENTS.md accurate saves every future session from re-discovering the codebase.

## Working environment

| Parameter        | Value              |
| ---------------- | ------------------ |
| Operating System | Windows 11         |
| IDE              | Visual Studio Code |
| IDE Terminal     | PowerShell 7+      |


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

## Project Structure

<!-- update when files change -->

```
telegram_expense_bot/
├── .github/workflows/       # CI: manual-dispatch GitHub Action
├── ai_parser.py             # Gemini NL → structured JSON parser (intent + data)
├── main.py                  # Bot entrypoint: Telegram handlers + FastAPI webhook
├── metrics.py               # Prometheus metric definitions (counters, histograms, gauges)
├── supabase_client.py       # Supabase CRUD (expenses table)
├── drive_uploader.py        # Google Drive upload via service account
├── generate_daily_report.py # Monthly Excel report via pandas → Drive upload
├── register_webhook.py      # Telegram setWebhook registration script
├── deploy.ps1               # One-command Cloud Run deploy + webhook register
├── grafana/
│   └── dashboards/
│       └── bot-overview.json  # Grafana dashboard (request rates, latency, errors)
├── AGENTS.md                # Agent instructions (this file)
├── DEPLOY.md                # Cloud Run deployment + Grafana Cloud setup walkthrough
├── Dockerfile               # python:3.12-slim + gunicorn + uvicorn
├── requirements.txt         # Python dependencies
├── .env.example             # Template for all required env vars
├── .gitignore               # Git exclusion rules
├── .dockerignore            # Docker build exclusions
└── .gitattributes           # LF normalization
```

## Tech Stack

| Layer                | Technology                                    |
| -------------------- | --------------------------------------------- |
| Runtime              | Python 3.12                                   |
| Bot Framework        | python-telegram-bot v20+                      |
| NLU / Parsing        | Google Gemini (`google-genai`, `gemini-2.5-flash-lite`) |
| Database             | Supabase (Postgres via REST client)           |
| File Storage         | Google Drive API (service account)            |
| Reports              | pandas + openpyxl (Excel export)              |
| Webhook Server       | FastAPI + uvicorn + gunicorn                  |
| Deployment           | Docker → Google Cloud Run (min 0, max 1)      |
| Secrets              | Google Cloud Secret Manager                   |
| CI                   | GitHub Actions (manual trigger, polling mode) |
