from typing import Optional, Any, Dict, List

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from tools import (
    derive_project_idea,
    create_tech_stack,
    summarize_chat_history,
    ask_llm_stream,
)
from prompts import (
    PROJECT_IDEA_SYSTEM_PROMPT,
    TECH_STACK_SYSTEM_PROMPT,
    SUBMISSION_SUMMARY_SYSTEM_PROMPT,
    build_project_idea_user_prompt,
    build_tech_stack_user_prompt,
    build_submission_summary_user_prompt,
)
from models.db import (
    get_chat_messages,
    get_project_artifact,
    save_project_artifact,
)
from fastapi.responses import StreamingResponse
import json


router = APIRouter()


@router.post("/chat-sessions/{session_id}/derive-project-idea")
def derive_project_idea_route(session_id: str, stream: Optional[bool] = Query(False)):
    try:
        if not stream:
            result = derive_project_idea(session_id)
            return result

        msgs = get_chat_messages(session_id, limit=50)
        if not msgs:
            return JSONResponse(status_code=400, content={"error": "No chat history found for this session"})

        def _get_field(m, k):
            try:
                return m[k]
            except Exception:
                return m.get(k)

        snippets: List[str] = []
        for m in msgs[-20:]:
            role = _get_field(m, "role") or "user"
            content = (_get_field(m, "content") or "")
            content = content[:217] + "..." if len(content) > 220 else content
            if content:
                snippets.append(f"- {role}: {content}")
        user_prompt = build_project_idea_user_prompt(snippets)

        seed_messages: List[Dict[str, Any]] = [{"role": "system", "content": PROJECT_IDEA_SYSTEM_PROMPT}]
        for m in msgs[-20:]:
            try:
                role = _get_field(m, "role") or "user"
                content_full = (_get_field(m, "content") or "")
                if content_full:
                    seed_messages.append({"role": role, "content": content_full})
            except Exception:
                continue
        seed_messages.append({"role": "user", "content": user_prompt})

        async def token_generator():
            final_parts: List[str] = []
            try:
                async for chunk in ask_llm_stream(
                    PROJECT_IDEA_SYSTEM_PROMPT,
                    user_prompt,
                    temperature=0.2,
                    max_tokens=256,
                    seed_messages=seed_messages,
                ):
                    final_parts.append(chunk)
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
            except Exception:
                pass
            full_text = ("".join(final_parts)).strip()
            if not full_text:
                content_text = " ".join([_get_field(m, "content") or "" for m in msgs])
                tech_terms = [
                    "web",
                    "app",
                    "mobile",
                    "ai",
                    "ml",
                    "blockchain",
                    "api",
                    "dashboard",
                    "automation",
                    "analytics",
                    "chat",
                    "game",
                    "tool",
                    "platform",
                    "system",
                ]
                keywords = [t for t in tech_terms if t in content_text.lower()]
                if keywords:
                    full_text = (
                        f"A {' & '.join(keywords[:3])} solution that addresses the problems discussed in the chat. "
                        "The project leverages modern technologies to create an innovative hackathon submission."
                    )
                else:
                    full_text = (
                        "An innovative solution derived from the conversation topics and user requirements discussed."
                    )
                yield f"data: {json.dumps({'type': 'token', 'token': full_text})}\n\n"
            meta = {"generated_from": "sse_llm_first_fallback", "llm_used": bool(final_parts), "message_count": len(msgs)}
            try:
                save_project_artifact(session_id, "project_idea", full_text, meta)
            except Exception:
                pass
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        return StreamingResponse(token_generator(), media_type="text/event-stream")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/chat-sessions/{session_id}/create-tech-stack")
def create_tech_stack_route(session_id: str, stream: Optional[bool] = Query(False)):
    try:
        if not stream:
            result = create_tech_stack(session_id)
            return result

        msgs = get_chat_messages(session_id, limit=50)
        if not msgs:
            return JSONResponse(status_code=400, content={"error": "No chat history found for this session"})

        def _get_field(m, k):
            try:
                return m[k]
            except Exception:
                return m.get(k)

        snippets: List[str] = []
        for m in msgs[-20:]:
            role = _get_field(m, "role") or "user"
            content = (_get_field(m, "content") or "")
            content = content[:217] + "..." if len(content) > 220 else content
            if content:
                snippets.append(f"- {role}: {content}")
        user_prompt = build_tech_stack_user_prompt(snippets)

        seed_messages: List[Dict[str, Any]] = [{"role": "system", "content": TECH_STACK_SYSTEM_PROMPT}]
        for m in msgs[-20:]:
            try:
                role = _get_field(m, "role") or "user"
                content_full = (_get_field(m, "content") or "")
                if content_full:
                    seed_messages.append({"role": role, "content": content_full})
            except Exception:
                continue
        seed_messages.append({"role": "user", "content": user_prompt})

        async def token_generator():
            final_parts: List[str] = []
            try:
                async for chunk in ask_llm_stream(
                    TECH_STACK_SYSTEM_PROMPT,
                    user_prompt,
                    temperature=0.2,
                    max_tokens=512,
                    seed_messages=seed_messages,
                ):
                    final_parts.append(chunk)
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
            except Exception:
                pass
            full_text = ("".join(final_parts)).strip()
            if not full_text:
                content_text = " ".join([(_get_field(m, "content") or "").lower() for m in msgs])
                tech_mapping = {
                    "frontend": {
                        "react": ["react", "jsx", "create-react-app"],
                        "vue": ["vue", "vuejs"],
                        "angular": ["angular"],
                        "svelte": ["svelte"],
                        "html/css/js": ["html", "css", "javascript", "js"],
                    },
                    "backend": {
                        "fastapi": ["fastapi", "uvicorn"],
                        "express": ["express", "nodejs", "node.js"],
                        "django": ["django"],
                        "flask": ["flask"],
                        "python": ["python"],
                        "node.js": ["node", "nodejs"],
                    },
                    "database": {
                        "sqlite": ["sqlite"],
                        "postgresql": ["postgres", "postgresql"],
                        "mongodb": ["mongo", "mongodb"],
                        "mysql": ["mysql"],
                    },
                    "other": {
                        "ollama": ["ollama", "llm"],
                        "ai/ml": ["ai", "machine learning", "ml", "tensorflow", "pytorch"],
                        "blockchain": ["blockchain", "web3", "ethereum"],
                        "cloud": ["aws", "azure", "gcp", "cloud"],
                    },
                }
                detected = {"frontend": [], "backend": [], "database": [], "other": []}
                for cat, techs in tech_mapping.items():
                    for name, kws in techs.items():
                        if any(k in content_text for k in kws):
                            detected[cat].append(name)
                if not any(detected.values()):
                    detected = {
                        "frontend": ["React", "Tailwind CSS"],
                        "backend": ["FastAPI", "Python"],
                        "database": ["SQLite"],
                        "other": ["RESTful API"],
                    }
                else:
                    for cat in detected:
                        detected[cat] = list(set(detected[cat]))
                parts: List[str] = []
                if detected["frontend"]:
                    parts.append(f"Frontend: {', '.join(detected['frontend'])}")
                if detected["backend"]:
                    parts.append(f"Backend: {', '.join(detected['backend'])}")
                if detected["database"]:
                    parts.append(f"Database: {', '.join(detected['database'])}")
                if detected["other"]:
                    parts.append(f"Additional: {', '.join(detected['other'])}")
                full_text = " | ".join(parts)
                yield f"data: {json.dumps({'type': 'token', 'token': full_text})}\n\n"
            meta = {"generated_from": "sse_llm_first_fallback", "llm_used": bool(final_parts), "message_count": len(msgs)}
            try:
                save_project_artifact(session_id, "tech_stack", full_text, meta)
            except Exception:
                pass
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        return StreamingResponse(token_generator(), media_type="text/event-stream")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/chat-sessions/{session_id}/summarize-chat-history")
def summarize_chat_history_route(session_id: str, stream: Optional[bool] = Query(False)):
    try:
        if not stream:
            result = summarize_chat_history(session_id)
            return result

        msgs = get_chat_messages(session_id)
        if not msgs:
            return JSONResponse(status_code=400, content={"error": "No chat history found for this session"})

        idea_art = get_project_artifact(session_id, "project_idea")
        stack_art = get_project_artifact(session_id, "tech_stack")

        def _get_field(m, k):
            try:
                return m[k]
            except Exception:
                return m.get(k)

        snippets: List[str] = []
        for m in msgs[-40:]:
            role = _get_field(m, "role") or "user"
            content = (_get_field(m, "content") or "")
            content = content[:217] + "..." if len(content) > 220 else content
            if content:
                snippets.append(f"- {role}: {content}")

        user_prompt = build_submission_summary_user_prompt(
            snippets,
            idea_art["content"] if idea_art else None,
            stack_art["content"] if stack_art else None,
        )

        seed_messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SUBMISSION_SUMMARY_SYSTEM_PROMPT}
        ]
        for m in msgs[-40:]:
            try:
                role = _get_field(m, "role") or "user"
                content_full = (_get_field(m, "content") or "")
                if content_full:
                    seed_messages.append({"role": role, "content": content_full})
            except Exception:
                continue
        seed_messages.append(
            {
                "role": "user",
                "content": build_submission_summary_user_prompt(
                    snippets,
                    idea_art["content"] if idea_art else None,
                    stack_art["content"] if stack_art else None,
                ),
            }
        )

        async def token_generator():
            final_parts: List[str] = []
            try:
                async for chunk in ask_llm_stream(
                    SUBMISSION_SUMMARY_SYSTEM_PROMPT,
                    user_prompt,
                    temperature=0.1,
                    max_tokens=600,
                    seed_messages=seed_messages,
                ):
                    final_parts.append(chunk)
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
            except Exception:
                pass
            full_text = ("".join(final_parts)).strip()
            if not full_text:
                try:
                    result = summarize_chat_history(session_id)
                    full_text = result.get("submission_summary", "")
                except Exception:
                    full_text = ""
                if full_text:
                    yield f"data: {json.dumps({'type': 'token', 'token': full_text})}\n\n"
            meta = {"generated_from": "sse_llm_first_fallback", "llm_used": bool(final_parts), "message_count": len(msgs)}
            try:
                save_project_artifact(session_id, "submission_summary", full_text, meta)
            except Exception:
                pass
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        return StreamingResponse(token_generator(), media_type="text/event-stream")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


