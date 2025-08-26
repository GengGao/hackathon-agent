# HackathonHero Frontend

React + Vite UI powering the local hackathon assistant.

> Provides chat interface (SSE streaming with reasoning + tool call visualization), artifact generation & management, todo system, and complete export functionality.

---
## Stack
| Aspect | Tech | Notes |
|--------|------|-------|
| Framework | React 19 + Vite | Latest React with fast HMR |
| Build Tool | Vite 7.0.4 | ES modules, optimized builds |
| Styling | Tailwind CSS 3.4.17 | Utility-first with custom gradients |
| Markdown Render | `streamdown` 1.1.3 | Streaming markdown with syntax highlighting |
| HTTP | Fetch API | Native SSE & REST calls |
| State | Custom hooks + local state | `useChat`, `useDashboard`, `useOllama`, `useRag` |
| PWA | `vite-plugin-pwa` 1.0.2 | Service worker with runtime caching |
| Linting | ESLint 9.30.1 | React hooks + refresh plugins |

---
## Key Components
| File | Role |
|------|------|
| `App.jsx` | Main app layout with three-panel design (left: context/history, center: chat, right: dashboard) |
| `components/ChatBox.jsx` | Streaming chat UI with SSE handling, reasoning display, tool call visualization using Streamdown |
| `components/ChatHistory.jsx` | Session management with CRUD operations, title editing, and session switching |
| `components/ContextPanel.jsx` | RAG status monitoring, file/URL ingestion with drag & drop support |
| `components/ProjectDashboard.jsx` | Artifact generation and management, todo system, export functionality |
| `components/TodoManager.jsx` | Todo CRUD with status cycling (pending→in_progress→done), session-scoped |
| `components/FileDrop.jsx` | Multi-file upload with drag & drop, file type validation |
| `components/Header.jsx` | Model switching, provider toggle (Ollama/LMStudio), PWA status |
| `components/SkeletonText.jsx` | Loading states for streaming content |

All planned components are implemented.

---
## Chat Streaming Protocol
Backend emits Server-Sent Events (`text/event-stream`). Each event is one JSON object following a `data:` line; the frontend merges them into the last assistant message.

Event `type` values:
- `session_info` – initial metadata (session id)
- `rule_chunks` – retrieved rule text snippets (top-k)
- `thinking` – reasoning tokens (intermediate)
- `tool_calls` – list of function names + serialized args
- `token` – assistant content fragment (markdown eventually)
- `end` – stream completion

Render Rules:
1. While `isTyping`, show raw text (avoid expensive markdown re-render per token).
2. After `end`, re-render markdown with code highlighting.
3. Thinking text shown in a styled pre block (truncate planned after N chars).
4. Tool calls displayed in a collapsible panel (future improvement: show results).

---
## Todos UX
- Status pill cycles: pending → in_progress → done
- Priority accent bar + color-coded circle legend
- Inline editing triggers immediate PUT (optimistic update possible future)
- Detailed listing uses `/api/todos?detailed=true`

Planned: drag-and-drop ordering, filters, bulk actions.

---
## Implemented UI Features
| Area | Status |
|------|--------|
| Artifacts | ✅ Live panel with project idea, tech stack, summary generation & streaming |
| Export | ✅ One-click ZIP download with complete submission pack |
| Models | ✅ Dropdown model switching + provider toggle (Ollama/LMStudio) |
| PWA | ✅ Offline-capable with service worker and runtime caching |
| Streaming | ✅ Real-time SSE with reasoning, tool calls, and token streaming |
| Session Management | ✅ Full CRUD with history, titles, and context switching |
| Todo System | ✅ Status cycling, session-scoped, priority support |
| File Upload | ✅ Drag & drop multi-file with type validation |

## Planned UI Enhancements
| Area | Enhancement |
|------|-------------|
| Theming | Light/dark toggle + persisted preference |
| Accessibility | ARIA roles, focus outlines, keyboard navigation |
| Mobile | Responsive optimization, collapsible side sections |
| Reasoning | Collapsible reasoning area w/ truncation + copy button |
| Tool Results | Inline display of tool call execution results |

---
## Local Development
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```
The backend should run at `http://localhost:8000` (proxied during dev). Adjust CORS in `backend/main.py` if hosting differently.

### Optional Vite Proxy Example
Add to `vite.config.js` if you want same-origin API during dev:
```js
server: { proxy: { '/api': 'http://localhost:8000' } }
```

---
## Adding a New Panel
1. Create component under `components/`.
2. Import + place inside `App.jsx` (conditional or tabbed display).
3. Style with Tailwind; factor shared utilities into small components if reused.
4. If state crosses siblings, introduce React Context before adopting heavier state libs.

---
## Style Guidelines
- Prefer semantic elements + Tailwind utilities.
- Keep components <250 lines; refactor shared UI pieces.
- Avoid unnecessary re-renders: memo large lists if they grow.

---
## Testing (Planned)
Will add Vitest + React Testing Library for:
- Chat event reducer (synthetic SSE sequence → final rendered state)
- Todo CRUD (mock axios)
- Markdown security (ensure no raw HTML injection when enabling plugins)

---
## Performance Notes
- SSE token appends O(1); auto-scroll invoked in `useEffect`.
- Prism highlighting deferred until completion to avoid churn.
- Potential optimization: virtualization if long transcript grows (react-window).

---
## Security / Safety
- No `dangerouslySetInnerHTML`; using `react-markdown` with GFM only.
- Client defers validation (server enforces size/type); add pre-validation for UX.
- Future: sanitize or strip HTML if enabling raw HTML plugin.

---
## Roadmap Hooks
Frontend tasks tracked in root `GAP.md` under categories: `ui`, `accessibility`, `export`, `artifacts`, `performance`.

---
## Contributing
- Keep PRs small & scoped.
- Reference gap IDs in commit/PR messages.
- Update this README if adding major UI feature.

---
## License
Inherits root project license (to be added: MIT or Apache 2.0).

---
Ship fast, stay offline, help teams submit better.
