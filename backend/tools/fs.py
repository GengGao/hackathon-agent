from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def list_directory(path: str = ".") -> Dict[str, Any]:
    # Limited, safe directory listing relative to project root
    root = Path(__file__).resolve().parents[1]
    normalized = (path or ".").replace("\\", "/").strip()
    if normalized == "":
        normalized = "."
    candidate = (root / normalized).resolve()
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


__all__ = ["list_directory"]


