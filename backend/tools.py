from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import os


DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
TODOS_FILE = DATA_DIR / "todos.json"


def _read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json_file(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_todos() -> List[str]:
    todos = _read_json_file(TODOS_FILE, [])
    if not isinstance(todos, list):
        todos = []
    return todos


def add_todo(item: str) -> Dict[str, Any]:
    todos = list_todos()
    todos.append(item)
    _write_json_file(TODOS_FILE, todos)
    return {"ok": True, "count": len(todos)}


def clear_todos() -> Dict[str, Any]:
    _write_json_file(TODOS_FILE, [])
    return {"ok": True}


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
    ]


FUNCTION_DISPATCH = {
    "list_todos": lambda **kwargs: list_todos(),
    "add_todo": lambda **kwargs: add_todo(kwargs.get("item", "")),
    "clear_todos": lambda **kwargs: clear_todos(),
    "list_directory": lambda **kwargs: list_directory(kwargs.get("path", ".")),
}


def call_tool(function_name: str, arguments: Dict[str, Any]) -> Any:
    if function_name not in FUNCTION_DISPATCH:
        return {"ok": False, "error": f"Unknown function: {function_name}"}
    return FUNCTION_DISPATCH[function_name](**arguments)


