from __future__ import annotations

from typing import Any, Dict, List

# Intentionally avoid importing heavy modules at import time.
# Resolution happens lazily inside call_tool.


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


def call_tool(function_name: str, arguments: Dict[str, Any]) -> Any:
    """Resolve and execute tool by name with lazy imports to avoid heavy deps at import-time."""
    try:
        if function_name == "get_session_id":
            from .session import get_session_id as fn
            return fn(session_id=arguments.get("session_id"))
        if function_name == "list_todos":
            from .todos import list_todos as fn
            return fn(session_id=arguments.get("session_id"))
        if function_name == "add_todo":
            from .todos import add_todo as fn
            return fn(arguments.get("item", ""), session_id=arguments.get("session_id"))
        if function_name == "clear_todos":
            from .todos import clear_todos as fn
            return fn(session_id=arguments.get("session_id"))
        if function_name == "list_directory":
            from .fs import list_directory as fn
            return fn(arguments.get("path", "."))
        if function_name == "derive_project_idea":
            from .artifacts import derive_project_idea as fn
            return fn(arguments.get("session_id", ""))
        if function_name == "create_tech_stack":
            from .artifacts import create_tech_stack as fn
            return fn(arguments.get("session_id", ""))
        if function_name == "summarize_chat_history":
            from .artifacts import summarize_chat_history as fn
            return fn(arguments.get("session_id", ""))
        if function_name == "generate_chat_title":
            from .titles import generate_chat_title as fn
            return fn(arguments.get("session_id", ""), force=bool(arguments.get("force", False)))
        return {"ok": False, "error": f"Unknown function: {function_name}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


__all__ = [
    "get_tool_schemas",
    "call_tool",
]


