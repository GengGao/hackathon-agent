from __future__ import annotations

from pathlib import Path
import os
import tempfile

from models.db import (
    set_db_path,
    init_db,
    create_project,
    get_project_by_name,
    add_project_file,
    list_project_files,
    list_todos_db,
    add_todo_db,
    clear_todos_db,
)


def with_temp_db(func):
    def wrapper():
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test.db"
            set_db_path(db_path)
            init_db()
            func()
    return wrapper


@with_temp_db
def test_projects_and_files_crud():
    pid = create_project("demo", "desc")
    row = get_project_by_name("demo")
    assert row is not None and row["id"] == pid

    fid = add_project_file(pid, "file.txt", "/abs/file.txt", "text/plain", 12)
    files = list_project_files(pid)
    assert len(files) == 1
    f = files[0]
    assert f["id"] == fid and f["filename"] == "file.txt"


@with_temp_db
def test_todos_crud():
    assert list_todos_db() == []
    add_todo_db("a")
    add_todo_db("b")
    items = [r["item"] for r in list_todos_db()]
    assert items == ["a", "b"]
    clear_todos_db()
    assert list_todos_db() == []


