from __future__ import annotations

from typing import Optional, Dict, Any
import io
import json
import zipfile
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import Response, JSONResponse

from models.db import (
    get_chat_session,
    create_chat_session,
    get_chat_messages,
    get_project_artifact,
    list_todos_db,
    list_active_rules,
)


router = APIRouter()


@router.post("/export/submission-pack")
def export_submission_pack(session_id: Optional[str] = Query(None)):
    if not session_id:
        return JSONResponse(status_code=400, content={"error": "session_id is required"})

    session = get_chat_session(session_id)
    if not session:
        try:
            create_chat_session(session_id)
        except Exception:
            pass
        session = get_chat_session(session_id)

    # Collect artifacts (fallback to friendly text if missing)
    def _artifact_present(art_type: str) -> bool:
        art = get_project_artifact(session_id, art_type)
        if not art:
            return False
        try:
            content_val = art["content"]
        except Exception:
            try:
                content_val = art.get("content")
            except Exception:
                content_val = None
        return bool(content_val and str(content_val).strip())

    def _artifact_text(art_type: str, fallback: str) -> str:
        art = get_project_artifact(session_id, art_type)
        if art:
            try:
                content_val = art["content"]
            except Exception:
                try:
                    # type: ignore[attr-defined]
                    content_val = art.get("content")
                except Exception:
                    content_val = None
            if content_val:
                text = str(content_val).strip()
                if text:
                    return text
        return fallback

    has_idea = _artifact_present("project_idea")
    has_stack = _artifact_present("tech_stack")
    has_summary = _artifact_present("submission_summary")

    if not (has_idea or has_stack or has_summary):
        return JSONResponse(
            status_code=404,
            content={
                "error": "No artifacts generated yet for this session. Use the dashboard to generate Project Idea, Tech Stack, or Submission Notes, then export again.",
            },
        )

    idea_md = _artifact_text(
        "project_idea",
        "No project idea generated yet. Use the dashboard to generate one.",
    )
    stack_md = _artifact_text(
        "tech_stack",
        "No tech stack generated yet. Use the dashboard to generate one.",
    )
    summary_md = _artifact_text(
        "submission_summary",
        "No submission summary generated yet. Use the dashboard to generate one.",
    )

    # Todos as JSON
    todos_rows = list_todos_db(session_id=session_id)
    todos_json = [
        {
            "id": r["id"],
            "item": r["item"],
            **({"status": r["status"]} if "status" in r.keys() else {}),
            **({"sort_order": r["sort_order"]} if "sort_order" in r.keys() else {}),
            **({"created_at": r["created_at"]} if "created_at" in r.keys() else {}),
            **({"updated_at": r["updated_at"]} if "updated_at" in r.keys() else {}),
            **({"completed_at": r["completed_at"]} if "completed_at" in r.keys() else {}),
        }
        for r in todos_rows
    ]

    # Rules text
    rules_list = list_active_rules(session_id=session_id)
    if not rules_list:
        rules_text = "No rules/context available."
    else:
        # Delimit chunks deterministically
        parts = []
        for idx, txt in enumerate(rules_list, start=1):
            parts.append(f"===== RULE CHUNK {idx} =====\n{txt.strip()}\n")
        rules_text = "\n".join(parts)

    # Session metadata
    messages = get_chat_messages(session_id)
    meta: Dict[str, Any] = {}
    try:
        meta.update(
            {
                "session_id": session["session_id"],
                "title": session["title"],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
            }
        )
    except Exception:
        # Fallback shape if row access differs
        meta.update({"session_id": session_id})
    meta.update(
        {
            "messages_count": len(messages),
            "todos_count": len(todos_json),
            "rules_chunks": len(rules_list),
            "artifacts_present": {
                "project_idea": bool(_artifact_text("project_idea", "").strip()),
                "tech_stack": bool(_artifact_text("tech_stack", "").strip()),
                "submission_summary": bool(_artifact_text("submission_summary", "").strip()),
            },
            "exported_at": datetime.utcnow().isoformat() + "Z",
        }
    )

    # Build zip in-memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("idea.md", idea_md + ("\n" if not idea_md.endswith("\n") else ""))
        zf.writestr("tech_stack.md", stack_md + ("\n" if not stack_md.endswith("\n") else ""))
        zf.writestr("summary.md", summary_md + ("\n" if not summary_md.endswith("\n") else ""))
        zf.writestr("todos.json", json.dumps(todos_json, ensure_ascii=False, indent=2))
        zf.writestr("rules_ingested.txt", rules_text)
        zf.writestr("session_metadata.json", json.dumps(meta, ensure_ascii=False, indent=2))

    buf.seek(0)
    filename = f"submission_pack_{session_id[:8]}.zip"
    headers = {
        "Content-Disposition": f"attachment; filename=\"{filename}\"",
        "Cache-Control": "no-store",
    }
    return Response(content=buf.read(), media_type="application/zip", headers=headers)


