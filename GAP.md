# GAP Register (Feature & Quality Gaps)

Living tracker of missing / incomplete capabilities vs the intended vision described in `README.md`. Use this to focus limited hackathon time. Keep entries concise; link PRs when closed.

---
## Legend
- **Priority**: P0 (must-have for demo / submission) → P3 (nice stretch)
- **Status**: NS (Not Started), IP (In Progress), BLK (Blocked), DONE (Implemented), DROP (Descoped)
- **Owner**: handle or `unassigned`

---
## 1. Baseline (Implemented Today)
Backend:
- Local LLM streaming via Ollama (`/api/chat-stream`) with thinking + tool call transparency
- Tool calling: todos (add/list/clear/update/delete), directory listing, artifact generators (idea, tech stack, submission summary)
- RAG: simple blank-line chunking + FAISS L2 index (MiniLM embeddings, recomputed each load)
- SQLite schema + migrations; app settings persistence for model selection
- Multi-file + URL (text-only) ingestion with size & type guards + basic OCR (pytesseract)
- Model selection endpoints (`/api/ollama/status`, `/api/ollama/model`)
- Chat sessions CRUD, artifacts persistence

Frontend:
- React + Vite UI (Chat, File drop, Todo manager, Project dashboard, Model picker, Session history)
- SSE streaming (fetch fallback), displays thinking tokens & tool calls live
- Manual triggers for artifact generation
- Basic theming (glassmorphism), responsive (limited testing), priority/status UX for todos

Quality / Tests:
- Pytest coverage for DB, migrations, chat history, tools, artifacts, new feature endpoints

---
## 2. Gap Matrix (High-Level)
| ID | Title | Category | Priority | Status | Owner | Notes / Acceptance |
|----|-------|----------|----------|--------|-------|--------------------|
| GAP-001 | Cosine similarity retrieval | RAG Quality | P1 | DONE | geng | Switched to normalized vectors + IndexFlatIP; added test_rag_cosine.py. |
| GAP-002 | Embedding persistence/cache | Performance | P1 | NS | unassigned | Avoid re-embedding rules on restart (serialize vectors + chunks). |
| GAP-003 | Rule chunk highlighting in UI | UX / RAG | P2 | NS | unassigned | Surface which text matched; clickable popover. |
| GAP-004 | Submission pack ZIP export | Export | P0 | NS | unassigned | Endpoint: zip (idea.md, tech_stack.md, summary.md, todos.json, rules_ingested.txt). |
| GAP-005 | Single export README generator | Export | P1 | NS | unassigned | Compose artifacts into templated README snippet. |
| GAP-006 | SSE integration test | Testing | P1 | NS | unassigned | Verify streaming frame order (thinking/tool_calls/token/end). |
| GAP-007 | Tool auto-summarization trigger | Autonomy | P2 | NS | unassigned | Periodically summarize long chats to shrink context. |
| GAP-008 | Rolling memory / summary messages | Memory | P2 | NS | unassigned | Replace early history with summary after threshold (e.g., >50 msgs). |
| GAP-009 | Auth + simple rate limiting | Security | P1 | NS | unassigned | API key header + per-IP/session rate limit; protect from abuse. |
| GAP-010 | Multi-user isolation | Security | P3 | NS | unassigned | Namespacing DB rows by user / workspace. |
| GAP-011 | Model benchmarking script | Ops / Perf | P2 | NS | unassigned | Measure first token latency, tok/sec, RAM; outputs markdown table. |
| GAP-012 | Structured JSON logging | Observability | P2 | NS | unassigned | Add logger w/ request id, tool events, errors. |
| GAP-013 | Metrics endpoint (basic) | Observability | P3 | NS | unassigned | /api/metrics (Prometheus text) counts requests, tool calls, avg latency. |
| GAP-014 | PWA offline support | Offline UX | P3 | NS | unassigned | Service worker caching core shell + last chat sessions. |
| GAP-015 | Accessibility pass (ARIA, contrasts) | UX / A11y | P2 | NS | unassigned | Lint w/ axe; keyboard navigation for all buttons & dropdowns. |
| GAP-016 | Mobile layout optimization | UX | P2 | NS | unassigned | Breakpoint adjustments; vertical stacking; hide heavy panels behind tabs. |
| GAP-017 | Theme toggle (light/dark) | UX | P3 | NS | unassigned | CSS variables + persisted preference. |
| GAP-018 | Code scaffold tool | Tooling | P3 | NS | unassigned | New function call: scaffold_code(path, template). Guard paths. |
| GAP-019 | Export artifacts via function (tool call) | Tooling | P1 | NS | unassigned | Tool callable export_submission_pack returning manifest. |
| GAP-020 | Enhanced ingestion (chunk-level dedupe + MD headings) | RAG Quality | P2 | NS | unassigned | Parse markdown; preserve headings; dedupe repeated paragraphs. |
| GAP-021 | Large file streaming ingestion | Ingestion | P3 | NS | unassigned | Stream read for >1MB; incremental chunk embed. |
| GAP-022 | URL fetch hardening | Security | P1 | NS | unassigned | Enforce domain allowlist or disable network entirely for offline mode flag. |
| GAP-023 | Input validation / Pydantic schemas for routes | Robustness | P2 | NS | unassigned | Replace Form scatter with request models where appropriate. |
| GAP-024 | Error boundary & toast notifications | UX | P2 | NS | unassigned | Show non-blocking errors (model switch fail, export errors). |
| GAP-025 | Retry / exponential backoff for Ollama status | Resilience | P2 | NS | unassigned | Smooth status indicator; degrade gracefully. |
| GAP-026 | Session title auto-generation | UX | P2 | NS | unassigned | First user message or LLM summarization sets title. |
| GAP-027 | Artifact diff history | Artifacts | P3 | NS | unassigned | Track versions of regenerated artifacts. |
| GAP-028 | Security: path traversal unit tests | Security | P1 | DONE | geng | Tests added (test_security_list_directory.py). |
| GAP-029 | Rate limit tool call loops | Safety | P1 | NS | unassigned | Hard guard beyond existing max_tool_rounds → error event. |
| GAP-030 | MIT or Apache 2.0 LICENSE file | Compliance | P0 | DONE | geng | MIT LICENSE added (2025-08-08). |
| GAP-031 | README completion (benchmarks table) | Docs | P0 | NS | unassigned | Fill metrics + demo links. |
| GAP-032 | Demo video script & capture checklist | Docs | P0 | NS | unassigned | Outline ensures all criteria shown. |
| GAP-033 | CI workflow (pytest + lint) | Quality | P1 | NS | unassigned | GitHub Actions basic matrix (3.11). |
| GAP-034 | Frontend lint & format config | Quality | P2 | NS | unassigned | ESLint rules + Prettier; run in CI. |
| GAP-035 | Python lint/type (ruff + mypy) | Quality | P2 | NS | unassigned | Add config; fix high-signal issues. |
| GAP-036 | SSE backpressure handling | Robustness | P3 | NS | unassigned | Ensure UI doesn't freeze w/ very long streams (chunk scheduling). |
| GAP-037 | Cancel in-flight tool execution UI feedback | UX | P2 | NS | unassigned | Show tool call list updating statuses; allow cancel if long-running. |
| GAP-038 | Extended todo analytics (velocity) | Productivity | P3 | NS | unassigned | Compute completion counts over time. |
| GAP-039 | i18n readiness | Globalization | P3 | NS | unassigned | Extract strings; simple translation map. |
| GAP-040 | Fine-tune / adapter integration placeholder | Model | P3 | NS | unassigned | Hook for loading local LoRA adapter. |

---
## 3. Detailed Notes (Selected High Impact)
### GAP-001 Cosine Similarity Retrieval
Current FAISS index is L2; ranking drifts with varied vector norms. Switch to IndexFlatIP with pre-normalized embeddings or compute cosine manually. Add unit test asserting order changes for known query.

### GAP-002 Embedding Persistence
Serialize: `rules.index.npy` (vectors float32), `rules.chunks.json` (array of strings), and optional metadata (model name + checksum). Rebuild only if checksum changes.

### GAP-004 Submission Pack ZIP
Endpoint: `POST /api/chat-sessions/{id}/export-pack` returns `application/zip`. Includes all artifacts (generate missing? optional flag), todos JSON (with status/priority), raw rules file copy and timestamped manifest.

### GAP-009 Auth + Rate Limiting
Lightweight: env `HACKATHON_API_TOKEN`; middleware checks header. Use simple in-memory token bucket keyed by IP+route until more robust store needed.

### GAP-019 Export Tool Call
Expose `export_submission_pack` as a tool so the agent can autonomously initiate an export on user request.

### GAP-022 URL Fetch Hardening
Currently allows arbitrary HTTP GET. Add: max redirects=1, allowed MIME types `text/*`, optional domain allowlist or disable when `OFFLINE_LOCKDOWN=1`.

### GAP-029 Rate Limit Tool Call Loops
Already have `max_tool_rounds`. Add secondary guard: count of total tool invocations per request (e.g., <=15) and fail fast with explanatory assistant message.

### GAP-030 License
Add `LICENSE` (MIT or Apache 2.0) + update README licensing section.

### GAP-031 Benchmarks Table Completion
Use benchmarking script (GAP-011) to populate latency + throughput. Mandatory before submission.

### GAP-033 CI Workflow
GitHub Actions: steps: checkout → setup Python → install deps → run `pytest -q` → run `ruff` + `mypy` (when added) → artifact coverage (optional).

---
## 4. Sequencing / Dependencies
- Do GAP-030 (License) early to avoid forgetting.
- Export features (GAP-004, GAP-019) depend on artifact generation (already present) → implement after minor RAG improvements (GAP-001) if time allows.
- Embedding persistence (GAP-002) assists all future RAG experimentation.
- Auth / security (GAP-009, GAP-022, GAP-028, GAP-029) can be parallelized—minimal code surface.
- CI (GAP-033) precedes lint/type additions (GAP-034, GAP-035) but can land with placeholders.

---
## 5. Quick Wins (≤1h Each)
- GAP-028 Add explicit test on `list_directory` path traversal attempts
- GAP-030 Add LICENSE file
- GAP-031 Populate README placeholders (demo link once recorded)
- GAP-029 Add simple tool invocation counter
~ (Done) GAP-001 Switch to cosine (normalized + IP index)

---
## 6. Stretch (Likely Post-Submission)
- GAP-014 PWA offline shell caching
- GAP-018 Code scaffold tool (security surface area)
- GAP-038 Velocity analytics
- GAP-040 Adapter fine-tune hook

---
## 7. Closure Process
1. Implement + tests/docs.
2. Update Gap row: Status=DONE, link PR.
3. If descoped: Status=DROP with rationale.

---
_Last updated: {{DATE}}_
