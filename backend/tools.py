from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import os
from models.db import (
    list_todos_db, add_todo_db, clear_todos_db, update_todo_db, delete_todo_db,
    get_chat_messages, save_project_artifact, get_project_artifact,
    get_all_project_artifacts
)


DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json_file(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_todos(detailed: bool = False) -> List[Any]:
    rows = list_todos_db()
    if detailed:
        # Return dicts with extended fields if present
        out = []
        for r in rows:
            d = {"id": r["id"], "item": r["item"]}
            # sqlite3.Row supports 'k in row.keys()' and item access
            existing_keys = set(r.keys())  # type: ignore
            for k in ("status", "priority", "sort_order", "created_at", "updated_at", "completed_at"):
                if k in existing_keys:
                    d[k] = r[k]
            out.append(d)
        return out
    return [str(r["item"]) for r in rows]


def add_todo(item: str) -> Dict[str, Any]:
    add_todo_db(item)
    todos = list_todos()
    return {"ok": True, "count": len(todos)}


def clear_todos() -> Dict[str, Any]:
    clear_todos_db()
    return {"ok": True}


def update_todo(todo_id: int, **fields) -> Dict[str, Any]:
    ok = update_todo_db(todo_id, **fields)
    return {"ok": ok}


def delete_todo(todo_id: int) -> Dict[str, Any]:
    ok = delete_todo_db(todo_id)
    return {"ok": ok}


def list_directory(path: str = ".") -> Dict[str, Any]:
    # Limited, safe directory listing relative to project root
    root = Path(__file__).resolve().parents[1]
    candidate = (root / path).resolve()
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


def derive_project_idea(session_id: str) -> Dict[str, Any]:
    """Analyze chat history to derive and save a project idea."""
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    # Get recent chat messages
    messages = get_chat_messages(session_id, limit=50)
    if not messages:
        return {"ok": False, "error": "No chat history found for this session"}

    # Analyze messages to extract project-related information
    user_messages = [msg for msg in messages if msg["role"] == "user"]
    assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]

    # Extract key concepts from chat
    content_text = " ".join([msg["content"] for msg in messages])

    # Simple keyword-based project idea extraction
    keywords = []
    tech_terms = ["web", "app", "mobile", "ai", "ml", "blockchain", "api", "dashboard",
                  "automation", "analytics", "chat", "game", "tool", "platform", "system"]

    for term in tech_terms:
        if term.lower() in content_text.lower():
            keywords.append(term)

    # Generate project idea based on analysis
    if keywords:
        project_idea = f"A {' & '.join(keywords[:3])} solution that addresses the problems discussed in the chat. "
        project_idea += "The project leverages modern technologies to create an innovative hackathon submission."
    else:
        project_idea = "An innovative solution derived from the conversation topics and user requirements discussed."

    # Add more context from recent user messages
    if user_messages:
        recent_context = user_messages[-3:]  # Last 3 user messages
        context_summary = " Key focus areas include: " + "; ".join([
            msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            for msg in recent_context
        ])
        project_idea += context_summary

    # Save the project idea
    metadata = {
        "keywords": keywords,
        "message_count": len(messages),
        "generated_from": "chat_analysis"
    }

    save_project_artifact(session_id, "project_idea", project_idea, metadata)

    return {
        "ok": True,
        "project_idea": project_idea,
        "keywords": keywords,
        "based_on_messages": len(messages)
    }


def create_tech_stack(session_id: str) -> Dict[str, Any]:
    """Analyze chat history to create and save a recommended tech stack."""
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    messages = get_chat_messages(session_id, limit=50)
    if not messages:
        return {"ok": False, "error": "No chat history found for this session"}

    content_text = " ".join([msg["content"] for msg in messages]).lower()

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
            "other": ["RESTful API"]
        }
    else:
        # Clean up and format detected technologies
        for category in detected_techs:
            detected_techs[category] = list(set(detected_techs[category]))  # Remove duplicates

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

    tech_stack = " | ".join(tech_stack_parts)

    # Save the tech stack
    metadata = {
        "detected_technologies": detected_techs,
        "message_count": len(messages),
        "generated_from": "chat_analysis"
    }

    save_project_artifact(session_id, "tech_stack", tech_stack, metadata)

    return {
        "ok": True,
        "tech_stack": tech_stack,
        "technologies": detected_techs,
        "based_on_messages": len(messages)
    }


def summarize_chat_history(session_id: str) -> Dict[str, Any]:
    """Generate submission notes by summarizing chat history and project progress."""
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
    todos = list_todos_db()
    current_todos = [todo["item"] for todo in todos] if todos else []

    # Build summary
    summary_parts = []

    summary_parts.append(f"## Hackathon Project Summary")
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
        summary_parts.append("  - " + "\n  - ".join(current_todos[:5]))  # Show first 5 todos
        if len(current_todos) > 5:
            summary_parts.append(f"  - ... and {len(current_todos) - 5} more")

    # Add conversation highlights
    if len(messages) > 10:
        summary_parts.append(f"**Conversation Highlights:**")
        # Get first and last few messages for context
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

    submission_summary = "\n\n".join(summary_parts)

    # Save the summary
    metadata = {
        "message_count": len(messages),
        "user_messages": len(user_messages),
        "assistant_messages": len(assistant_messages),
        "todo_count": len(current_todos),
        "generated_from": "full_chat_analysis"
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


# Tool schema definitions for OpenAI-style tool calling
def get_tool_schemas() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_todos",
                "description": "List the current to-do items maintained by the agent.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_todo",
                "description": "Add a new item to the agent to-do list.",
                "parameters": {
                    "type": "object",
                    "properties": {"item": {"type": "string"}},
                    "required": ["item"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "clear_todos",
                "description": "Clear all items from the agent to-do list.",
                "parameters": {"type": "object", "properties": {}, "required": []},
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
    ]


FUNCTION_DISPATCH = {
    "list_todos": lambda **kwargs: list_todos(),
    "add_todo": lambda **kwargs: add_todo(kwargs.get("item", "")),
    "clear_todos": lambda **kwargs: clear_todos(),
    "list_directory": lambda **kwargs: list_directory(kwargs.get("path", ".")),
    "derive_project_idea": lambda **kwargs: derive_project_idea(kwargs.get("session_id", "")),
    "create_tech_stack": lambda **kwargs: create_tech_stack(kwargs.get("session_id", "")),
    "summarize_chat_history": lambda **kwargs: summarize_chat_history(kwargs.get("session_id", "")),
}


def call_tool(function_name: str, arguments: Dict[str, Any]) -> Any:
    if function_name not in FUNCTION_DISPATCH:
        return {"ok": False, "error": f"Unknown function: {function_name}"}
    return FUNCTION_DISPATCH[function_name](**arguments)


