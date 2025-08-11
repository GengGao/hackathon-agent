from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, AsyncGenerator, Optional, Callable
import asyncio
from utils.text import strip_context_blocks
from models.db import (
    list_todos_db, add_todo_db, clear_todos_db, update_todo_db, delete_todo_db,
    get_chat_messages, save_project_artifact, get_project_artifact,
    get_all_project_artifacts, get_chat_session, update_chat_session_title
)
from llm import client as llm_client, get_current_model
from prompts import (
    TECH_STACK_SYSTEM_PROMPT,
    PROJECT_IDEA_SYSTEM_PROMPT,
    SUBMISSION_SUMMARY_SYSTEM_PROMPT,
    CHAT_TITLE_SYSTEM_PROMPT,
    build_chat_title_user_prompt,
    build_project_idea_user_prompt,
    build_tech_stack_user_prompt,
    build_submission_summary_user_prompt,
)
def _shorten(text: str, limit: int = 220) -> str:
    return (text[: limit - 3] + "...") if len(text) > limit else text


def _build_conversation_snippets(messages: List[Dict[str, Any]], max_messages: int = 20) -> List[str]:
    def _get_message_field(msg: Any, key: str, default: str = "") -> str:
        if isinstance(msg, dict):
            return str(msg.get(key, default))
        try:
            return str(msg[key])  # sqlite3.Row supports key access
        except Exception:
            return default

    snippets: List[str] = []
    for msg in messages[-max_messages:]:
        role = _get_message_field(msg, "role", "user")
        raw_content = _get_message_field(msg, "content", "").strip()
        content = _shorten(strip_context_blocks(raw_content))
        if not content:
            continue
        snippets.append(f"- {role}: {content}")
    return snippets


def _can_call_llm_sync() -> bool:
    try:
        loop = asyncio.get_running_loop()
        if loop and loop.is_running():
            return False
    except RuntimeError:
        # No running loop
        return True
    return True


def _ask_llm_once(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 512,
    on_delta: Optional[Callable[[str], None]] = None,
) -> str:
    if not _can_call_llm_sync():
        return ""
    async def _go() -> str:
        final_parts: List[str] = []
        stream = await llm_client.chat.completions.create(
            model=get_current_model(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            try:
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None) or getattr(choice, "message", None) or choice
                text = None
                if delta is not None and hasattr(delta, "content"):
                    text = getattr(delta, "content")
                if text is None and isinstance(delta, dict):
                    text = delta.get("content")
                if text:
                    final_parts.append(text)
                    if on_delta:
                        try:
                            on_delta(text)
                        except Exception:
                            pass
            except Exception:
                continue
        return ("".join(final_parts)).strip()

    try:
        return asyncio.run(_go())
    except Exception:
        return ""


def _ask_llm_once_non_stream(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 512,
    allow_reasoning_fallback: bool = False,
) -> str:
    """Best-effort single-shot non-streaming call. Returns empty string on error."""
    if not _can_call_llm_sync():
        return ""

    async def _go() -> str:
        try:
            resp = await llm_client.chat.completions.create(
                model=get_current_model(),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                extra_body={"reasoning_effort": "low"}
            )
            try:
                # Prefer assistant message content; optionally fall back to reasoning if allowed
                msg = resp.choices[0].message
                content = ""
                try:
                    content = (getattr(msg, "content", None) or "").strip()
                except Exception:
                    content = ""
                if not content and allow_reasoning_fallback:
                    try:
                        reasoning = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
                        if not reasoning and isinstance(msg, dict):
                            reasoning = msg.get("reasoning") or msg.get("reasoning_content")
                        if reasoning:
                            content = str(reasoning).strip()
                    except Exception:
                        pass

                return content
            except Exception:
                return ""
        except Exception:
            return ""

    try:
        return asyncio.run(_go())
    except Exception:
        return ""


async def ask_llm_stream(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 512,
) -> AsyncGenerator[str, None]:
    """Async generator yielding content tokens from the LLM.

    Backed by the OpenAI-compatible streaming API exposed by the local client.
    Yields only content deltas; ignores reasoning/tool_calls for simplicity.
    """
    stream = await llm_client.chat.completions.create(
        model=get_current_model(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        extra_body={"reasoning_effort": "medium"}
    )
    async for chunk in stream:
        try:
            choice = chunk.choices[0]
            delta = getattr(choice, "delta", None) or getattr(choice, "message", None) or choice
            text = None
            if delta is not None and hasattr(delta, "content"):
                text = getattr(delta, "content")
            if text is None and isinstance(delta, dict):
                text = delta.get("content")
            if text:
                yield text
        except Exception:
            continue


def list_todos(detailed: bool = False, session_id: str | None = None) -> List[Any]:
    rows = list_todos_db(session_id=session_id)
    if detailed:
        # Return dicts with extended fields if present
        out = []
        for r in rows:
            d = {"id": r["id"], "item": r["item"]}
            # sqlite3.Row supports 'k in row.keys()' and item access
            existing_keys = set(r.keys())  # type: ignore
            for k in ("status", "sort_order", "created_at", "updated_at", "completed_at"):
                if k in existing_keys:
                    d[k] = r[k]
            if "session_id" in existing_keys:
                d["session_id"] = r["session_id"]
            out.append(d)
        return out
    return [str(r["item"]) for r in rows]


def add_todo(item: str, session_id: str | None = None) -> Dict[str, Any]:
    add_todo_db(item, session_id=session_id)
    todos = list_todos(session_id=session_id)
    return {"ok": True, "count": len(todos)}


def clear_todos(session_id: str | None = None) -> Dict[str, Any]:
    # Only clear when a session_id is explicitly provided (tool-call scoping)
    if not session_id:
        return {"ok": True, "deleted": 0}
    deleted = clear_todos_db(session_id=session_id)
    return {"ok": True, "deleted": deleted}


def update_todo(todo_id: int, **fields) -> Dict[str, Any]:
    ok = update_todo_db(todo_id, **fields)
    return {"ok": ok}


def delete_todo(todo_id: int, session_id: str | None = None) -> Dict[str, Any]:
    ok = delete_todo_db(todo_id, session_id=session_id)
    return {"ok": ok}


def list_directory(path: str = ".") -> Dict[str, Any]:
    # Limited, safe directory listing relative to project root
    root = Path(__file__).resolve().parents[1]
    # Normalize path to handle Windows-style separators and traversal attempts consistently
    normalized = (path or ".").replace("\\", "/").strip()
    if normalized == "":
        normalized = "."
    candidate = (root / normalized).resolve()
    if not str(candidate).startswith(str(root)):
        return {"ok": False, "error": "Path outside project root is not allowed"}
    if not candidate.exists() or not candidate.is_dir():
        return {"ok": False, "error": "Directory not found"}
    items = []
    for entry in candidate.iterdir():
        if entry.name.startswith('.'):
            continue
        items.append({
            "name": entry.name,
            "is_dir": entry.is_dir(),
            "size": entry.stat().st_size if entry.is_file() else None,
        })
    return {"ok": True, "items": items}


def get_session_id(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Return the current chat session id injected by the request pipeline.

    When called within the chat-stream flow, the router supplies the active
    session_id automatically to all tool calls. This function surfaces it to
    the model so it never needs to ask the user.
    """
    return {"ok": True, "session_id": session_id}


def derive_project_idea(session_id: str) -> Dict[str, Any]:
    """Analyze chat history to derive and save a project idea.

    Attempts an LLM-generated idea first using recent chat messages. Falls back
    to simple keyword extraction to ensure deterministic behavior when LLM is
    unavailable.
    """
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    # Get recent chat messages
    messages = get_chat_messages(session_id, limit=50)
    if not messages:
        return {"ok": False, "error": "No chat history found for this session"}

    # LLM attempt
    snippets = _build_conversation_snippets(messages)
    user_prompt = build_project_idea_user_prompt(snippets)
    project_idea_llm = _ask_llm_once(PROJECT_IDEA_SYSTEM_PROMPT, user_prompt, temperature=0.2, max_tokens=256)

    # Fallback keyword-based extraction
    def _get_field(m: Any, k: str) -> str:
        if isinstance(m, dict):
            return str(m.get(k, ""))
        try:
            return str(m[k])
        except Exception:
            return ""
    content_text = " ".join([_get_field(msg, "content") for msg in messages])
    keywords: List[str] = []
    tech_terms = [
        "web", "app", "mobile", "ai", "ml", "blockchain", "api", "dashboard",
        "automation", "analytics", "chat", "game", "tool", "platform", "system",
    ]
    for term in tech_terms:
        if term.lower() in content_text.lower():
            keywords.append(term)

    fallback_idea = (
        f"A {' & '.join(keywords[:3])} solution that addresses the problems discussed in the chat. "
        "The project leverages modern technologies to create an innovative hackathon submission."
        if keywords
        else "An innovative solution derived from the conversation topics and user requirements discussed."
    )

    project_idea = project_idea_llm or fallback_idea

    # Save the project idea
    metadata = {
        "keywords": keywords,
        "message_count": len(messages),
        "generated_from": "llm_first_fallback_keywords",
        "llm_used": bool(project_idea_llm),
    }

    save_project_artifact(session_id, "project_idea", project_idea, metadata)

    return {
        "ok": True,
        "project_idea": project_idea,
        "keywords": keywords,
        "based_on_messages": len(messages)
    }


def create_tech_stack(session_id: str) -> Dict[str, Any]:
    """Analyze chat history to create and save a recommended tech stack.

    Attempts an LLM-generated summary first using recent chat messages. Falls back
    to keyword-based detection to ensure deterministic behavior when LLM is
    unavailable. Always persists the artifact and returns detected technologies
    for downstream consumers/tests.
    """
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    messages = get_chat_messages(session_id, limit=50)
    if not messages:
        return {"ok": False, "error": "No chat history found for this session"}

    content_text = " ".join([msg["content"] for msg in messages]).lower()

    # Try LLM generation first (best-effort; safe fallback on error)
    llm_text: str = ""
    try:
        # Build concise system and user prompts to drive a structured summary
        system_prompt = TECH_STACK_SYSTEM_PROMPT
        # Include a compact view of recent messages for context
        def _shorten(s: str, limit: int = 220) -> str:
            return (s[: limit - 3] + "...") if len(s) > limit else s

        convo_snippets = _build_conversation_snippets(messages, max_messages=20)
        user_prompt = build_tech_stack_user_prompt(convo_snippets)

        async def _ask_llm() -> str:
            resp = await llm_client.chat.completions.create(
                model=get_current_model(),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=512,
                stream=False,
            )
            try:
                return (resp.choices[0].message.content or "").strip()
            except Exception:
                return ""

        # Run in a new event loop in this thread (sync context)
        llm_text = asyncio.run(_ask_llm())
    except Exception:
        llm_text = ""

    # Technology detection based on mentions in chat
    frontend_techs = []
    backend_techs = []
    database_techs = []
    other_techs = []

    tech_mapping = {
        "frontend": {
            "react": ["react", "jsx", "create-react-app"],
            "vue": ["vue", "vuejs"],
            "angular": ["angular"],
            "svelte": ["svelte"],
            "html/css/js": ["html", "css", "javascript", "js"]
        },
        "backend": {
            "fastapi": ["fastapi", "uvicorn"],
            "express": ["express", "nodejs", "node.js"],
            "django": ["django"],
            "flask": ["flask"],
            "python": ["python"],
            "node.js": ["node", "nodejs"]
        },
        "database": {
            "sqlite": ["sqlite"],
            "postgresql": ["postgres", "postgresql"],
            "mongodb": ["mongo", "mongodb"],
            "mysql": ["mysql"]
        },
        "other": {
            "ollama": ["ollama", "llm"],
            "ai/ml": ["ai", "machine learning", "ml", "tensorflow", "pytorch"],
            "blockchain": ["blockchain", "web3", "ethereum"],
            "cloud": ["aws", "azure", "gcp", "cloud"]
        }
    }

    detected_techs = {
        "frontend": [],
        "backend": [],
        "database": [],
        "other": []
    }

    for category, techs in tech_mapping.items():
        for tech_name, keywords in techs.items():
            if any(keyword in content_text for keyword in keywords):
                detected_techs[category].append(tech_name)

    # Default stack if nothing detected
    if not any(detected_techs.values()):
        detected_techs = {
            "frontend": ["React", "Tailwind CSS"],
            "backend": ["FastAPI", "Python"],
            "database": ["SQLite"],
            "other": ["RESTful API"],
        }
    else:
        # Clean up and format detected technologies
        for category in detected_techs:
            detected_techs[category] = list(set(detected_techs[category]))

    # Format tech stack description
    tech_stack_parts = []
    if detected_techs["frontend"]:
        tech_stack_parts.append(f"Frontend: {', '.join(detected_techs['frontend'])}")
    if detected_techs["backend"]:
        tech_stack_parts.append(f"Backend: {', '.join(detected_techs['backend'])}")
    if detected_techs["database"]:
        tech_stack_parts.append(f"Database: {', '.join(detected_techs['database'])}")
    if detected_techs["other"]:
        tech_stack_parts.append(f"Additional: {', '.join(detected_techs['other'])}")

    # Prefer LLM-produced text when available; otherwise use deterministic fallback
    fallback_text = " | ".join(tech_stack_parts)
    tech_stack = llm_text if llm_text else fallback_text

    # Save the tech stack
    metadata = {
        "detected_technologies": detected_techs,
        "message_count": len(messages),
        "generated_from": "llm_first_fallback_keywords",
        "llm_used": bool(llm_text),
    }

    save_project_artifact(session_id, "tech_stack", tech_stack, metadata)

    return {
        "ok": True,
        "tech_stack": tech_stack,
        "technologies": detected_techs,
        "based_on_messages": len(messages)
    }


def summarize_chat_history(session_id: str) -> Dict[str, Any]:
    """Generate submission notes by summarizing chat history and project progress.

    Attempts an LLM-generated summary first using recent chat messages and known
    artifacts. Falls back to a deterministic rule-based summary.
    """
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    messages = get_chat_messages(session_id)
    if not messages:
        return {"ok": False, "error": "No chat history found for this session"}

    # Get existing project artifacts for context
    project_idea_artifact = get_project_artifact(session_id, "project_idea")
    tech_stack_artifact = get_project_artifact(session_id, "tech_stack")

    # Analyze chat progression
    user_messages = [msg for msg in messages if msg["role"] == "user"]
    assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]

    # Extract key accomplishments and challenges
    accomplishments = []
    challenges = []
    next_steps = []

    # Look for todo-related discussions
    for msg in assistant_messages:
        content = msg["content"].lower()
        if "completed" in content or "done" in content or "finished" in content:
            accomplishments.append("Task completion mentioned in conversation")
        if "issue" in content or "problem" in content or "error" in content:
            challenges.append("Technical challenges discussed")
        if "next" in content or "todo" in content or "plan" in content:
            next_steps.append("Next steps identified")

    # Get current todos
    from models.db import list_todos_db
    todos = list_todos_db(session_id=session_id)
    current_todos = [todo["item"] for todo in todos] if todos else []

    # LLM attempt
    snippets = _build_conversation_snippets(messages, max_messages=40)
    user_prompt = build_submission_summary_user_prompt(
        snippets,
        project_idea_artifact['content'] if project_idea_artifact else None,
        tech_stack_artifact['content'] if tech_stack_artifact else None,
    )
    llm_summary = _ask_llm_once(
        SUBMISSION_SUMMARY_SYSTEM_PROMPT,
        user_prompt,
        temperature=0.1,
        max_tokens=600,
    )

    # Fallback summary
    summary_parts: List[str] = []
    summary_parts.append("## Hackathon Project Summary")
    summary_parts.append(f"**Total Messages:** {len(messages)} ({len(user_messages)} user, {len(assistant_messages)} assistant)")
    if project_idea_artifact:
        summary_parts.append(f"**Project Idea:** {project_idea_artifact['content'][:200]}...")
    if tech_stack_artifact:
        summary_parts.append(f"**Tech Stack:** {tech_stack_artifact['content']}")
    if accomplishments:
        summary_parts.append(f"**Key Accomplishments:** {len(set(accomplishments))} areas of progress")
    if challenges:
        summary_parts.append(f"**Challenges Addressed:** {len(set(challenges))} technical issues discussed")
    if current_todos:
        summary_parts.append(f"**Remaining Tasks:** {len(current_todos)} items in todo list")
        summary_parts.append("  - " + "\n  - ".join(current_todos[:5]))
        if len(current_todos) > 5:
            summary_parts.append(f"  - ... and {len(current_todos) - 5} more")
    if len(messages) > 10:
        summary_parts.append("**Conversation Highlights:**")
        early_context = messages[:2]
        recent_context = messages[-3:]
        for msg in early_context:
            if msg["role"] == "user":
                content = msg["content"][:150] + "..." if len(msg["content"]) > 150 else msg["content"]
                summary_parts.append(f"  - Early: {content}")
        for msg in recent_context:
            if msg["role"] == "user":
                content = msg["content"][:150] + "..." if len(msg["content"]) > 150 else msg["content"]
                summary_parts.append(f"  - Recent: {content}")
    # Ensure a consistent header is present even when LLM returns text
    if llm_summary:
        # If LLM response lacks the expected header, prefix minimal header + stats
        if "## Hackathon Project Summary" not in llm_summary:
            minimal_prefix = "\n\n".join(summary_parts[:2])  # Header + Total Messages line
            submission_summary = f"{minimal_prefix}\n\n{llm_summary}".strip()
        else:
            submission_summary = llm_summary
    else:
        submission_summary = "\n\n".join(summary_parts)

    # Save the summary
    metadata = {
        "message_count": len(messages),
        "user_messages": len(user_messages),
        "assistant_messages": len(assistant_messages),
        "todo_count": len(current_todos),
        "generated_from": "llm_first_fallback_rule_summary",
        "llm_used": bool(llm_summary),
    }

    save_project_artifact(session_id, "submission_summary", submission_summary, metadata)

    return {
        "ok": True,
        "submission_summary": submission_summary,
        "statistics": {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "current_todos": len(current_todos)
        }
    }


# --- Chat title generation ---
def generate_chat_title(session_id: str, force: bool = False) -> Dict[str, Any]:
    """Generate and persist a concise chat title from recent conversation.

    - Uses the local LLM first; falls back to a deterministic title if unavailable
    - Persists the title to `chat_sessions.title` unless one already exists (unless force=True)
    - Returns the chosen title and whether the LLM was used
    """
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    try:
        session = get_chat_session(session_id)
    except Exception:
        session = None

    if session is None:
        return {"ok": False, "error": "Session not found"}

    existing_title = None
    try:
        existing_title = session["title"]
    except Exception:
        try:
            existing_title = session.get("title")  # type: ignore
        except Exception:
            existing_title = None

    if existing_title and not force:
        return {"ok": True, "title": existing_title, "skipped": True}

    messages = get_chat_messages(session_id, limit=40)
    if not messages:
        return {"ok": False, "error": "No chat history found for this session"}

    snippets = _build_conversation_snippets(messages, max_messages=20)

    system_prompt = CHAT_TITLE_SYSTEM_PROMPT
    user_prompt = build_chat_title_user_prompt(snippets)

    def _sanitize_title(text: str) -> str:
        t = (text or "").strip()
        if not t:
            return ""
        # Use only first line if multiple lines were returned
        t = t.splitlines()[0]
        # Remove surrounding quotes/backticks
        if (t.startswith("\"") and t.endswith("\"")) or (t.startswith("'") and t.endswith("'")):
            t = t[1:-1]
        t = t.replace("`", "").strip()
        # Collapse whitespace
        t = " ".join(t.split())
        # Trim length
        if len(t) > 80:
            t = t[:80].rstrip()
        # Remove trailing punctuation that looks like a sentence
        while t and t[-1] in ".!?;,:":
            t = t[:-1]
        return t.strip()

    # Try LLM first (non-streaming for reliability here)
    llm_text = _ask_llm_once_non_stream(system_prompt, user_prompt, temperature=0.2, allow_reasoning_fallback=False)

    # Validate LLM title
    def _valid(title: str) -> bool:
        if not title or len(title.split()) < 2:
            return False
        lower = title.lower()
        for bad in ("new chat", "conversation", "untitled", "no title"):
            if lower == bad:
                return False
        return True

    # Fallback: use first user message snippet
    def _fallback_title() -> str:
        try:
            user_msgs = [m for m in messages if (m.get("role") if isinstance(m, dict) else m["role"]) == "user"]
        except Exception:
            user_msgs = messages
        content = ""
        for m in user_msgs:
            try:
                content = (m.get("content") or "").strip() if isinstance(m, dict) else (m["content"] or "").strip()
            except Exception:
                content = ""
            if content:
                break
        if not content:
            # Last resort generic title with small specificity
            return "Chat Session"
        # Use first sentence-ish or first 8 words
        candidates = content.replace("\n", " ").split(". ")
        first = candidates[0] if candidates else content
        words = first.split()
        short = " ".join(words[:8])
        return _sanitize_title(short)

    final_title = llm_text if _valid(llm_text) else _fallback_title()
    if not _valid(final_title):
        # As a last resort, use a simple two-word title
        final_title = (final_title or "Chat Session").strip()

    try:
        update_chat_session_title(session_id, final_title)
    except Exception:
        return {"ok": False, "error": "Failed to persist title", "title": final_title}

    return {"ok": True, "title": final_title, "llm_used": bool(llm_text)}


# Tool schema definitions for OpenAI-style tool calling
def get_tool_schemas() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_session_id",
                "description": "Return the active chat session_id so the model never needs to ask the user.",
                "parameters": {
                    "type": "object",
                    "properties": {"session_id": {"type": "string"}},
                    "required": []
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_todos",
                "description": "List the current to-do items maintained by the agent.",
                "parameters": {
                    "type": "object",
                    "properties": {"session_id": {"type": "string"}},
                    "required": []
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_todo",
                "description": "Add a new item to the agent to-do list. ONLY add if the user asks for it.",
                "parameters": {
                    "type": "object",
                    "properties": {"item": {"type": "string"}, "session_id": {"type": "string"}},
                    "required": ["item", "session_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "clear_todos",
                "description": "Clear all items from the current chat session to-do list.",
                "parameters": {
                    "type": "object",
                    "properties": {"session_id": {"type": "string"}},
                    "required": ["session_id"]
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "List files and folders within the project directory (safe, relative paths only). when done let user know",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "Relative path from project root"}},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "derive_project_idea",
                "description": "Analyze chat history to automatically derive and save a project idea for the hackathon based on conversation topics.",
                "parameters": {
                    "type": "object",
                    "properties": {"session_id": {"type": "string", "description": "Current chat session ID"}},
                    "required": ["session_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_tech_stack",
                "description": "Analyze chat history to automatically create and save a recommended tech stack based on technologies mentioned in conversation.",
                "parameters": {
                    "type": "object",
                    "properties": {"session_id": {"type": "string", "description": "Current chat session ID"}},
                    "required": ["session_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "summarize_chat_history",
                "description": "Generate comprehensive submission notes by summarizing the entire chat history, progress, and todos for hackathon submission.",
                "parameters": {
                    "type": "object",
                    "properties": {"session_id": {"type": "string", "description": "Current chat session ID"}},
                    "required": ["session_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "generate_chat_title",
                "description": "Create and save a concise, descriptive chat title from recent conversation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Current chat session ID"},
                        "force": {"type": "boolean", "description": "Regenerate even if a title already exists", "default": False},
                    },
                    "required": ["session_id"],
                },
            },
        },
    ]


FUNCTION_DISPATCH = {
    "get_session_id": lambda **kwargs: get_session_id(session_id=kwargs.get("session_id")),
    "list_todos": lambda **kwargs: list_todos(session_id=kwargs.get("session_id")),
    "add_todo": lambda **kwargs: add_todo(kwargs.get("item", ""), session_id=kwargs.get("session_id")),
    "clear_todos": lambda **kwargs: clear_todos(session_id=kwargs.get("session_id")),
    "list_directory": lambda **kwargs: list_directory(kwargs.get("path", ".")),
    "derive_project_idea": lambda **kwargs: derive_project_idea(kwargs.get("session_id", "")),
    "create_tech_stack": lambda **kwargs: create_tech_stack(kwargs.get("session_id", "")),
    "summarize_chat_history": lambda **kwargs: summarize_chat_history(kwargs.get("session_id", "")),
    "generate_chat_title": lambda **kwargs: generate_chat_title(kwargs.get("session_id", ""), force=bool(kwargs.get("force", False))),
}


def call_tool(function_name: str, arguments: Dict[str, Any]) -> Any:
    if function_name not in FUNCTION_DISPATCH:
        return {"ok": False, "error": f"Unknown function: {function_name}"}
    return FUNCTION_DISPATCH[function_name](**arguments)


