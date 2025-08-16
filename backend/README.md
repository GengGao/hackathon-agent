# HackathonHero Backend

FastAPI + local LLM orchestration + retrieval + tooling + persistence.

> This directory hosts the offline agent service: streaming chat (SSE), rule‑aware retrieval, function (tool) execution, and artifact generation. See root `README.md` for product overview; this file focuses on backend internals and ops.

---
## Contents
- [HackathonHero Backend](#hackathonhero-backend)
  - [Contents](#contents)
  - [Stack](#stack)
  - [Service Responsibilities](#service-responsibilities)
  - [Architecture](#architecture)
  - [Data Flow (Chat Request)](#data-flow-chat-request)
  - [Tools / Function Calling](#tools--function-calling)
  - [RAG Pipeline](#rag-pipeline)
  - [Database \& Migrations](#database--migrations)
  - [Environment Variables](#environment-variables)
  - [Running Locally](#running-locally)
  - [API Endpoints](#api-endpoints)
  - [Adding a New Tool](#adding-a-new-tool)
  - [Development Workflow](#development-workflow)
  - [Testing](#testing)
  - [Performance Notes](#performance-notes)
  - [Planned Enhancements](#planned-enhancements)
  - [License](#license)

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
2. Files OCR / text extracted (pdfminer, python‑docx, pytesseract, plain text) within guardrails (size + extension).
3. Chat message persisted (`role=user`).
4. **RuleRAG** loads the current rules file (`docs/rules.txt`), splits it into *blank‑line groups*, embeds each chunk with MiniLM, and caches the resulting vectors in `data/embeddings/rules_{hash}.pkl`.
   - If the rules file is replaced, the hash changes and the cache is regenerated.
5. Top‑k rule chunks are retrieved via a **FAISS IndexFlatIP** (cosine similarity) and inserted into the system prompt.
   - The FAISS index itself is kept in memory; only the embeddings are persisted to disk to avoid recomputation on every restart.
6. `generate_stream` begins streaming tokens:
   - Yields `thinking` frames (guarded for repetition/length)
   - Yields `tool_calls` frame if functions invoked (before execution)
   - Executes tool(s) → appends tool results as messages → (optional subsequent round)
   - Yields `content` tokens
7. Final assistant message persisted.

---
## Tools / Function Calling
Declared in `tools/registry.py` via `get_tool_schemas()` (OpenAI function schema) with lazy `call_tool` dispatch. Additions only require:
1. Implement function logic in an appropriate module under `backend/tools/` (pure if possible).
2. Add schema entry in `tools/registry.py`.
3. Ensure `call_tool` resolves your function name.
4. (Optional) Frontend UI support.

Current tools: todos CRUD (`list_todos`, `add_todo`, `clear_todos`), `list_directory`, artifact generators (`derive_project_idea`, `create_tech_stack`, `summarize_chat_history`), `generate_chat_title`.

---
## RAG Pipeline
The rule‑based retrieval is implemented by the `RuleRAG` class (see `models/rag.py`).
Key steps:

1. **Load Rules** – `docs/rules.txt` (or a replacement file) is read once at startup or when the file is updated.
2. **Chunking** – Simple blank‑line grouping (fast). Future work: semantic split & token‑length capping.
3. **Embedding** – Each chunk is encoded with MiniLM (`sentence-transformers/all-MiniLM-L6-v2`).
   - Vectors are L2‑normalised so that cosine similarity reduces to a dot product.
4. **Caching** – The embeddings and the FAISS index are serialised to `data/embeddings/` keyed by a SHA‑256 hash of the rules file.
   - On startup, if a cache file exists for the current hash, it is loaded; otherwise embeddings are recomputed and the cache written.
5. **Querying** – The user query is embedded, normalised, and searched against the in‑memory FAISS `IndexFlatIP`.
   - `top_k=5` by default; each returned chunk is paired with its similarity score.
6. **Prompt Construction** – The top‑k chunks (with scores) are inserted into the system prompt and also streamed to the client as `rule_chunks` events for UI display.

**Vector Index** – FAISS (IndexFlatIP) is used as the vector database. No external service is required; the index lives entirely in memory, with optional persistence via the embedding cache.

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
```powershell
# From repo root
cd backend

# Create a virtual environment
python -m venv .venv

# ------------------ Windows (PowerShell) ------------------
# Activate the venv in PowerShell (pwsh.exe)
. .venv\Scripts\Activate.ps1

# ------------------ Windows (cmd.exe) ------------------
# If you use the classic cmd shell instead of PowerShell
.venv\Scripts\activate

# ------------------ macOS / Linux ------------------
# Activate the venv on macOS or Linux
source .venv/bin/activate

# Install Python requirements
pip install -r requirements.txt

# Optional (recommended for image OCR): install Tesseract system dependency
# Windows (Chocolatey):
#   choco install tesseract
# macOS (Homebrew):
#   brew install tesseract

# Initialize the database (creates sqlite file and schema)
python -c "from models.db import init_db; init_db()"

# Run the dev server
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
1. Implement Python function in `backend/tools/<area>.py`.
2. Add JSON schema entry inside `tools/registry.py:get_tool_schemas()`.
3. Ensure name is handled in `tools/registry.py:call_tool`.
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
