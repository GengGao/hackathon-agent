## GAP & Roadmap Register

Living document cataloguing missing / partial features, quality gaps, and forward roadmap for HackathonHero. Each gap gets:
ID | Priority (P0–P3) | Status | Owner? | Summary | Resolution Sketch / Acceptance Criteria.

Priority Scale:
- P0 – Critical for reliability / core value in current milestone.
- P1 – High impact or differentiator for submission quality (target next).
- P2 – Valuable improvement; implement after P0/P1 stabilize.
- P3 – Exploratory / nice-to-have / future vision.

Status Legend: planned | in_progress | done | deferred.

---
### Snapshot (Counts)
- Total gaps: 27
- P0: 5 | P1: 8 | P2: 8 | P3: 6  (auth moved to deferred P3 per local-only scope)
- Closed (done): 0 (initial register population)

---
### Gap Table (Condensed)
| ID | P | Status | Area | Summary |
|----|---|--------|------|---------|
| G-001 | P0 | planned | Export | Submission ZIP pack (artifacts + todos + rules) |
| G-002 | P0 | planned | Export | Individual artifact download endpoints (markdown) |
| G-003 | P0 | planned | RAG | Embedding cache persistence (avoid recompute) |
| G-004 | P3 | deferred | Security | Basic auth + rate limiting (local-only => deferred) |
| G-005 | P0 | planned | Stability | SSE integration test (stream ordering & end frame) |
| G-006 | P0 | planned | Observability | Structured JSON logging + minimal metrics |
| G-007 | P1 | planned | RAG | Semantic / token-length aware chunking + IDs |
| G-008 | P1 | planned | Memory | Rolling chat summarization (auto compress history) |
| G-009 | P1 | planned | Tooling | Code scaffold + safe file write sandbox tool |
| G-010 | P1 | planned | Performance | Model benchmarking script & persisted results |
| G-011 | P1 | planned | UI | Rule chunk highlight & side panel display |
| G-012 | P1 | planned | UI | Artifact management UI (list, view, export) |
| G-013 | P1 | planned | Security | Harden URL ingestion (mime allowlist, max redirects) |
| G-014 | P1 | planned | Offline UX | PWA caching + offline front-end shell |
| G-015 | P2 | planned | RAG | Chunk scoring normalization & rerank experiment |
| G-016 | P2 | planned | Tooling | Auto multi-round tool call loop (planning → execution) |
| G-017 | P2 | planned | Testing | Synthetic RAG accuracy regression test harness |
| G-018 | P2 | planned | Testing | Tool chain multi-call simulation test |
| G-019 | P2 | planned | Performance | Async file/OCR ingestion pre-stream |
| G-020 | P2 | planned | DB | WAL mode + vacuum strategy for higher concurrency |
| G-021 | P2 | planned | UX | Accessibility (ARIA roles, keyboard nav, contrast) |
| G-022 | P2 | planned | UX | Theming (dark/light toggle persisted) |
| G-023 | P3 | planned | Autonomy | Prioritized roadmap auto-derivation (todo clustering) |
| G-024 | P3 | planned | AI | Lightweight local adapter fine-tune for mentor voice |
| G-025 | P3 | planned | Export | Devpost-ready README template generator |
| G-026 | P3 | planned | Observability | Prometheus endpoint & Grafana sample dashboard |
| G-027 | P3 | planned | Offline UX | Queue + retry for failed POSTs while offline |

---
### Detailed Gap Descriptions

#### G-001 – Submission ZIP Pack (P0)
Add endpoint `POST /api/export/submission-pack` returning a ZIP containing: `idea.md`, `tech_stack.md`, `summary.md`, `todos.json`, `rules_ingested.txt`, `session_metadata.json`. Acceptance: deterministic file names; size <2MB typical; test asserts presence & non-empty content.

#### G-002 – Artifact Download Endpoints (P0)
`GET /api/chat-sessions/{id}/artifact/{type}.md` streaming markdown with proper `Content-Disposition`. Acceptance: 200 for existing; 404 otherwise; test coverage.

#### G-003 – Embedding Cache Persistence (P0)
Serialize embeddings + chunk metadata to `data/rules_index.{json,bin}` keyed by hash of concatenated active rules. Acceptance: cold start load <300ms for 1k chunks vs >X ms baseline; unit test ensures reuse when unchanged.

#### G-004 – Basic Auth + Rate Limiting (P3, deferred)
Current decision: local-only, trusted environment; no auth friction desired. Defer adding API key header & rate limiting until commercialization / multi-user deployment. Keep design sketch for future: optional `HERO_API_KEY` env; middleware enforcement; simple token bucket (60 chat-stream/min) toggleable. Acceptance (when activated later): exceeding limit returns 429; disabled when env unset.

#### G-005 – SSE Stream Ordering Test (P0)
Integration test asserting first events: `session_info` → `rule_chunks` → zero+ `thinking`/`tool_calls` → tokens → `end`. Acceptance: deterministic fixture using fake stream generator.

#### G-006 – Structured Logging + Metrics (P0)
Introduce logger emitting JSON lines: timestamp, event, session_id, latency_ms, token_count. Simple `/api/health` returns uptime, served_requests. Acceptance: log schema validated in test.

#### G-007 – Semantic / Token-Aware Chunking (P1)
Replace blank-line split with: sentence segmentation + max token window (e.g. 200 tokens) with overlap. Acceptance: average chunk token length variance < threshold; retrieval precision improves on synthetic eval set.

#### G-008 – Rolling Chat Summarization (P1)
Background compressor summarizing older messages after N tokens. Acceptance: prompt token count capped (<8k) while preserving summary artifact content relevance on eval queries.

#### G-009 – Code Scaffold Tool (P1)
New tool: `scaffold_code` with constrained path whitelist writing to `scaffolds/` & returning diff preview. Acceptance: attempts outside whitelist blocked; test ensures safe write.

#### G-010 – Model Benchmark Script (P1)
Script `scripts/benchmark_models.py` measuring first token latency, tokens/sec, memory (psutil). Stores JSON under `data/benchmarks/`. Acceptance: README table auto-updated via script.

#### G-011 – Rule Chunk Highlight UI (P1)
Frontend maps retrieved chunk indices to side panel with highlight in answer (e.g. [R3]). Acceptance: visual test + mapping appears in SSE event handling.

#### G-012 – Artifact Management UI (P1)
List artifacts per session with copy/download buttons; refresh on creation. Acceptance: manual test & unit test for fetch hook.

#### G-013 – Harden URL Ingestion (P1)
Add redirect limit=3, content length guard via HEAD, allowed mime list (`text/*`, `application/json`, `application/xml`). Acceptance: tests simulate blocked binary.

#### G-014 – PWA Offline Shell (P1)
Service Worker caching static assets + offline placeholder; manifest for install. Acceptance: Lighthouse PWA passes basic offline check.

#### G-015 – Retrieval Score Normalization (P2)
Experiment with length normalization or cosine + rerank (e.g. MiniLM cross-encoder optional). Acceptance: measurable MRR improvement on synthetic dataset (≥+5%).

#### G-016 – Multi-Round Tool Planning Loop (P2)
Controller decides if further tool calls required before responding (chain-of-thought hidden). Acceptance: scenarios requiring sequential todo additions executed in single user turn.

#### G-017 – RAG Accuracy Regression Harness (P2)
Dataset of (query, expected chunk id). Test ensures top-k contains expected; failing raises alert. Acceptance: CI job.

#### G-018 – Tool Chain Simulation Test (P2)
Test simulating multiple tool_calls in sequence with stub LLM to ensure proper message injection order. Acceptance: passes deterministically.

#### G-019 – Async File & OCR Ingestion (P2)
Move blocking OCR/PDF parsing off main request (pre-process then stream). Acceptance: time to first SSE token reduced ≥30% for multi-file scenario.

#### G-020 – SQLite WAL & Maintenance (P2)
Enable WAL, periodic `ANALYZE` & `VACUUM` heuristic. Acceptance: documented config; concurrency test with parallel writes shows reduced lock waits.

#### G-021 – Accessibility Enhancements (P2)
Add ARIA labels, focus outlines, skip links. Acceptance: axe audit <5 issues (critical/serious=0).

#### G-022 – Theme Toggle (P2)
Persisted light/dark via localStorage + Tailwind config. Acceptance: preference restored across reloads.

#### G-023 – Auto Roadmap Derivation (P3)
LLM summarizes brainstorm into prioritized todo groups with scoring heuristics. Acceptance: generated sections: Feasibility / Impact / Effort.

#### G-024 – Local Adapter Fine-Tune (P3)
LoRA or QLoRA small adapter to refine mentor tone; optional load flag. Acceptance: config flag & fallback when adapter absent.

#### G-025 – Devpost README Template Generator (P3)
Tool `generate_submission_readme` assembling artifacts into formatted README. Acceptance: includes sections required by Devpost checklist.

#### G-026 – Prometheus Metrics (P3)
`/metrics` endpoint (optional extra dependency) exposing counters (requests_total, tokens_streamed_total). Acceptance: scrape sample succeeds.

#### G-027 – Offline Action Queue (P3)
Frontend queues failed POSTs (todos, artifacts) and retries when back online (navigator.onLine). Acceptance: simulated offline test passes.

---
### Closed Gaps (History)
None yet.

---
### Cross-Cutting Risks & Mitigations
- Model Drift: Pin model version in settings; record hash on artifact generation.
- Large Rules File Performance: Mitigate via G-003 cache + stream chunk loading.
- Security Surface: Harden (G-004, G-013) before public demo video.
- Data Integrity: Add lightweight checksum on exported ZIP (G-001) for reproducibility.

---
### Suggested Execution Order (Milestone Focus)
Milestone 1 (Stabilize Core): G-005, G-006, G-003 (auth deferred)
Milestone 2 (Submission Essentials): G-001, G-002, G-010, G-013
Milestone 3 (Differentiators): G-009, G-008, G-011, G-012, G-014
Milestone 4 (Performance & Depth): G-019, G-015, G-016, G-017, G-018, G-020
Milestone 5 (Polish & Vision): Remaining P2/P3 (G-021→G-027)

---
### Update Process
1. Add new gap with next numeric ID; keep priority rationale concise.
2. When starting work set status to in_progress; link PR in commit message referencing ID.
3. On merge & verification mark done and move details to Closed section (retain acceptance criteria & completion date).
4. Re-evaluate priorities after each milestone; adjust only with rationale noted inline.

---
### References
- Backend README Planned Enhancements section.
- Root `README.md` sections: Roadmap Snapshot, Future Enhancements.
- Current tests coverage (backend/tests) – identifies testing gaps (G-005, G-017, G-018).

---
Maintained for transparency & focused iteration. Keep lean, actionable.
