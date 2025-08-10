from fastapi import APIRouter, UploadFile, File, Form, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict, Any, Optional
from llm import generate_stream, check_ollama_status, get_current_model, set_model
from prompts import build_hackathon_system_prompt
from rag import RuleRAG
from tools import (
    get_tool_schemas, call_tool, list_todos, add_todo, clear_todos,
    update_todo, delete_todo,
    derive_project_idea, create_tech_stack, summarize_chat_history,
    ask_llm_stream,
)
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
from models.schemas import (
    ChatSession,
    ChatMessage,
    ProjectArtifact,
)
import uuid
from pathlib import Path
import threading
import json, io, time
import pdfminer.high_level
import docx
import pytesseract
from PIL import Image
import requests
from models.db import add_rule_context, get_rules_rows
import re
from prompts import (
    PROJECT_IDEA_SYSTEM_PROMPT,
    TECH_STACK_SYSTEM_PROMPT,
    SUBMISSION_SUMMARY_SYSTEM_PROMPT,
)
from models.db import save_project_artifact

router = APIRouter()
# Initialise RAG with default rule file (user can replace via API call later)
rag = RuleRAG(Path(__file__).parent / "docs" / "rules.txt", lazy=False)

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5MB limit per file
ALLOWED_FILE_EXT = {'.txt', '.md', '.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg'}


def strip_context_blocks(text: str) -> str:
    if not text:
        return text
    # Remove [FILE:...]...[/FILE] blocks
    cleaned = re.sub(r"\[FILE:[^\]]+\][\s\S]*?\[/FILE\]", "", text, flags=re.IGNORECASE)
    # Remove [URL_TEXT]...[/URL_TEXT] blocks
    cleaned = re.sub(r"\[URL_TEXT\][\s\S]*?\[/URL_TEXT\]", "", cleaned, flags=re.IGNORECASE)
    # Collapse excessive blank lines and trim
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned

def extract_text_from_file(file: UploadFile) -> str:
    filename = file.filename
    lower = filename.lower()
    ext = ''.join(['.', filename.split('.')[-1].lower()]) if '.' in filename else ''
    raw = file.file.read()
    if len(raw) > MAX_FILE_BYTES:
        return f"[File '{filename}' skipped: exceeds size limit]"
    if ext and ext not in ALLOWED_FILE_EXT:
        return f"[File '{filename}' skipped: extension not allowed]"
    try:
        if lower.endswith('.pdf'):
            return pdfminer.high_level.extract_text(io.BytesIO(raw))
        elif lower.endswith('.docx') or lower.endswith('.doc'):
            d = docx.Document(io.BytesIO(raw))
            return "\n".join(p.text for p in d.paragraphs)
        elif lower.endswith(('.png', '.jpg', '.jpeg')):
            try:
                img = Image.open(io.BytesIO(raw))
                text = pytesseract.image_to_string(img)
                return text or f"[No text detected in image {filename}]"
            except Exception as e:
                return f"[Image OCR failed for {filename}: {e}]"
        else:
            return raw.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"[Failed to process {filename}: {e}]"


@router.post("/chat-stream")
async def chat_stream(
    user_input: str = Form(...),
    files: List[UploadFile] = File(default=None),  # multi-file support
    url_text: str = Form(None),
    session_id: str = Form(None),
):
    """
    Streaming version of the chat endpoint that returns Server-Sent Events.
    Includes chat history as context when session_id is provided.
    """
    # Generate or use provided session_id
    if not session_id:
        session_id = str(uuid.uuid4())

    # Create/ensure chat session exists
    create_chat_session(session_id)

    # Scope RAG to this session
    try:
        rag.set_session(session_id)
    except Exception:
        pass

    # Ensure session-scoped index exists (synchronous build if needed)
    try:
        rag.ensure_index()
    except Exception:
        pass

    # Gather context
    context_parts = []
    metadata = {}

    # Collect files list
    collected_files: List[UploadFile] = []
    if files:
        collected_files.extend(files)
    if collected_files:
        file_meta = []
        for f in collected_files[:10]:  # cap number processed per request
            extracted = extract_text_from_file(f)
            context_parts.append(f"[FILE:{f.filename}]\n{extracted}\n[/FILE]")
            file_meta.append({"filename": f.filename, "size_bytes": getattr(f.file, 'tell', lambda: None)()})
        metadata["files"] = file_meta

    if url_text:
        # url_text can be plain pasted text or a URL
        if url_text.startswith(('http://', 'https://')):
            try:
                resp = requests.get(url_text, timeout=5, stream=True)
                ctype = resp.headers.get('Content-Type', '')
                # Only allow text-like
                if 'text' not in ctype.lower():
                    snippet = f"[Blocked non-text content-type {ctype}]"
                else:
                    # Limit to first 100KB
                    content_bytes = resp.content[:100_000]
                    if len(resp.content) > 100_000:
                        snippet = content_bytes.decode('utf-8', errors='ignore') + "\n[Truncated]"
                    else:
                        snippet = content_bytes.decode('utf-8', errors='ignore')
                metadata["url"] = url_text
                context_parts.append(f"[URL:{url_text}]\n{snippet}\n[/URL]")
            except Exception as e:
                err = f"[Failed to fetch URL: {e}]"
                context_parts.append(err)
                metadata["url_error"] = str(e)
        else:
            metadata["url_text"] = url_text[:100] + "..." if len(url_text) > 100 else url_text
            context_parts.append(f"[URL_TEXT]\n{url_text}\n[/URL_TEXT]")

    # Save user message to database (strip context tags for stored/displayed content)
    user_content = "\n".join(context_parts + [user_input])
    saved_user_content = strip_context_blocks(user_content)
    add_chat_message(session_id, "user", saved_user_content, metadata)

    # Retrieve relevant rule chunks (scoped to session)
    rule_hits = rag.retrieve(user_input, k=5)
    rule_text = "\n".join([f"Rule Chunk {i+1}:\n{chunk}" for i, (chunk, _) in enumerate(rule_hits)])

    # Build system prompt for the LLM (explicit tool usage guidance added)
    system_prompt = build_hackathon_system_prompt(rule_text)

    # Load previous chat history for context
    chat_history = get_chat_messages(session_id, limit=20)  # Last 20 messages

    # Build messages for tool-enabled streaming
    tools = get_tool_schemas()
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
    ]

    # Add previous chat history (excluding the current message we just added)
    for msg_row in chat_history[:-1]:  # Exclude the last message (current user input)
        messages.append({
            "role": msg_row["role"],
            "content": msg_row["content"]
        })

    # Add current user message
    messages.append({
        "role": "user",
        "content": user_content
    })

    async def token_generator():
        # Send session info first
        yield f"data: {json.dumps({'type': 'session_info', 'session_id': session_id})}\n\n"
        # Send rule chunks hits
        yield f"data: {json.dumps({'type': 'rule_chunks', 'rule_chunks': [c for c,_ in rule_hits]})}\n\n"

        # Collect assistant response for saving to database
        assistant_response_parts = []
        assistant_thinking_parts: List[str] = []
        tool_calls_logged: List[Dict[str, Any]] = []

        # Stream the assistant response, surface tool_calls events to UI as info
        last_heartbeat = time.time()
        async for data in generate_stream(
                user_content,
                system=system_prompt,
                tools=tools,
                execute_tool=lambda fn, args: call_tool(
                    fn,
                    {**(args or {}), **({"session_id": session_id} if session_id else {})}
                ),
            ):
                if isinstance(data, dict):
                    if data.get("type") == "thinking":
                        # Throttle thinking tokens minimally to avoid flooding
                        yield f"data: {json.dumps({'type': 'thinking', 'content': data.get('content')})}\n\n"
                        # Collect full thinking text for metadata persistence
                        content_piece = data.get("content")
                        if content_piece:
                            assistant_thinking_parts.append(content_piece)
                    elif data.get("type") == "tool_calls":
                        calls = data.get("tool_calls", []) or []
                        yield f"data: {json.dumps({'type': 'tool_calls', 'tool_calls': calls})}\n\n"
                        # Accumulate unique tool calls for metadata persistence
                        for tc in calls:
                            try:
                                # Deduplicate by id if present; otherwise by (name, arguments)
                                has_id = isinstance(tc, dict) and tc.get("id") is not None
                                if has_id:
                                    if any(existing.get("id") == tc.get("id") for existing in tool_calls_logged):
                                        continue
                                else:
                                    if any((existing.get("name") == tc.get("name") and existing.get("arguments") == tc.get("arguments")) for existing in tool_calls_logged):
                                        continue
                                tool_calls_logged.append(tc)
                            except Exception:
                                # Best-effort logging; ignore malformed entries
                                pass
                    elif data.get("type") == "content" and data.get("content"):
                        content = data['content']
                        assistant_response_parts.append(content)
                        yield f"data: {json.dumps({'type': 'token', 'token': content})}\n\n"
                elif isinstance(data, str) and data:
                    assistant_response_parts.append(data)
                    yield f"data: {json.dumps({'type': 'token', 'token': data})}\n\n"

                # Heartbeat every 15s to keep SSE alive
                if time.time() - last_heartbeat > 15:
                    yield f": ping\n\n"
                    last_heartbeat = time.time()

        # Save assistant response to database (ensure no context tags leak)
        if assistant_response_parts:
            assistant_content = strip_context_blocks("".join(assistant_response_parts))
            # Persist thinking and tool_calls inside metadata for later rendering
            metadata: Dict[str, Any] = {}
            full_thinking = "".join(assistant_thinking_parts).strip()
            if full_thinking:
                metadata["thinking"] = full_thinking
            if tool_calls_logged:
                metadata["tool_calls"] = tool_calls_logged
            add_chat_message(session_id, "assistant", assistant_content, metadata if metadata else None)

        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")





@router.get("/todos")
def get_todos(detailed: bool = Query(False), session_id: Optional[str] = Query(None)):
    return {"todos": list_todos(detailed=detailed, session_id=session_id)}


@router.post("/todos")
def post_todo(item: str = Form(...), session_id: Optional[str] = Form(None)):
    res = add_todo(item, session_id=session_id)
    return {"ok": res.get("ok", True), "todos": list_todos(session_id=session_id)}


@router.delete("/todos")
def delete_todos(session_id: Optional[str] = Query(None)):
    if not session_id:
        return JSONResponse(status_code=400, content={"error": "session_id is required"})
    res = clear_todos(session_id=session_id)
    return {"ok": res.get("ok", True), "deleted": res.get("deleted", 0)}


@router.put("/todos/{todo_id}")
async def update_todo_route(todo_id: int,
                            request: Request,
                            item: Optional[str] = Form(None),
                            status: Optional[str] = Form(None),
                            sort_order: Optional[int] = Form(None),
                            session_id: Optional[str] = Form(None)):
    # Accept either form-encoded fields or JSON body
    fields: Dict[str, Any] = {}
    if item is not None:
        fields["item"] = item
    if status is not None:
        fields["status"] = status
    if sort_order is not None:
        fields["sort_order"] = sort_order

    if session_id is not None:
        fields["session_id"] = session_id

    if not fields:
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                payload = await request.json()
                if isinstance(payload, dict):
                    for k in ("item", "status", "sort_order", "session_id"):
                        if k in payload and payload[k] is not None:
                            fields[k] = payload[k]
        except Exception:
            pass

    if not fields:
        return JSONResponse(status_code=400, content={"error": "No fields provided"})

    res = update_todo(todo_id, **fields)
    if not res.get("ok"):
        # Differentiate not-found vs. no-op
        return JSONResponse(status_code=404, content={"error": "Todo not found"})
    return {"ok": True}


@router.delete("/todos/{todo_id}")
def delete_todo_route(todo_id: int, session_id: Optional[str] = Query(None)):
    res = delete_todo(todo_id, session_id=session_id)
    if not res.get("ok"):
        return JSONResponse(status_code=404, content={"error": "Todo not found"})
    return {"ok": True}


@router.post("/context/rules")
def upload_rules(file: UploadFile = File(...), session_id: Optional[str] = Form(None)):
    """Replace the current rules file & store in DB as a new active context row."""
    content_bytes = file.file.read()
    content = content_bytes.decode('utf-8', errors='ignore')
    if session_id:
        create_chat_session(session_id)
    add_rule_context('file', content, filename=file.filename, active=True, session_id=session_id)
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
    # If it's a URL, fetch and store fetched snippet instead of raw URL only
    if cleaned.startswith(('http://', 'https://')):
        try:
            resp = requests.get(cleaned, timeout=8, stream=True)
            ctype = resp.headers.get('Content-Type', '')
            if 'text' not in ctype.lower():
                snippet = f"[Blocked non-text content-type {ctype}]"
            else:
                content_bytes = resp.content[:100_000]
                if len(resp.content) > 100_000:
                    snippet = content_bytes.decode('utf-8', errors='ignore') + "\n[Truncated]"
                else:
                    snippet = content_bytes.decode('utf-8', errors='ignore')
            block = f"[URL:{cleaned}]\n{snippet}"
            if session_id:
                create_chat_session(session_id)
            add_rule_context('url', block, filename=cleaned, session_id=session_id)
        except Exception as e:
            # Store URL with failure note to keep traceability
            block = f"[URL_FETCH_FAILED:{cleaned}]\nError: {e}"
            if session_id:
                create_chat_session(session_id)
            add_rule_context('url', block, filename=cleaned, session_id=session_id)
    else:
        if session_id:
            create_chat_session(session_id)
        add_rule_context('text', cleaned, session_id=session_id)
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
        # If index not ready and not currently building, trigger background build
        if not status.get("ready") and not status.get("building"):
            try:
                threading.Thread(target=rag.rebuild, kwargs={"force": True}, daemon=True).start()
                # Reflect build kickoff without re-reading potentially cross-session state
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


@router.get("/chat-sessions")
def get_chat_sessions(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    """Get recent chat sessions with simple pagination."""
    sessions = get_recent_chat_sessions(limit=limit + offset)
    sliced = sessions[offset:offset+limit]
    return {
        "sessions": [ChatSession.from_row(row).model_dump() for row in sliced],
        "total_fetched": len(sessions),
        "offset": offset,
        "limit": limit
    }


@router.get("/chat-sessions/{session_id}")
def get_chat_session_detail(session_id: str, limit: Optional[int] = Query(None, ge=1, le=1000), offset: int = Query(0, ge=0)):
    """Get a specific chat session with its messages (paged)."""
    session = get_chat_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    all_messages = get_chat_messages(session_id)
    if limit is None:
        paged = all_messages
    else:
        paged = all_messages[offset: offset + limit]
    # Sanitize content on return to avoid leaking any context tags from legacy rows
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
        "limit": limit if limit is not None else len(all_messages)
    }


@router.put("/chat-sessions/{session_id}/title")
def update_session_title(session_id: str, title: str = Form(...)):
    """Update the title of a chat session."""
    session = get_chat_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    update_chat_session_title(session_id, title)
    return {"ok": True}


@router.delete("/chat-sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a chat session and all its messages."""
    session = get_chat_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    delete_chat_session(session_id)
    return {"ok": True}


@router.get("/ollama/status")
async def get_ollama_status():
    """Check if Ollama is running and return connection status."""
    try:
        status = await check_ollama_status()
        return {
            "connected": status["connected"],
            "model": status.get("model"),
            "available_models": status.get("available_models", [])
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "model": None,
            "available_models": []
        }


@router.get("/ollama/model")
def get_ollama_model():
    """Get the currently selected model."""
    return {"model": get_current_model()}


@router.post("/ollama/model")
async def set_ollama_model(model: str = Form(...)):
    """Set the model to use for generation."""
    try:
        success = await set_model(model)
        if success:
            return {"ok": True, "model": get_current_model()}
        else:
            return JSONResponse(status_code=400, content={"error": "Invalid model"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/chat-sessions/{session_id}/derive-project-idea")
def derive_project_idea_route(session_id: str, stream: Optional[bool] = Query(False)):
    """Derive project idea from chat history. Supports SSE when stream=true."""
    try:
        if not stream:
            result = derive_project_idea(session_id)
            return result

        # SSE streaming path
        msgs = get_chat_messages(session_id, limit=50)
        if not msgs:
            return JSONResponse(status_code=400, content={"error": "No chat history found for this session"})

        # Build user prompt from recent conversation
        def _get_field(m, k):
            try:
                return m[k]
            except Exception:
                return m.get(k)
        snippets = []
        for m in msgs[-20:]:
            role = _get_field(m, "role") or "user"
            content = (_get_field(m, "content") or "")
            content = content[:217] + "..." if len(content) > 220 else content
            if content:
                snippets.append(f"- {role}: {content}")
        user_prompt = "Draft a concise project idea based on these messages.\n\n" + "\n".join(snippets)

        async def token_generator():
            final_parts: List[str] = []
            try:
                async for chunk in ask_llm_stream(PROJECT_IDEA_SYSTEM_PROMPT, user_prompt, temperature=0.2, max_tokens=256):
                    final_parts.append(chunk)
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
            except Exception:
                pass
            full_text = ("".join(final_parts)).strip()
            if not full_text:
                # Fallback keyword-based idea
                content_text = " ".join([_get_field(m, "content") or "" for m in msgs])
                tech_terms = ["web", "app", "mobile", "ai", "ml", "blockchain", "api", "dashboard", "automation", "analytics", "chat", "game", "tool", "platform", "system"]
                keywords = [t for t in tech_terms if t in content_text.lower()]
                if keywords:
                    full_text = f"A {' & '.join(keywords[:3])} solution that addresses the problems discussed in the chat. The project leverages modern technologies to create an innovative hackathon submission."
                else:
                    full_text = "An innovative solution derived from the conversation topics and user requirements discussed."
                yield f"data: {json.dumps({'type': 'token', 'token': full_text})}\n\n"
            # Persist artifact
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
    """Create tech stack from chat history. Supports SSE when stream=true."""
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
        snippets = []
        for m in msgs[-20:]:
            role = _get_field(m, "role") or "user"
            content = (_get_field(m, "content") or "")
            content = content[:217] + "..." if len(content) > 220 else content
            if content:
                snippets.append(f"- {role}: {content}")
        user_prompt = "Create a recommended tech stack strictly from these messages.\n\n" + "\n".join(snippets)

        async def token_generator():
            final_parts: List[str] = []
            try:
                async for chunk in ask_llm_stream(TECH_STACK_SYSTEM_PROMPT, user_prompt, temperature=0.2, max_tokens=512):
                    final_parts.append(chunk)
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
            except Exception:
                pass
            full_text = ("".join(final_parts)).strip()
            if not full_text:
                # Fallback to deterministic mapping
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
                    detected = {"frontend": ["React", "Tailwind CSS"], "backend": ["FastAPI", "Python"], "database": ["SQLite"], "other": ["RESTful API"]}
                else:
                    for cat in detected:
                        detected[cat] = list(set(detected[cat]))
                parts = []
                if detected["frontend"]: parts.append(f"Frontend: {', '.join(detected['frontend'])}")
                if detected["backend"]: parts.append(f"Backend: {', '.join(detected['backend'])}")
                if detected["database"]: parts.append(f"Database: {', '.join(detected['database'])}")
                if detected["other"]: parts.append(f"Additional: {', '.join(detected['other'])}")
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
    """Generate submission notes from chat history. Supports SSE when stream=true."""
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
        snippets = []
        for m in msgs[-40:]:
            role = _get_field(m, "role") or "user"
            content = (_get_field(m, "content") or "")
            content = content[:217] + "..." if len(content) > 220 else content
            if content:
                snippets.append(f"- {role}: {content}")
        up_lines: List[str] = []
        if idea_art:
            up_lines.append(f"Project Idea: {idea_art['content']}")
        if stack_art:
            up_lines.append(f"Tech Stack: {stack_art['content']}")
        up_lines.append("Conversation (most recent first):")
        up_lines.extend(snippets)
        user_prompt = "\n".join(up_lines)

        async def token_generator():
            final_parts: List[str] = []
            try:
                async for chunk in ask_llm_stream(SUBMISSION_SUMMARY_SYSTEM_PROMPT, user_prompt, temperature=0.1, max_tokens=600):
                    final_parts.append(chunk)
                    yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
            except Exception:
                pass
            full_text = ("".join(final_parts)).strip()
            if not full_text:
                # Fallback: reuse deterministic builder from tools via function call
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


@router.get("/chat-sessions/{session_id}/project-artifacts")
def get_project_artifacts_route(session_id: str):
    """Get all project artifacts for a session."""
    try:
        artifacts = get_all_project_artifacts(session_id)
        return {
            "artifacts": [ProjectArtifact.from_row(row).model_dump() for row in artifacts]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/chat-sessions/{session_id}/project-artifacts/{artifact_type}")
def get_specific_project_artifact_route(session_id: str, artifact_type: str):
    """Get a specific project artifact by type."""
    try:
        artifact = get_project_artifact(session_id, artifact_type)
        if not artifact:
            return JSONResponse(status_code=404, content={"error": "Artifact not found"})

        return {
            "artifact": ProjectArtifact.from_row(artifact).model_dump()
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})