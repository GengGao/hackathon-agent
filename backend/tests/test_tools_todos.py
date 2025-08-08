from __future__ import annotations

from pathlib import Path
import tempfile

from models.db import set_db_path, init_db
from tools import list_todos, add_todo, clear_todos


def test_tools_todos_with_db():
    with tempfile.TemporaryDirectory() as td:
        set_db_path(Path(td) / "db.sqlite")
        init_db()
        clear_todos()
        assert list_todos() == []
        add_todo("task1")
        add_todo("task2")
        assert list_todos() == ["task1", "task2"]
        clear_todos()
        assert list_todos() == []


