from __future__ import annotations

from pathlib import Path
import tempfile

from models.db import set_db_path, init_db
from tools import list_todos, add_todo, clear_todos


def test_tools_todos_with_db():
    with tempfile.TemporaryDirectory() as td:
        set_db_path(Path(td) / "db.sqlite")
        init_db()
        # Defaults to global (no session) scope
        clear_todos()
        assert list_todos() == []
        add_todo("task1")
        add_todo("task2")
        assert list_todos() == ["task1", "task2"]
        # Session-scoped entries do not leak into global listing
        add_todo("s1-a", session_id="s1")
        add_todo("s1-b", session_id="s1")
        assert list_todos() == ["task1", "task2"]
        assert list_todos(session_id="s1") == ["s1-a", "s1-b"]
        out = clear_todos(session_id="s1")
        assert out.get("deleted", 0) >= 0
        assert list_todos(session_id="s1") == []
        # Clear without session should be rejected at API level; tool returns no-op
        out2 = clear_todos()
        assert out2.get("deleted", 0) == 0
        # Manually clean global items by specifying empty session is not supported; leave as-is


