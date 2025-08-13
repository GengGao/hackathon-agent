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
- P0: 3 | P1: 6 | P2: 4 | P3: 3
- Closed (done): 3

---
### Gap Table (condensed)
| ID | P | Status | Area | Summary |
|----|---|--------|------|---------|
| G-001 | P0 | done | Export | Submission ZIP pack (artifacts + todos + rules) |
| G-002 | P0 | done | RAG | Embedding cache persistence keyed by rules hash |
| G-003 | P0 | deferred | Stability | SSE stream ordering test (thinking/tool_calls/token/end) |
| G-004 | P1 | deferred | Observability | JSON logs + minimal `/api/health` counters |
| G-005 | P1 | done | Security | Harden URL ingestion (redirect cap, stricter mime) |
| G-006 | P1 | deferred | UI | Rule chunk highlight and mapping in answers |
| G-007 | P1 | deferred | UI | Artifact management panel (list/view/download) |
| G-008 | P1 | deferred | Perf | Model benchmark script (latency/tokens/sec/memory) |
| G-009 | P1 | deferred | Memory | Rolling chat summarization to cap prompt size |
| G-010 | P2 | deferred | Retrieval | Token-aware/semantic chunking with overlap |
| G-011 | P2 | deferred | Retrieval | Score normalization or rerank experiment |
| G-012 | P2 | done | Tooling | Multi-round tool planning loop controller |
| G-013 | P2 | deferred | DB | WAL mode + maintenance guidance |
| G-014 | P3 | done    | Offline UX | PWA app shell using vite-plugin-pwa |
| G-015 | P3 | deferred| Security | Basic auth + rate limit (local-first, defer) |
| G-016 | P3 | deferred | UI | Show tool call results inline (not just names/args) |

---
### Details

#### G-001 – Submission ZIP Pack (P0)
Endpoint: `POST /api/export/submission-pack` → ZIP of `idea.md`, `tech_stack.md`, `summary.md`, `todos.json`, `rules_ingested.txt`, `session_metadata.json`.

#### G-002 – Embedding Cache (P0)
Implemented cache under `backend/data/rag_cache/<rules_hash>/` storing `chunks.json`, `meta.json`, and `embeddings.npy`. On rebuild (non-forced), attempts to load cache before recomputing; warm start uses cached FAISS index. Session scoping resets the rules hash when `session_id` changes to avoid cross-session leakage.

#### G-003 – SSE Ordering Test (P0)
Deterministic integration test ensuring order: `session_info` → `rule_chunks` → (`thinking`/`tool_calls`)* → `token` → `end`.
Note: Basic streaming test exists; add explicit ordering assertions across frames.

#### G-004 – JSON Logs + Health (P1)
Structured logs per stream; `/api/health` returns uptime, served_requests.

#### G-005 – URL Ingestion Hardening (P1)
Now enforces: redirect cap (≤3), HEAD size/mime guard, stricter MIME allowlist (text/*, application/xhtml+xml), and streams up to a byte cap without buffering the full response. Tests cover blocked binary, oversize responses, XHTML allow, and redirect loops.

#### G-006 – Rule Chunk Highlight (P1)
Current: UI shows a separate "Referenced rules" list using chunk texts. Target: emit stable chunk IDs in SSE and render inline refs like [R3] with side panel mapping.

#### G-007 – Artifact Panel (P1)
Current: Dashboard lists and generates artifacts; backend exposes `GET /api/chat-sessions/{id}/project-artifacts` and `GET /api/chat-sessions/{id}/project-artifacts/{type}`. Target: add copy/download actions in UI and stream/download endpoints for individual artifacts.

#### G-008 – Model Benchmarks (P1)
`scripts/benchmark_models.py` stores results to `data/benchmarks/*.json` and updates README table.

#### G-009 – Rolling Summarization (P1)
Cap prompt tokens by summarizing history. Keep artifacts fidelity on eval set.

#### G-010 – Semantic Chunking (P2)
Sentence segmentation + token window with overlap.

#### G-011 – Score Normalization/Rerank (P2)
Experiment with length-normalization or cross-encoder rerank.

#### G-012 – Tool Planning Loop (P2)
Current: Streaming loop supports multiple tool-call rounds with guards; emits `tool_calls` frames and continues until content or max rounds.

#### G-013 – SQLite WAL (P2)
Enable WAL; document `VACUUM`/`ANALYZE` cadence; concurrency test.

#### G-014 – PWA App Shell (P3, done)
Frontend already integrates `vite-plugin-pwa` with runtime caching.

#### G-015 – Auth + Rate Limiting (P3, deferred)
Local-only scope; keep design sketch for future deployment.

#### G-016 – Tool Call Results UI (P3)
Current: The chat UI shows a collapsible list of tool call names and truncated arguments per assistant turn.
Target: Render the tool execution results inline beneath each call (pretty-printed JSON), with copy-to-clipboard and collapse/expand per call.
Acceptance: When the backend emits `tool_calls` and later the assistant message is saved with `metadata.tool_calls`, the UI displays each call's `name`, `arguments`, and a summarized `result` (first-level keys) with a toggle to show full JSON. Add a visual indicator when multiple tool rounds occur in one turn.

---
### Closed
- G-001:  Submission ZIP pack
- G-002: Embedding cache persistence keyed by rules hash
- G-005: URL Ingestion Hardening
- G-012: Multi-round tool planning loop
- G-014: PWA offline app shell (vite-plugin-pwa, manifest, runtime caching)

---
### Risks & Mitigations
- Large rules files → G-002 cache + lazy rebuild
- Data leakage in URL fetch → G-005 stricter guards
- Stream instability → G-003 ordering test + heartbeats (already present)

---
### Milestones
- M1 (Core reliability): G-002, G-003, G-004
- M2 (Submission essentials): G-001, G-005, G-008
- M3 (Product polish): G-006, G-007, G-009
- M4 (Depth & perf): G-010, G-011, G-012, G-013

---
### Update Process
1. Add new gap with next numeric ID; keep rationale concise.
2. Set status to in_progress when work starts; link PR.
3. On merge and verification, mark done and move to Closed with date.
4. Re-evaluate priorities after each milestone.

---
References: backend `router.py`, `rag.py`, tests under `backend/tests`, and root README API snapshot.
