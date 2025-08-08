from __future__ import annotations

from pathlib import Path
import tempfile

from models.db import (
    set_db_path,
    init_db,
    create_project,
    get_project_by_name,
    add_project_file,
    list_project_files,
)
from models.schemas import Project, ProjectFile


def test_pydantic_models_from_rows():
    with tempfile.TemporaryDirectory() as td:
        set_db_path(Path(td) / "db.sqlite")
        init_db()
        pid = create_project("p1", "d")
        row = get_project_by_name("p1")
        p = Project.from_row(row)
        assert p.id == pid and p.name == "p1" and p.description == "d"

        fid = add_project_file(pid, "a.txt", "/tmp/a.txt", "text/plain", 1)
        rows = list_project_files(pid)
        pf = ProjectFile.from_row(rows[0])
        assert pf.id == fid and pf.project_id == pid and pf.filename == "a.txt"


