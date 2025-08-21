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
        {
            "type": "function",
            "function": {
                "name": "get_conversation_insights",
                "description": "Analyze conversation insights from chat history including decisions made, technologies chosen, problems solved, and current blockers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Current chat session ID"},
                        "message_limit": {"type": "integer", "description": "Maximum number of recent messages to analyze", "default": 50},
                    },
                    "required": ["session_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_project_progress",
                "description": "Analyze project progress from chat history including completed tasks, current blockers, in-progress work, and milestone updates.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Current chat session ID"},
                        "message_limit": {"type": "integer", "description": "Maximum number of recent messages to analyze", "default": 50},
                    },
                    "required": ["session_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_focused_summary",
                "description": "Get a focused summary of conversation insights with specific focus areas: decisions, blockers, progress, technologies, or comprehensive.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Current chat session ID"},
                        "focus": {"type": "string", "description": "Focus area: decisions, blockers, progress, technologies, or comprehensive", "default": "comprehensive"},
                    },
                    "required": ["session_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_actionable_recommendations",
                "description": "Get actionable insights and recommendations from conversation analysis including priority recommendations and project health assessment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Current chat session ID"},
                    },
                    "required": ["session_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_team_decisions",
                "description": "Extract and analyze key decisions made by the team including technology choices, architecture decisions, and decision-making patterns.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Current chat session ID"},
                    },
                    "required": ["session_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "track_problem_resolution",
                "description": "Track problems encountered and their resolution status including solution success rate and recurring issues.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Current chat session ID"},
                    },
                    "required": ["session_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_extraction_status",
                "description": "Get the status and progress of a background extraction task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task ID returned from starting an extraction"},
                    },
                    "required": ["task_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_extraction_result",
                "description": "Get the result of a completed background extraction task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task ID of the completed extraction"},
                    },
                    "required": ["task_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_session_extractions",
                "description": "List all extraction tasks for a specific chat session.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Chat session ID to check"},
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
        if function_name == "get_conversation_insights":
            from .insight_tools import get_conversation_insights as fn
            return fn(arguments.get("session_id", ""), arguments.get("message_limit", 50))
        if function_name == "get_project_progress":
            from .insight_tools import get_project_progress as fn
            return fn(arguments.get("session_id", ""), arguments.get("message_limit", 50))
        if function_name == "get_focused_summary":
            from .insight_tools import get_focused_summary as fn
            return fn(arguments.get("session_id", ""), arguments.get("focus", "comprehensive"))
        if function_name == "get_actionable_recommendations":
            from .insight_tools import get_actionable_recommendations as fn
            return fn(arguments.get("session_id", ""))
        if function_name == "analyze_team_decisions":
            from .insight_tools import analyze_team_decisions as fn
            return fn(arguments.get("session_id", ""))
        if function_name == "track_problem_resolution":
            from .insight_tools import track_problem_resolution as fn
            return fn(arguments.get("session_id", ""))
        if function_name == "get_extraction_status":
            from .insight_tools import get_extraction_status as fn
            return fn(arguments.get("task_id", ""))
        if function_name == "get_extraction_result":
            from .insight_tools import get_extraction_result as fn
            return fn(arguments.get("task_id", ""))
        if function_name == "list_session_extractions":
            from .insight_tools import list_session_extractions as fn
            return fn(arguments.get("session_id", ""))
        return {"ok": False, "error": f"Unknown function: {function_name}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


__all__ = [
    "get_tool_schemas",
    "call_tool",
]


