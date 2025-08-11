from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.db import get_chat_session, get_chat_messages, update_chat_session_title
from prompts import (
    CHAT_TITLE_SYSTEM_PROMPT,
    build_chat_title_user_prompt,
)
from .llm_helpers import _build_conversation_snippets, _ask_llm_once_non_stream


def generate_chat_title(session_id: str, force: bool = False) -> Dict[str, Any]:
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
        t = t.splitlines()[0]
        if (t.startswith("\"") and t.endswith("\"")) or (t.startswith("'") and t.endswith("'")):
            t = t[1:-1]
        t = t.replace("`", "").strip()
        t = " ".join(t.split())
        if len(t) > 80:
            t = t[:80].rstrip()
        while t and t[-1] in ".!?;,:":
            t = t[:-1]
        return t.strip()

    llm_text = _ask_llm_once_non_stream(
        system_prompt,
        user_prompt,
        temperature=0.2,
        allow_reasoning_fallback=False,
        seed_messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    def _valid(title: str) -> bool:
        if not title or len(title.split()) < 2:
            return False
        lower = title.lower()
        for bad in ("new chat", "conversation", "untitled", "no title"):
            if lower == bad:
                return False
        return True

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
            return "Chat Session"
        candidates = content.replace("\n", " ").split(". ")
        first = candidates[0] if candidates else content
        words = first.split()
        short = " ".join(words[:8])
        return _sanitize_title(short)

    final_title = llm_text if _valid(llm_text) else _fallback_title()
    if not _valid(final_title):
        final_title = (final_title or "Chat Session").strip()

    try:
        update_chat_session_title(session_id, final_title)
    except Exception:
        return {"ok": False, "error": "Failed to persist title", "title": final_title}

    return {"ok": True, "title": final_title, "llm_used": bool(llm_text)}


__all__ = ["generate_chat_title"]


