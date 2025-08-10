# HackathonHero Backend

FastAPI + local LLM orchestration + retrieval + tooling + persistence.

> This directory hosts the offline agent service: streaming chat (SSE), rule‑aware retrieval, function (tool) execution, and artifact generation. See root `README.md` for product overview; this file focuses on backend internals and ops.

---
## Contents
- [Stack](#stack)
- [Service Responsibilities](#service-responsibilities)
- [Architecture](#architecture)
- [Data Flow (Chat Request)](#data-flow-chat-request)
- [Tools / Function Calling](#tools--function-calling)
- [RAG Pipeline](#rag-pipeline)
- [Database & Migrations](#database--migrations)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [API Endpoints](#api-endpoints)
- [Adding a New Tool](#adding-a-new-tool)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Performance Notes](#performance-notes)
- [Planned Enhancements](#planned-enhancements)

---
## Stack
| Layer | Tech | Notes |
|-------|------|-------|
| Web Framework | FastAPI | Async, OpenAPI generation |
| Server | Uvicorn | Auto-reload in dev |
| LLM Access | `openai` compatible client → Ollama | Local gpt-oss models |
| Embeddings | `sentence-transformers` MiniLM | Lightweight, CPU friendly |
| Vector Index | FAISS (IndexFlatIP cosine) | Plans: embedding persistence |
| DB | SQLite | File: `data/app.db` |
| ORM | Raw SQL + helpers | Explicit migrations in `.sql` |
| Streaming | Server-Sent Events (SSE) | Thinking + tool_calls + tokens |

---
## Service Responsibilities
1. Accept multi-modal text inputs (user text, uploaded file text extraction, limited URL fetch) and append to chat history.
2. Retrieve relevant rule chunks for context (RAG) and construct system prompt.
3. Stream model response with transparent reasoning (“thinking”) and tool call events.
4. Execute tool calls (todos, artifacts, directory listing) and feed results back into model if multiple rounds needed.
5. Persist sessions, messages, todos, and generated project artifacts.

---
## Architecture
```
Client (React) ──POST /api/chat-stream (multipart form)──▶ Router
  ▲                                                   │
  │ (SSE: thinking/tool_calls/tokens/end)             │
  │                                                   ▼
State (SQLite) ◀── models/db helpers ── FastAPI Router ──▶ llm.generate_stream
                                   │                    │
                                   └──> RuleRAG (FAISS) ┴──> Ollama (gpt-oss model)
```

---
## Data Flow (Chat Request)
1. User sends form: (`user_input`, optional `files[]`, `url_text`, optional `session_id`).
2. Files OCR / text extracted (pdfminer, python-docx, pytesseract, plain text) within guardrails (size + extension).
3. Chat message persisted (`role=user`).
4. Top-k rule chunks retrieved via FAISS and embedded in system prompt.
5. `generate_stream` begins streaming tokens:
   - Yields `thinking` frames (guarded for repetition/length)
   - Yields `tool_calls` frame if functions invoked (before execution)
   - Executes tool(s) → appends tool results as messages → (optional subsequent round)
   - Yields `content` tokens
6. Final assistant message persisted.

---
## Tools / Function Calling
Declared in `tools.py` via `get_tool_schemas()` (OpenAI function schema). Execution dispatch: `FUNCTION_DISPATCH` mapping → simple lambdas. Additions only require:
1. Implement function logic (pure, deterministic if possible).
2. Add schema entry.
3. Add dispatch line.
4. (Optional) Frontend UI support.

Current tools: todos CRUD (`list_todos`, `add_todo`, `clear_todos`), `list_directory`, artifact generators (`derive_project_idea`, `create_tech_stack`, `summarize_chat_history`).

---
## RAG Pipeline
1. Load rules file (`docs/rules.txt`).
2. Chunk: split on blank-line groups (simple, fast). *Planned:* semantic splitting & token length capping.
3. Embed chunks (MiniLM) at startup & on rules replacement.
4. Query: encode user query; cosine similarity (dot product of normalized vectors) search top-k=5.
5. Returned similarity scores + raw chunks inserted into system prompt (and separately streamed to client for UI display).

Planned upgrades: embedding cache serialization (avoid recompute), chunk metadata (ids + char offsets), highlight mapping.

---
## Database & Migrations
Migrations: `backend/migrations/00X_*.sql` executed in lexical order; applied versions stored in `schema_migrations`. Additional table `app_settings` created programmatically for small key/value (e.g., persisted current model selection).

Tables (summary):
- `todos`
- `chat_sessions`
- `chat_messages`
- `project_artifacts`
- `app_settings`

Helper functions: see `models/db.py` (CRUD wrappers with safe context management and idempotent schema initialization `init_db()`).

---
## Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `HACKATHON_DB_PATH` | Override database path | `backend/data/app.db` |
| `DEBUG_STREAM` | Print raw streaming chunks to stdout | `0` |

---
## Running Locally
```bash
# From repo root
cd backend
python -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -c "from models.db import init_db; init_db()"
uvicorn main:app --reload
```
API root: http://localhost:8000/api
SSE events emitted by `/api/chat-stream`: `session_info`, `rule_chunks`, `thinking`, `tool_calls`, `token`, `end`.

Ollama must be running locally with at least `gpt-oss:20b` pulled.

---
## API Endpoints
See root README (API Snapshot) for table. This backend README focuses on extension guidelines.

---
## Adding a New Tool
1. Implement Python function (pure if possible) in `tools.py`.
2. Add JSON schema entry inside `get_tool_schemas()`.
3. Add execution mapping in `FUNCTION_DISPATCH`.
4. (Optional) Create matching frontend UI component if user-triggered.
5. (Optional) Add tests under `tests/` verifying tool behavior.

---
## Development Workflow
- Keep business logic side-effect-light for deterministic tests.
- Add migration instead of mutating prior migration files after publish.
- Use small helper functions for DB operations (avoid inline SQL inside route handlers).
- Avoid blocking calls within streaming generator (perform IO async or prefetch). *Current image/PDF extraction executes before streaming begins.*

---
## Testing
Pytest tests live in `backend/tests`. Run:
```bash
pytest -q
```
Suggested additional tests (open gaps):
- SSE stream handshake & event ordering
- Tool call round-trip (model stub / monkeypatch)
- RAG retrieval correctness (inject synthetic rules file)

---
## Performance Notes
- Embedding of rules is O(N) at startup; acceptable for small/medium rule sets. Plan to cache embeddings.
- Streaming generator includes guardrails (reasoning token truncation by char count & repetition). Fine-tune thresholds if models evolve.
- SQLite write pattern: many small inserts; acceptable locally. For concurrency > ~50 RPS, consider WAL + batch summarization.

---
## Planned Enhancements
| Area | Plan |
|------|------|
| Retrieval | Chunk metadata & highlighting, embedding cache persistence |
| Export | ZIP pack endpoint with artifacts & todos |
| Auth | Simple API key / per-session token |
| Summarization | Automatic rolling memory compression |
| Tooling | Code scaffold + file write sandbox |
| Observability | Structured JSON logs & basic metrics |
| Embeddings | Cache file keyed by rules hash |

---
## License
See root project LICENSE (MIT).

---
Happy hacking. Extend safely, keep it offline.
