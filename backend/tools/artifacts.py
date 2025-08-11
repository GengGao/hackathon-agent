from __future__ import annotations

from typing import Any, Dict, List, Optional
import asyncio

from models.db import (
    get_chat_messages,
    save_project_artifact,
    get_project_artifact,
    list_todos_db,
)
from llm import client as llm_client, get_current_model
from utils.text import strip_context_blocks
from prompts import (
    TECH_STACK_SYSTEM_PROMPT,
    PROJECT_IDEA_SYSTEM_PROMPT,
    SUBMISSION_SUMMARY_SYSTEM_PROMPT,
    build_project_idea_user_prompt,
    build_tech_stack_user_prompt,
    build_submission_summary_user_prompt,
)
from .llm_helpers import (
    _build_conversation_snippets,
    _ask_llm_once,
)


def derive_project_idea(session_id: str) -> Dict[str, Any]:
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    messages = get_chat_messages(session_id, limit=50)
    if not messages:
        return {"ok": False, "error": "No chat history found for this session"}

    snippets = _build_conversation_snippets(messages)
    user_prompt = build_project_idea_user_prompt(snippets)
    seed_messages: List[Dict[str, Any]] = [{"role": "system", "content": PROJECT_IDEA_SYSTEM_PROMPT}]
    for m in messages[-20:]:
        try:
            role = m["role"] if isinstance(m, dict) else m["role"]
            content_full = (m["content"] if isinstance(m, dict) else m["content"]) or ""
        except Exception:
            role, content_full = "user", ""
        if content_full:
            seed_messages.append({"role": role, "content": content_full})
    seed_messages.append({"role": "user", "content": user_prompt})

    project_idea_llm = _ask_llm_once(
        PROJECT_IDEA_SYSTEM_PROMPT,
        user_prompt,
        temperature=0.2,
        max_tokens=256,
        seed_messages=seed_messages,
    )

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
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    messages = get_chat_messages(session_id, limit=50)
    if not messages:
        return {"ok": False, "error": "No chat history found for this session"}

    content_text = " ".join([msg["content"] for msg in messages]).lower()

    llm_text: str = ""
    try:
        system_prompt = TECH_STACK_SYSTEM_PROMPT
        convo_snippets = _build_conversation_snippets(messages, max_messages=20)
        user_prompt = build_tech_stack_user_prompt(convo_snippets)

        seed_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for m in messages[-20:]:
            try:
                role = m["role"] if isinstance(m, dict) else m["role"]
                content_full = (m["content"] if isinstance(m, dict) else m["content"]) or ""
            except Exception:
                role, content_full = "user", ""
            if content_full:
                seed_messages.append({"role": role, "content": content_full})
        seed_messages.append({"role": "user", "content": user_prompt})

        async def _ask_llm() -> str:
            resp = await llm_client.chat.completions.create(
                model=get_current_model(),
                messages=seed_messages,
                temperature=0.2,
                max_tokens=512,
                stream=False,
            )
            try:
                return (resp.choices[0].message.content or "").strip()
            except Exception:
                return ""

        llm_text = asyncio.run(_ask_llm())
    except Exception:
        llm_text = ""

    tech_mapping = {
        "frontend": {
            "react": ["react", "jsx", "create-react-app"],
            "vue": ["vue", "vuejs"],
            "angular": ["angular"],
            "svelte": ["svelte"],
            "html/css/js": ["html", "css", "javascript", "js"],
        },
        "backend": {
            "fastapi": ["fastapi", "uvicorn"],
            "express": ["express", "nodejs", "node.js"],
            "django": ["django"],
            "flask": ["flask"],
            "python": ["python"],
            "node.js": ["node", "nodejs"],
        },
        "database": {
            "sqlite": ["sqlite"],
            "postgresql": ["postgres", "postgresql"],
            "mongodb": ["mongo", "mongodb"],
            "mysql": ["mysql"],
        },
        "other": {
            "ollama": ["ollama", "llm"],
            "ai/ml": ["ai", "machine learning", "ml", "tensorflow", "pytorch"],
            "blockchain": ["blockchain", "web3", "ethereum"],
            "cloud": ["aws", "azure", "gcp", "cloud"],
        },
    }

    detected_techs = {"frontend": [], "backend": [], "database": [], "other": []}
    for category, techs in tech_mapping.items():
        for tech_name, keywords in techs.items():
            if any(keyword in content_text for keyword in keywords):
                detected_techs[category].append(tech_name)

    if not any(detected_techs.values()):
        detected_techs = {
            "frontend": ["React", "Tailwind CSS"],
            "backend": ["FastAPI", "Python"],
            "database": ["SQLite"],
            "other": ["RESTful API"],
        }
    else:
        for category in detected_techs:
            detected_techs[category] = list(set(detected_techs[category]))

    parts = []
    if detected_techs["frontend"]:
        parts.append(f"Frontend: {', '.join(detected_techs['frontend'])}")
    if detected_techs["backend"]:
        parts.append(f"Backend: {', '.join(detected_techs['backend'])}")
    if detected_techs["database"]:
        parts.append(f"Database: {', '.join(detected_techs['database'])}")
    if detected_techs["other"]:
        parts.append(f"Additional: {', '.join(detected_techs['other'])}")

    tech_stack = llm_text if llm_text else " | ".join(parts)

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
        "based_on_messages": len(messages),
    }


def summarize_chat_history(session_id: str) -> Dict[str, Any]:
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    messages = get_chat_messages(session_id)
    if not messages:
        return {"ok": False, "error": "No chat history found for this session"}

    project_idea_artifact = get_project_artifact(session_id, "project_idea")
    tech_stack_artifact = get_project_artifact(session_id, "tech_stack")

    user_messages = [msg for msg in messages if msg["role"] == "user"]
    assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]

    accomplishments: List[str] = []
    challenges: List[str] = []
    next_steps: List[str] = []

    for msg in assistant_messages:
        content = msg["content"].lower()
        if "completed" in content or "done" in content or "finished" in content:
            accomplishments.append("Task completion mentioned in conversation")
        if "issue" in content or "problem" in content or "error" in content:
            challenges.append("Technical challenges discussed")
        if "next" in content or "todo" in content or "plan" in content:
            next_steps.append("Next steps identified")

    todos = list_todos_db(session_id=session_id)
    current_todos = [todo["item"] for todo in todos] if todos else []

    snippets = _build_conversation_snippets(messages, max_messages=40)
    user_prompt = build_submission_summary_user_prompt(
        snippets,
        project_idea_artifact['content'] if project_idea_artifact else None,
        tech_stack_artifact['content'] if tech_stack_artifact else None,
    )

    seed_messages: List[Dict[str, Any]] = [{"role": "system", "content": SUBMISSION_SUMMARY_SYSTEM_PROMPT}]
    for m in messages[-40:]:
        try:
            role = m["role"] if isinstance(m, dict) else m["role"]
            content_full = (m["content"] if isinstance(m, dict) else m["content"]) or ""
        except Exception:
            role, content_full = "user", ""
        if content_full:
            seed_messages.append({"role": role, "content": content_full})
    seed_messages.append({"role": "user", "content": user_prompt})

    llm_summary = _ask_llm_once(
        SUBMISSION_SUMMARY_SYSTEM_PROMPT,
        user_prompt,
        temperature=0.1,
        max_tokens=600,
        seed_messages=seed_messages,
    )

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

    if llm_summary:
        if "## Hackathon Project Summary" not in llm_summary:
            minimal_prefix = "\n\n".join(summary_parts[:2])
            submission_summary = f"{minimal_prefix}\n\n{llm_summary}".strip()
        else:
            submission_summary = llm_summary
    else:
        submission_summary = "\n\n".join(summary_parts)

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
            "current_todos": len(current_todos),
        },
    }


__all__ = [
    "derive_project_idea",
    "create_tech_stack",
    "summarize_chat_history",
]


