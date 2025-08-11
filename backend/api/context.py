from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse

from models.db import add_rule_context, get_rules_rows, create_chat_session
from .common import rag, extract_text_from_file, build_url_block


router = APIRouter()


@router.post("/context/rules")
def upload_rules(file: UploadFile = File(...), session_id: Optional[str] = Form(None)):
    """Replace the current rules file & store in DB as a new active context row."""
    content = extract_text_from_file(file)
    if session_id:
        create_chat_session(session_id)
    add_rule_context("file", content, filename=file.filename, active=True, session_id=session_id)
    try:
        rag.set_session(session_id)
    except Exception:
        pass
    rag.rebuild()
    return {"ok": True, "chunks": len(rag.chunks)}


@router.post("/context/add-text")
def add_text_context(text: str = Form(...), session_id: Optional[str] = Form(None)):
    """Add a block of pasted text as context for RAG."""
    cleaned = text.strip()
    if not cleaned:
        return JSONResponse(status_code=400, content={"error": "Empty text"})
    if cleaned.startswith(("http://", "https://")):
        block = build_url_block(cleaned)
        if session_id:
            create_chat_session(session_id)
        add_rule_context("url", block, filename=cleaned, session_id=session_id)
    else:
        if session_id:
            create_chat_session(session_id)
        add_rule_context("text", cleaned, session_id=session_id)
    try:
        rag.set_session(session_id)
    except Exception:
        pass
    rag.rebuild()
    return {"ok": True, "chunks": len(rag.chunks)}


@router.get("/context/status")
def get_context_status(session_id: Optional[str] = Query(None)):
    """Expose current RAG indexing status for the UI, scoped to the provided session."""
    try:
        status = rag.status_scoped(session_id)
        if not status.get("ready") and not status.get("building"):
            try:
                import threading

                threading.Thread(target=rag.rebuild, kwargs={"force": True}, daemon=True).start()
                status = {**status, "building": True}
            except Exception:
                pass
        return status
    except Exception as e:
        return {"ready": False, "building": False, "chunks": 0, "session_id": session_id, "error": str(e)}


@router.get("/context/list")
def list_context(session_id: Optional[str] = Query(None)):
    try:
        rag.set_session(session_id)
    except Exception:
        pass
    return {"items": get_rules_rows(session_id=session_id), "chunks": len(rag.chunks)}


