from typing import Optional, Any, Dict, List

from fastapi import APIRouter, Query, Form
from fastapi.responses import JSONResponse

from models.db import (
    create_chat_session,
    get_chat_session,
    add_chat_message,
    get_chat_messages,
    update_chat_session_title,
    get_recent_chat_sessions,
    delete_chat_session,
    get_project_artifact,
    get_all_project_artifacts,
)
from models.schemas import ChatSession, ChatMessage, ProjectArtifact
from utils.text import strip_context_blocks


router = APIRouter()


@router.get("/chat-sessions")
def get_chat_sessions(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    sessions = get_recent_chat_sessions(limit=limit + offset)
    sliced = sessions[offset : offset + limit]
    return {
        "sessions": [ChatSession.from_row(row).model_dump() for row in sliced],
        "total_fetched": len(sessions),
        "offset": offset,
        "limit": limit,
    }


@router.get("/chat-sessions/{session_id}")
def get_chat_session_detail(
    session_id: str, limit: Optional[int] = Query(None, ge=1, le=1000), offset: int = Query(0, ge=0)
):
    session = get_chat_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    all_messages = get_chat_messages(session_id)
    if limit is None:
        paged = all_messages
    else:
        paged = all_messages[offset : offset + limit]
    out_messages: List[Dict[str, Any]] = []
    for row in paged:
        msg = ChatMessage.from_row(row)
        msg.content = strip_context_blocks(msg.content)
        out_messages.append(msg.model_dump())
    return {
        "session": ChatSession.from_row(session).model_dump(),
        "messages": out_messages,
        "total_messages": len(all_messages),
        "offset": offset,
        "limit": limit if limit is not None else len(all_messages),
    }


@router.put("/chat-sessions/{session_id}/title")
def update_session_title(session_id: str, title: str = Form(...)):
    session = get_chat_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    update_chat_session_title(session_id, title)
    return {"ok": True}


@router.delete("/chat-sessions/{session_id}")
def delete_session(session_id: str):
    session = get_chat_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    delete_chat_session(session_id)
    return {"ok": True}


@router.get("/chat-sessions/{session_id}/project-artifacts")
def get_project_artifacts_route(session_id: str):
    try:
        artifacts = get_all_project_artifacts(session_id)
        return {"artifacts": [ProjectArtifact.from_row(row).model_dump() for row in artifacts]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/chat-sessions/{session_id}/project-artifacts/{artifact_type}")
def get_specific_project_artifact_route(session_id: str, artifact_type: str):
    try:
        artifact = get_project_artifact(session_id, artifact_type)
        if not artifact:
            return JSONResponse(status_code=404, content={"error": "Artifact not found"})
        return {"artifact": ProjectArtifact.from_row(artifact).model_dump()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


