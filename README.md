# HackathonHero

> Offline, local-first AI agent that turns raw brainstorming + files into a polished hackathon submission pack. NO accounts required.

![Main UI](screenshots/HackathonHero%20Diagram.png)

---
## Quick Links
- Demo Video (≤3 min): *(add YouTube link before submission)*
- Live Screens / Screenshots: `screenshots/` *(see below)*
- Gap / Roadmap Tracker: [GAP.md](./GAP.md)
- Primary Category: **Best Local Agent**
- Secondary Framing: **For Humanity** (equitable offline ideation & submission assistance)

---
## 1. Problem & Motivation
Hackathon teams lose disproportionate time structuring ideas, tracking progress, and assembling submission artifacts (idea, tech stack, summary) — especially in bandwidth‑constrained or privacy‑sensitive settings. Online AI tools introduce latency, data exposure, and sometimes go down during crunch time.

**HackathonHero** provides an end‑to‑end, *fully local* assistant: ingest rules & files → brainstorm with a reasoning‑capable model → auto‑derive project idea / tech stack → maintain todos → export a ready submission pack — all without external API calls once models are pulled.

---
## 2. What It Does (Feature Summary)
- 🚀 **Complete One-Liner Setup & Run**: Run one command → HackathonHero opens in browser ready to use!
- 🔁 **Streaming Local LLM** (gpt-oss via Ollama or LM Studio) with thinking + tool call transparency (SSE)
- 📜 **Rules-Aware RAG**: chunk + embed rulebook; retrieve top‑k context per query; cached embeddings for warm starts
- ✅ **Intelligent Todo System**: status cycle (pending → in_progress → done), agent adds tasks via function calls, session-scoped
- 🧠 **Artifact Generation**: derive project idea, recommended tech stack, submission summary from chat history
- 📎 **Multi-File & URL Text Ingestion**: txt / md / pdf / docx / images (OCR) with size & extension guards
- 🧰 **Tool Calling Interface**: LLM invokes structured functions (todos, directory listing, artifact generation, session management)
- 📴 **Offline-First**: after local model + embedding download, zero outward network dependency
- 🗂 **SQLite + Migrations**: reproducible state, artifacts persisted per chat session with 7 migrations
- 📦 **Complete Export System**: One-click ZIP generation with idea.md, tech_stack.md, summary.md, todos.json, rules_ingested.txt, session_metadata.json
- 🗺 **Gap Register (GAP.md)**: transparent roadmap & prioritization with 6/16 gaps completed
- 🧩 **PWA App Shell**: service worker with runtime caching via vite-plugin-pwa, offline-capable

---
## 3. Category Alignment
| Category | Fit | Notes |
|----------|-----|-------|
| Best Local Agent | **Primary** | Purely local inference + RAG + agentic tool calls + complete automation |
| For Humanity | **Secondary** | Enables teams in low‑connectivity environments + democratizes AI education |
| Wildcard | Possible | If autonomous planning / export pack innovation is emphasized |

📋 **Detailed Justifications**: See [CATEGORY_JUSTIFICATION.md](./CATEGORY_JUSTIFICATION.md) for comprehensive category justifications with technical details and strategic positioning.

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
- Default LLM: `gpt-oss:20b` (switchable to other installed `gpt-oss:*` models)
- Embedding model: `all-MiniLM-L6-v2` or `paraphrase-MiniLM-L3-v2` (downloaded once; cached locally)
- No remote OpenAI calls: `AsyncOpenAI` base URL is loopback → Ollama

---
## 6. Quick Start

### 🚀 One-Liner Setup & Run (Recommended for Hackathons)
Choose your platform and run the complete automated setup script:

#### MacOS
```bash
curl -fsSL https://raw.githubusercontent.com/genggao/hackathon-agent/main/setup-macos.sh | bash
```

#### Linux (Ubuntu/Debian/CentOS/Arch)
```bash
curl -fsSL https://raw.githubusercontent.com/genggao/hackathon-agent/main/setup-linux.sh | bash
```

#### Windows (PowerShell as Administrator)
```powershell
# Download and run the setup script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/genggao/hackathon-agent/main/setup-windows.ps1" -OutFile "setup-windows.ps1"
.\setup-windows.ps1
```

**What these scripts do (COMPLETE automation):**
- ✅ Install Python 3.11+, Node.js 22+, Tesseract OCR
- ✅ Install and configure Ollama
- ✅ Clone the HackathonHero repository
- ✅ Set up backend virtual environment and dependencies
- ✅ Set up frontend dependencies
- ✅ Initialize the database
- ✅ **AUTO-START Ollama service**
- ✅ **AUTO-DOWNLOAD default model (gpt-oss:20b)**
- ✅ **AUTO-START backend server (http://localhost:8000)**
- ✅ **AUTO-START frontend server (http://localhost:5173)**
- ✅ **AUTO-OPEN browser to HackathonHero**

**Result:** After running the script, HackathonHero opens automatically in your browser - ready to use! 🎉

---

### Manual Setup
#### Prerequisites
- Python 3.11+
- Node.js 22+
- Tesseract OCR (for image text extraction)
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
  - Windows (Chocolatey): `choco install tesseract`
- [Ollama](https://ollama.com) installed and running
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
python -c "from models.db import init_db; init_db()"  # run migrations (idempotent)
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

Models and embeddings download once and are cached locally. If Ollama is not available, model list falls back to `gpt-oss:20b`, `gpt-oss:120b` until Ollama is reachable.

---
## 7. Usage Flow

![Main Chat Interface](screenshots/HackathonHero%20Chat.png)

1. **Start Services**: Run one-liner setup script → HackathonHero opens in browser automatically
2. **Add Context**: Upload files or paste text/URLs in the left panel (calls `/api/context/*`). Index status appears live; chat is gated until RAG is ready.
3. **Chat & Brainstorm**: Use the streaming chat interface; agent may propose/add todos via tool calls.

![Todo Management](screenshots/HackathonHero%20Tools.png)

4. **Generate Artifacts**:
   - `POST /api/chat-sessions/{id}/derive-project-idea`
   - `POST /api/chat-sessions/{id}/create-tech-stack`
   - `POST /api/chat-sessions/{id}/summarize-chat-history`

![Project Artifacts](screenshots/HackathonHero%20Artifacts.png)

5. **Review & Export**: Review generated artifacts and export complete submission pack.

---
## 8. Tooling (Function Calls)
| Tool | Purpose | Args |
|------|---------|------|
| `get_session_id` | Returns active session id | session_id? |
| `list_todos` | Retrieve current tasks | session_id? |
| `add_todo` | Add a task | item, session_id |
| `clear_todos` | Remove tasks for a session | session_id |
| `list_directory` | Safe project dir listing | path? |
| `derive_project_idea` | Create idea artifact | session_id |
| `create_tech_stack` | Create tech stack artifact | session_id |
| `summarize_chat_history` | Submission summary | session_id |
| `generate_chat_title` | Auto title the session | session_id, force? |

Planned: `scaffold_code`, `auto_summarize`.

---
## 9. Retrieval Augmented Generation (RAG)

![RAG Context Retrieval](screenshots/HackathonHero%20RAG.png)

**Current Implementation:**
- **Chunking**: split on blank-line groups
- **Index**: FAISS cosine (normalized MiniLM embeddings via IndexFlatIP)
- **Query**: top‑k=5 similarities (higher = more relevant) returned
- **Caching**: embeddings, chunks, and metadata persisted under `backend/data/rag_cache/<rules_hash>/` for warm starts; session-aware scoping

**Planned Improvements:**
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
See [GAP.md](./GAP.md) for full prioritized list (P0→P3). Current status:
- [x] PWA offline app shell (G-014 done)
- [x] Submission pack export (G-001 done)
- [x] Embedding cache persistence (G-002 done)
- [x] SSE stream ordering test (G-003 done)
- [x] URL ingestion hardening (G-005 done)
- [x] Multi-round tool planning loop (G-012 done)

Immediate targets:
- [ ] Rule chunk highlight in UI (G-006)
- [ ] Artifact management panel (G-007)
- [ ] Model benchmarking script (G-008)
- [ ] Rolling chat summarization (G-009)
- [ ] Tool call results inline in UI (G-016)

---
## 14. Devpost Submission Checklist
- [x] Public repo with this README
- [x] LICENSE file present (MIT)
- [ ] 3‑minute demo video (offline proof + tool calls visible)
- [x] Screenshots (Chat, Todos, RAG retrieval, Artifacts)
- [x] Category justification paragraph (see [CATEGORY_JUSTIFICATION.md](./CATEGORY_JUSTIFICATION.md))
- [x] Model usage & offline explanation (see [MODEL_USAGE_OFFLINE.md](./MODEL_USAGE_OFFLINE.md))
- [x] Clear run instructions (verified on fresh machine) - includes one-liner setup scripts for MacOS/Linux/Windows

---

## 14.1 Screenshots Gallery

### Main Chat Interface
![Chat Interface](screenshots/HackathonHero%20Chat.png)

### Todo Management & Tools
![Todo Management](screenshots/HackathonHero%20Tools.png)

### Project Artifacts Generation
![Project Artifacts](screenshots/HackathonHero%20Artifacts.png)

### RAG Context Retrieval
![RAG System](screenshots/HackathonHero%20RAG.png)

### Markdown streaming
![Markdown Streaming](screenshots/HackathonHero%20Diagram.png)

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

- Embeddings recomputed each rules update (sync) — large files slow startup

---
## 17. Future Enhancements
| Area | Enhancement |
|------|-------------|
| Autonomy | Iterative planning loop that converts brainstorming into prioritized roadmap automatically |

| Code Gen | Safe scoped code scaffold + diff/preview tool |
| Memory | Rolling summarization to keep prompt small |
| UI | Accessibility (ARIA), theming toggle, mobile optimization |

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
@genggao

---
## 22. Appendix (API Snapshot)
| Method & Path | Purpose |
|--------------|---------|
| POST `/api/chat-stream` | Stream chat (SSE): `session_info` → `rule_chunks` → (`thinking`/`tool_calls`)* → `token` → `end` |
| GET `/api/todos` | List todos (`?detailed=true`, `?session_id=`) |
| POST `/api/todos` | Add todo (form `item`, optional `session_id`) |
| PUT `/api/todos/{id}` | Update fields (item/status/sort_order/session_id) |
| DELETE `/api/todos/{id}` | Delete one (`?session_id=` optional) |
| DELETE `/api/todos` | Clear all for a session (`?session_id=` required) |
| POST `/api/context/rules` | Upload rules/content file (optional `session_id`) |
| POST `/api/context/add-text` | Add pasted text or fetched URL snippet (optional `session_id`) |
| GET `/api/context/status` | RAG status (accepts `session_id` query) |
| GET `/api/context/list` | List context rows (accepts `session_id` query) |
| GET `/api/chat-sessions` | List sessions (limit/offset) |
| GET `/api/chat-sessions/{id}` | Session detail & messages (limit/offset) |
| PUT `/api/chat-sessions/{id}/title` | Rename session |
| DELETE `/api/chat-sessions/{id}` | Delete session |
| GET `/api/chat-sessions/{id}/project-artifacts` | List artifacts for session |
| GET `/api/chat-sessions/{id}/project-artifacts/{type}` | Get specific artifact |
| POST `/api/chat-sessions/{id}/derive-project-idea` | Generate & store idea |
| POST `/api/chat-sessions/{id}/create-tech-stack` | Generate & store tech stack |
| POST `/api/chat-sessions/{id}/summarize-chat-history` | Generate & store submission summary |
| POST `/api/export/submission-pack` | Download ZIP of idea.md, tech_stack.md, summary.md, todos.json, rules_ingested.txt, session_metadata.json (requires `session_id` query) |
| GET `/api/ollama/status` | Model & availability |
| GET `/api/ollama/model` | Get current model |
| POST `/api/ollama/model` | Switch active model |

---
**Ready to Hack Locally.** Improve what matters, stay offline, submit faster.
