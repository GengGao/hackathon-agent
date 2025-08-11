# HackathonHero

> Offline, local-first AI agent that turns raw brainstorming + files into a polished hackathon submission pack. NO accounts required.

---
## Quick Links
- Demo Video (≤3 min): *(add YouTube link before submission)*
- Live Screens / GIFs: `docs/media/` *(add assets)*
- Gap / Roadmap Tracker: [GAP.md](./GAP.md)
- Primary Category: **Best Local Agent**
- Secondary Framing: **For Humanity** (equitable offline ideation & submission assistance)

---
## 1. Problem & Motivation
Hackathon teams lose disproportionate time structuring ideas, tracking progress, and assembling submission artifacts (idea, tech stack, summary) — especially in bandwidth‑constrained or privacy‑sensitive settings. Online AI tools introduce latency, data exposure, and sometimes go down during crunch time.

**HackathonHero** provides an end‑to‑end, *fully local* assistant: ingest rules & files → brainstorm with a reasoning‑capable model → auto‑derive project idea / tech stack → maintain todos → summarize & (soon) export a ready submission pack — all without external API calls once models are pulled.

---
## 2. What It Does (Feature Summary)
- 🔁 **Streaming Local LLM** (gpt-oss via Ollama) with thinking + tool call transparency (SSE)
- 📜 **Rules-Aware RAG**: chunk + embed rulebook; retrieve top‑k context per query
- ✅ **Intelligent Todo System**: status cycle (pending → in_progress → done), priorities, agent adds tasks via function calls
- 🧠 **Artifact Generation**: derive project idea, recommended tech stack, submission summary from chat history
- 📎 **Multi-File & URL Text Ingestion**: txt / md / pdf / docx / images (OCR) with size & extension guards
- 🧰 **Tool Calling Interface**: LLM invokes structured functions (todos, directory listing, artifact generation)
- 📴 **Offline-First**: after local model + embedding download, zero outward network dependency
- 🗂 **SQLite + Migrations**: reproducible state, artifacts persisted per chat session
- 🗺 **Gap Register (GAP.md)**: transparent roadmap & prioritization
- 🧩 **PWA App Shell**: service worker with runtime caching via vite-plugin-pwa

Planned (near term): export submission pack ZIP; code scaffold tool; auto summarization triggers; light auth/rate limiting.

---
## 3. Category Alignment
| Category | Fit | Notes |
|----------|-----|-------|
| Best Local Agent | Strong | Purely local inference + RAG + agentic tool calls |
| For Humanity | Supportive | Enables teams in low‑connectivity environments to iterate & prepare submissions |
| Wildcard | Possible | If autonomous planning / export pack innovation is emphasized |

---
## 4. Architecture Overview
```
+------------------+        +-----------------+        +-------------------------+
|  React / Vite UI |  SSE   |   FastAPI API   |  IPC   |   Ollama (gpt-oss:* )   |
|  Chat + Todos    +<-------+  /api/* routes  +<------>+  Local Model Runtime    |
|  Markdown Render |        |  Tool Dispatch  |        +-------------------------+
+---------+--------+        |  RAG (FAISS)    |                ^
          |                 |  SQLite (DB)    | Embeddings     |
          | HTTP            +--------+--------+ (MiniLM)       |
          v                           |                       |
  Browser uploads (rules/files)  Project Artifacts & Chat Logs
```
**Key Components**
- `backend/llm.py`: streaming + tool call processing (OpenAI-compatible client to Ollama)
- `backend/rag.py`: rule chunking + FAISS index (SentenceTransformer MiniLM embeddings)
- `backend/tools/`: modular tools package (todos, fs, artifacts, titles, registry)
- `backend/models/db.py`: migrations + persistence helpers
- `frontend/src/*`: chat UI, SSE handling, todo manager

---
## 5. Local Model & Embeddings
- Default LLM: `gpt-oss:20b` (can switch to `gpt-oss:120b` if installed)
- Embedding model: `all-MiniLM-L6-v2` (downloaded once; cached locally)
- No remote OpenAI calls: `AsyncOpenAI` base URL is loopback → Ollama

---
## 6. Quick Start
### Prerequisites
- Python 3.11+
- Node 18+
- Tesseract OCR (for image text extraction)
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
  - Windows (Chocolatey): `choco install tesseract`
- [Ollama](https://ollama.com) installed
- Pull at least one gpt-oss model:
```bash
ollama pull gpt-oss:20b
# (Optional larger)
ollama pull gpt-oss:120b
```

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -c "from models.db import init_db; init_db()"  # run migrations
uvicorn main:app --reload
```
Backend default: http://localhost:8000 (API under `/api`)

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend default: http://localhost:5173

### Environment Variables (Optional)
| Variable | Purpose | Default |
|----------|---------|---------|
| `HACKATHON_DB_PATH` | Custom SQLite path | `backend/data/app.db` |
| `DEBUG_STREAM` | Verbose chunk logging | `0` |

---
## 7. Usage Flow
1. Start Ollama + backend + frontend.
2. Add context: upload files or paste text/URLs in the left panel (calls `/api/context/*`).
3. Chat: brainstorm; agent may propose/add todos via tool calls.
4. Generate artifacts:
   - `POST /api/chat-sessions/{id}/derive-project-idea`
   - `POST /api/chat-sessions/{id}/create-tech-stack`
   - `POST /api/chat-sessions/{id}/summarize-chat-history`
5. Review artifacts.

---
## 8. Tooling (Function Calls)
| Tool | Purpose | Args |
|------|---------|------|
| `list_todos` | Retrieve current tasks | – |
| `add_todo` | Add a task | item |
| `clear_todos` | Remove tasks | – |
| `list_directory` | Safe project dir listing | path? |
| `derive_project_idea` | Create idea artifact | session_id |
| `create_tech_stack` | Create tech stack artifact | session_id |
| `summarize_chat_history` | Submission summary | session_id |

Planned: `export_submission_pack`, `scaffold_code`, `auto_summarize`.

---
## 9. Retrieval Augmented Generation (RAG)
Current:
- Chunking: split on blank-line groups
- Index: FAISS cosine (normalized MiniLM embeddings via IndexFlatIP)
- Query: top‑k=5 similarities (higher = more relevant) returned

Planned improvements:
- Serialize / cache embeddings for faster startup
- Rule chunk highlighting in UI

---
## 10. Data Model (SQLite)
| Table | Purpose |
|-------|---------|
| `todos` | Task list with status, priority, timestamps |
| `chat_sessions` | Logical session container |
| `chat_messages` | Ordered message history |
| `project_artifacts` | Generated artifacts (idea, tech_stack, summary) |
| `app_settings` | Key/value (e.g., persisted current model) |

Migrations live in `backend/migrations/*.sql` and are applied automatically on startup.

---
## 11. Safety & Privacy
- Offline inference (no external API after initial model pulls)
- URL ingestion guarded (size/content-type/timeouts) *(harden further per GAP.md)*
- Path traversal prevention in directory tool (ensures within repo root)
- No PII retention beyond chat content stored locally
Planned: minimal auth token, rate limiting, structured audit logs.

---
## 12. Benchmarks (Placeholder)
Add a short table after measuring:
| Metric | gpt-oss:20b | gpt-oss:120b |
|--------|-------------|--------------|
| First token latency | – | – |
| Tokens/sec (stream) | – | – |
| Peak RAM | – | – |

Script (planned) will capture and record these locally for transparency.

---
## 13. Roadmap Snapshot
See [GAP.md](./GAP.md) for full prioritized list (P0→P3). Immediate targets:
- [x] PWA offline app shell (done)
- [ ] Submission pack export
- [ ] Artifact download endpoints
- [ ] Model benchmarking script
- [ ] Embedding cache

---
## 14. Devpost Submission Checklist
- [ ] Public repo with this README
- [ ] LICENSE file present (MIT)
- [ ] 3‑minute demo video (offline proof + tool calls visible)
- [ ] Screenshots (Chat, Todos, RAG retrieval, Artifacts)
- [ ] Category justification paragraph
- [ ] Model usage & offline explanation
- [ ] Clear run instructions (verified on fresh machine)

---
## 15. Testing
```bash
cd backend
pytest -q
```
Coverage targets (informal): exercise DB migrations, tools, artifact generation, chat session endpoints.

Planned: integration test for SSE streaming + tool call event frames; export pack test.

---
## 16. Limitations
- Heuristic artifact extraction (no semantic clustering yet)
- Retrieval scoring unnormalized (affects ordering for heterogeneous chunk lengths)
- No multi-user isolation / auth
- No export pack (in progress)
- Embeddings recomputed each rules update (sync) — large files slow startup

---
## 17. Future Enhancements
| Area | Enhancement |
|------|-------------|
| Autonomy | Iterative planning loop that converts brainstorming into prioritized roadmap automatically |
| Export | One-click submission ZIP (idea.md, tech_stack.md, summary.md, todos.json, rules_ingested.txt) |
| Code Gen | Safe scoped code scaffold + diff/preview tool |
| Memory | Rolling summarization to keep prompt small |
| UI | Accessibility (ARIA), theming toggle, mobile optimization |
| Offline UX | PWA caching & queued actions |
| Observability | Structured JSON logs, basic Prometheus metrics |
| Fine-tune | Domain-adapted lightweight adapter for mentor tone |

---
## 18. Contributing
1. Fork & branch (`feat/<short-name>`).
2. Add/adjust migrations if schema changes.
3. Run tests + lint (lint config TBD).
4. Update README / GAP.md if introducing new gap or closing one.
5. Open PR referencing gap ID.

---
## 19. Licensing & Attribution
Licensed under the MIT License (see `LICENSE`).
Copyright (c) 2025 Geng Gao.
Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (Apache 2.0).
FAISS, FastAPI, React, Tailwind, Ollama, gpt-oss models — respective licenses apply.

---
## 20. Acknowledgments
- Open gpt-oss initiative
- SentenceTransformers & FAISS for efficient local retrieval
- FastAPI & React communities

---
## 21. Maintainers
Add handle(s) here.

---
## 22. Appendix (API Snapshot)
| Method & Path | Purpose |
|--------------|---------|
| POST `/api/chat-stream` | Stream chat (SSE) with `thinking`, `tool_calls`, `token`, `end` |
| GET `/api/todos` | List todos (`?detailed=true`) |
| POST `/api/todos` | Add todo (form `item`) |
| PUT `/api/todos/{id}` | Update fields (item/status/sort_order) |
| DELETE `/api/todos/{id}` | Delete one |
| DELETE `/api/todos` | Clear all |
| POST `/api/context/rules` | Upload rules/content file (optional `session_id`) |
| GET `/api/chat-sessions` | List sessions (limit/offset) |
| GET `/api/chat-sessions/{id}` | Session detail & messages |
| PUT `/api/chat-sessions/{id}/title` | Rename session |
| DELETE `/api/chat-sessions/{id}` | Delete session |
| POST `/api/chat-sessions/{id}/derive-project-idea` | Generate & store idea |
| POST `/api/chat-sessions/{id}/create-tech-stack` | Generate & store tech stack |
| POST `/api/chat-sessions/{id}/summarize-chat-history` | Generate & store submission summary |
| POST `/api/context/add-text` | Add pasted text or fetched URL snippet (optional `session_id`) |
| GET `/api/context/status` | RAG status (accepts `session_id` query) |
| GET `/api/context/list` | List context rows (accepts `session_id` query) |
| GET `/api/ollama/status` | Model & availability |
| POST `/api/ollama/model` | Switch active model |

---
**Ready to Hack Locally.** Improve what matters, stay offline, submit faster.
