## GAP & Roadmap Register

Focused, current view of missing/partial features and quality work for HackathonHero. Each gap lists: ID | Priority (P0–P3) | Status | Area | Summary | Acceptance criteria.

Priority scale:
- P0 – Critical for reliability/core value in this milestone
- P1 – High impact for submission quality (next up)
- P2 – Valuable improvement after P0/P1 stabilize
- P3 – Exploratory/nice-to-have/future vision

Status: planned | in_progress | done | deferred

---
### Snapshot
- Total gaps: 16
- P0: 4 | P1: 6 | P2: 4 | P3: 2
- Closed (done): 1

---
### Gap Table (condensed)
| ID | P | Status | Area | Summary |
|----|---|--------|------|---------|
| G-001 | P0 | planned | Export | Submission ZIP pack (artifacts + todos + rules) |
| G-002 | P0 | planned | Export | Download endpoints for individual artifacts (markdown) |
| G-003 | P0 | in_progress | RAG | Embedding cache persistence keyed by rules hash |
| G-004 | P0 | planned | Stability | SSE stream ordering test (thinking/tool_calls/token/end) |
| G-005 | P1 | planned | Observability | JSON logs + minimal `/api/health` counters |
| G-006 | P1 | planned | Security | Harden URL ingestion (redirect cap, stricter mime) |
| G-007 | P1 | planned | UI | Rule chunk highlight and mapping in answers |
| G-008 | P1 | planned | UI | Artifact management panel (list/view/download) |
| G-009 | P1 | planned | Perf | Model benchmark script (latency/tokens/sec/memory) |
| G-010 | P1 | planned | Memory | Rolling chat summarization to cap prompt size |
| G-011 | P2 | planned | Retrieval | Token-aware/semantic chunking with overlap |
| G-012 | P2 | planned | Retrieval | Score normalization or rerank experiment |
| G-013 | P2 | in_progress | Tooling | Multi-round tool planning loop controller |
| G-014 | P2 | planned | DB | WAL mode + maintenance guidance |
| G-015 | P3 | done    | Offline UX | PWA app shell using vite-plugin-pwa |
| G-016 | P3 | deferred| Security | Basic auth + rate limit (local-first, defer) |

---
### Details

#### G-001 – Submission ZIP Pack (P0)
Endpoint: `POST /api/export/submission-pack` → ZIP of `idea.md`, `tech_stack.md`, `summary.md`, `todos.json`, `rules_ingested.txt`, `session_metadata.json`.
Acceptance: deterministic names; content non-empty; <=2MB typical; test asserts members.

#### G-002 – Artifact Downloads (P0)
Endpoint: `GET /api/chat-sessions/{id}/artifact/{type}.md` streamed with `Content-Disposition`.
Acceptance: 200 when exists; 404 otherwise; unit tests.

#### G-003 – Embedding Cache (P0)
Implemented cache under `backend/data/rag_cache/<rules_hash>/` storing `chunks.json`, `meta.json`, and `embeddings.npy`. On rebuild (non-forced), attempts to load cache before recomputing; warm start uses cached FAISS index. Session scoping resets the rules hash when `session_id` changes to avoid cross-session leakage.
Acceptance (remaining): warm start <300ms for ~1k chunks; add unit test verifying cache reuse when rules unchanged; document behavior in README.

#### G-004 – SSE Ordering Test (P0)
Deterministic integration test ensuring order: `session_info` → `rule_chunks` → (`thinking`/`tool_calls`)* → `token` → `end`.
Note: Basic streaming test exists; add explicit ordering assertions across frames.

#### G-005 – JSON Logs + Health (P1)
Structured logs per stream; `/api/health` returns uptime, served_requests.

#### G-006 – URL Ingestion Hardening (P1)
Baseline guards exist (text-only content types and max snippet length). Remaining: add redirect cap (≤3), HEAD size guard, stricter MIME allowlist, and avoid buffering full response into memory. Tests should simulate blocked binary and oversize responses.

#### G-007 – Rule Chunk Highlight (P1)
Current: UI shows a separate "Referenced rules" list using chunk texts. Target: emit stable chunk IDs in SSE and render inline refs like [R3] with side panel mapping.

#### G-008 – Artifact Panel (P1)
Current: Dashboard lists and generates artifacts; backend exposes `GET /api/chat-sessions/{id}/project-artifacts` and `GET /api/chat-sessions/{id}/project-artifacts/{type}`. Target: add copy/download actions in UI and stream/download endpoints for individual artifacts.

#### G-009 – Model Benchmarks (P1)
`scripts/benchmark_models.py` stores results to `data/benchmarks/*.json` and updates README table.

#### G-010 – Rolling Summarization (P1)
Cap prompt tokens by summarizing history. Keep artifacts fidelity on eval set.

#### G-011 – Semantic Chunking (P2)
Sentence segmentation + token window with overlap.

#### G-012 – Score Normalization/Rerank (P2)
Experiment with length-normalization or cross-encoder rerank.

#### G-013 – Tool Planning Loop (P2)
Current: Streaming loop supports multiple tool-call rounds with guards; emits `tool_calls` frames and continues until content or max rounds.
Acceptance: add multi-round integration test (≥2 rounds), document termination conditions, ensure UI stability across rounds.

#### G-014 – SQLite WAL (P2)
Enable WAL; document `VACUUM`/`ANALYZE` cadence; concurrency test.

#### G-015 – PWA App Shell (P3, done)
Frontend already integrates `vite-plugin-pwa` with runtime caching.

#### G-016 – Auth + Rate Limiting (P3, deferred)
Local-only scope; keep design sketch for future deployment.

---
### Closed
- G-015: PWA offline app shell (vite-plugin-pwa, manifest, runtime caching)

---
### Risks & Mitigations
- Large rules files → G-003 cache + lazy rebuild
- Data leakage in URL fetch → G-006 stricter guards
- Stream instability → G-004 ordering test + heartbeats (already present)

---
### Milestones
- M1 (Core reliability): G-003, G-004, G-005
- M2 (Submission essentials): G-001, G-002, G-006, G-009
- M3 (Product polish): G-007, G-008, G-010
- M4 (Depth & perf): G-011, G-012, G-013, G-014

---
### Update Process
1. Add new gap with next numeric ID; keep rationale concise.
2. Set status to in_progress when work starts; link PR.
3. On merge and verification, mark done and move to Closed with date.
4. Re-evaluate priorities after each milestone.

---
References: backend `router.py`, `rag.py`, tests under `backend/tests`, and root README API snapshot.
