from __future__ import annotations

# Public API facade for tools

# Import lightweight modules eagerly
from .session import get_session_id
from .todos import list_todos, add_todo, clear_todos, update_todo, delete_todo
from .fs import list_directory


# Heavy modules (LLM access) are imported lazily inside wrapper functions
def derive_project_idea(session_id: str):
    from .artifacts import derive_project_idea as _impl
    return _impl(session_id)


def create_tech_stack(session_id: str):
    from .artifacts import create_tech_stack as _impl
    return _impl(session_id)


def summarize_chat_history(session_id: str):
    from .artifacts import summarize_chat_history as _impl
    return _impl(session_id)


def generate_chat_title(session_id: str, force: bool = False):
    from .titles import generate_chat_title as _impl
    return _impl(session_id, force=force)


def ask_llm_stream(system_prompt: str, user_prompt: str, *, temperature: float = 0.2, max_tokens: int = 512, seed_messages=None):
    from .llm_helpers import ask_llm_stream as _impl
    return _impl(system_prompt, user_prompt, temperature=temperature, max_tokens=max_tokens, seed_messages=seed_messages)


from .registry import get_tool_schemas, call_tool


__all__ = [
    "get_session_id",
    "list_todos",
    "add_todo",
    "clear_todos",
    "update_todo",
    "delete_todo",
    "list_directory",
    "derive_project_idea",
    "create_tech_stack",
    "summarize_chat_history",
    "generate_chat_title",
    "ask_llm_stream",
    "get_tool_schemas",
    "call_tool",
]


