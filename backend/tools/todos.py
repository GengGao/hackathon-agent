from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.db import (
    list_todos_db, add_todo_db, clear_todos_db, update_todo_db, delete_todo_db,
)


def list_todos(detailed: bool = False, session_id: Optional[str] = None) -> List[Any]:
    rows = list_todos_db(session_id=session_id)
    if detailed:
        out = []
        for r in rows:
            d: Dict[str, Any] = {"id": r["id"], "item": r["item"]}
            existing_keys = set(r.keys())  # type: ignore
            for k in ("status", "sort_order", "created_at", "updated_at", "completed_at"):
                if k in existing_keys:
                    d[k] = r[k]
            if "session_id" in existing_keys:
                d["session_id"] = r["session_id"]
            out.append(d)
        return out
    return [str(r["item"]) for r in rows]


def add_todo(item: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    add_todo_db(item, session_id=session_id)
    todos = list_todos(session_id=session_id)
    return {"ok": True, "count": len(todos)}


def clear_todos(session_id: Optional[str] = None) -> Dict[str, Any]:
    if not session_id:
        return {"ok": True, "deleted": 0}
    deleted = clear_todos_db(session_id=session_id)
    return {"ok": True, "deleted": deleted}


def update_todo(todo_id: int, **fields) -> Dict[str, Any]:
    ok = update_todo_db(todo_id, **fields)
    return {"ok": ok}


def delete_todo(todo_id: int, session_id: Optional[str] = None) -> Dict[str, Any]:
    ok = delete_todo_db(todo_id, session_id=session_id)
    return {"ok": ok}


# Convenience functions for common status updates
def mark_todo_done(todo_id: int, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Mark a specific todo as completed (done)."""
    ok = update_todo_db(todo_id, status="done", session_id=session_id)
    return {"ok": ok}


def mark_todo_in_progress(todo_id: int, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Mark a specific todo as in progress."""
    ok = update_todo_db(todo_id, status="in_progress", session_id=session_id)
    return {"ok": ok}


def mark_todo_pending(todo_id: int, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Mark a specific todo as pending."""
    ok = update_todo_db(todo_id, status="pending", session_id=session_id)
    return {"ok": ok}


__all__ = [
    "list_todos",
    "add_todo",
    "clear_todos",
    "update_todo",
    "delete_todo",
    "mark_todo_done",
    "mark_todo_in_progress",
    "mark_todo_pending",
]


