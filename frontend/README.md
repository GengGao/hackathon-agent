# HackathonHero Frontend

React + Vite UI powering the local hackathon assistant.

> Provides chat interface (SSE streaming with reasoning + tool call visualization), todo management, and (upcoming) artifact panel & export controls.

---
## Stack
| Aspect | Tech | Notes |
|--------|------|-------|
| Framework | React 18 + Vite | Fast dev HMR |
| Styling | Tailwind CSS | Utility-first styling |
| Markdown Render | `react-markdown` + `remark-gfm` | Tables, lists, code formatting |
| Syntax Highlight | `react-syntax-highlighter` (Prism) | Highlights model code outputs |
| HTTP | Fetch / Axios | SSE & REST calls |
| State | Local component state | Simple, no global store yet |

---
## Key Components
| File | Role |
|------|------|
| `App.jsx` | Layout, orchestrates panels |
| `components/ChatBox.jsx` | Streaming chat UI + reasoning + tool call sections |
| `components/ChatHistory.jsx` | Session list (extend / paginate) |
| `components/TodoManager.jsx` | Todos (status cycle, priority) |
| `components/FileDrop.jsx` | Drag/drop multi-file upload |

Planned: `ArtifactPanel.jsx`, `ExportButton.jsx`, `ModelSelector.jsx`.

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
## Planned UI Enhancements
| Area | Enhancement |
|------|-------------|
| Artifacts | Live panel listing project idea / tech stack / summary with refresh buttons |
| Export | One-click ZIP download (calls future backend endpoint) |
| Models | Dropdown to switch gpt-oss model + latency metric |
| Theming | Light/dark toggle + persisted preference |
| Accessibility | ARIA roles, focus outlines, keyboard nav review |
| Mobile | Responsive layout, collapsible side sections |
| Reasoning | Collapsible reasoning area w/ truncation + copy button |

---
## Local Development
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```
The backend should run at `http://localhost:8000`. Adjust CORS in `backend/main.py` if hosting differently.

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
