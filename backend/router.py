from fastapi import APIRouter, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict, Any, Optional
from llm import generate_stream, check_ollama_status, get_current_model, set_model
from rag import RuleRAG
from tools import (
    get_tool_schemas, call_tool, list_todos, add_todo, clear_todos,
    update_todo, delete_todo,
    derive_project_idea, create_tech_stack, summarize_chat_history
)
from models import (
    create_chat_session,
    get_chat_session,
    add_chat_message,
    get_chat_messages,
    update_chat_session_title,
    get_recent_chat_sessions,
    delete_chat_session,
    get_project_artifact,
    get_all_project_artifacts,
    ChatSession,
    ChatMessage,
    ProjectArtifact,
)
import uuid
from pathlib import Path
import json, io, time
import pdfminer.high_level
import docx
import pytesseract
from PIL import Image
import requests
from models.db import add_rule_context, get_rules_rows

router = APIRouter()
# Initialise RAG with default rule file (user can replace via API call later)
rag = RuleRAG(Path(__file__).parent / "docs" / "rules.txt")

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5MB limit per file
ALLOWED_FILE_EXT = {'.txt', '.md', '.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg'}

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

    # Save user message to database
    user_content = "\n".join(context_parts + [user_input])
    add_chat_message(session_id, "user", user_content, metadata)

    # Retrieve relevant rule chunks
    rule_hits = rag.retrieve(user_input, k=5)
    rule_text = "\n".join([f"Rule Chunk {i+1}:\n{chunk}" for i, (chunk, _) in enumerate(rule_hits)])

    # Build system prompt for the LLM (explicit tool usage guidance added)
    system_prompt = f"""You are **HackathonHero**, an expert assistant that helps participants create, refine, and submit hackathon projects completely offline.

    You have access to function-calling tools. Use them when they clearly help the user:
    - Use add_todo to add actionable tasks to the project To-Do list.
    - Use list_todos to recall current tasks and trust its output. Present the items without speculation or self-correction.
    - Use clear_todos to reset the task list when asked.
    - Use list_directory to explore local files when requested.

    Rules context (authoritative):
    {rule_text}

    Guidance:
    - Prefer using tools to perform actions instead of describing actions.
    - When planning work, convert steps into separate add_todo calls.
    - Keep the tone clear, concise, and encouraging. Do not mention any external APIs or internet resources.
    - Cite rule chunk numbers in brackets if you refer to a specific rule."""

    # Load previous chat history for context
    chat_history = get_chat_messages(session_id, limit=20)  # Last 20 messages

    # Build messages for tool-enabled streaming
    tools = get_tool_schemas()
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt + "\n\n" + rule_text},
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

        # Stream the assistant response, surface tool_calls events to UI as info
        last_heartbeat = time.time()
        async for data in generate_stream(
                user_content,
                system=system_prompt + "\n\n" + rule_text,
                tools=tools,
                execute_tool=lambda fn, args: call_tool(fn, args),
            ):
                if isinstance(data, dict):
                    if data.get("type") == "thinking":
                        # Throttle thinking tokens minimally to avoid flooding
                        yield f"data: {json.dumps({'type': 'thinking', 'content': data.get('content')})}\n\n"
                    elif data.get("type") == "tool_calls":
                        yield f"data: {json.dumps({'type': 'tool_calls', 'tool_calls': data.get('tool_calls', [])})}\n\n"
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

        # Save assistant response to database
        if assistant_response_parts:
            assistant_content = "".join(assistant_response_parts)
            add_chat_message(session_id, "assistant", assistant_content)

        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")





@router.get("/todos")
def get_todos(detailed: bool = Query(False)):
    return {"todos": list_todos(detailed=detailed)}


@router.post("/todos")
def post_todo(item: str = Form(...)):
    res = add_todo(item)
    return {"ok": res.get("ok", True), "todos": list_todos()}


@router.delete("/todos")
def delete_todos():
    res = clear_todos()
    return {"ok": res.get("ok", True)}


@router.put("/todos/{todo_id}")
def update_todo_route(todo_id: int,
                      item: Optional[str] = Form(None),
                      status: Optional[str] = Form(None),
                      priority: Optional[int] = Form(None),
                      sort_order: Optional[int] = Form(None)):
    res = update_todo(todo_id, item=item, status=status, priority=priority, sort_order=sort_order)
    if not res.get("ok"):
        return JSONResponse(status_code=404, content={"error": "Todo not found"})
    return {"ok": True}


@router.delete("/todos/{todo_id}")
def delete_todo_route(todo_id: int):
    res = delete_todo(todo_id)
    if not res.get("ok"):
        return JSONResponse(status_code=404, content={"error": "Todo not found"})
    return {"ok": True}


@router.post("/rules")
def upload_rules(file: UploadFile = File(...)):
    """Replace the current rules file & store in DB as a new active context row."""
    content_bytes = file.file.read()
    content = content_bytes.decode('utf-8', errors='ignore')
    add_rule_context('file', content, filename=file.filename, active=True)
    rag.rebuild()
    return {"ok": True, "chunks": len(rag.chunks)}


@router.post("/context/add-text")
def add_text_context(text: str = Form(...)):
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
            add_rule_context('url', block, filename=cleaned)
        except Exception as e:
            # Store URL with failure note to keep traceability
            block = f"[URL_FETCH_FAILED:{cleaned}]\nError: {e}"
            add_rule_context('url', block, filename=cleaned)
    else:
        add_rule_context('text', cleaned)
    rag.rebuild()
    return {"ok": True, "chunks": len(rag.chunks)}


@router.post("/context/add-url-text")
def add_url_text_context(url: str = Form(...), content: str = Form(...)):
    """Add content fetched from a URL (frontend is responsible for fetching)."""
    block = f"[URL:{url}]\n{content.strip()}"
    add_rule_context('url', block, filename=url)
    rag.rebuild()
    return {"ok": True, "chunks": len(rag.chunks)}


@router.get("/context/list")
def list_context():
    return {"items": get_rules_rows(), "chunks": len(rag.chunks)}


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
    return {
        "session": ChatSession.from_row(session).model_dump(),
        "messages": [ChatMessage.from_row(row).model_dump() for row in paged],
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
def derive_project_idea_route(session_id: str):
    """Derive project idea from chat history."""
    try:
        result = derive_project_idea(session_id)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/chat-sessions/{session_id}/create-tech-stack")
def create_tech_stack_route(session_id: str):
    """Create tech stack from chat history."""
    try:
        result = create_tech_stack(session_id)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/chat-sessions/{session_id}/summarize-chat-history")
def summarize_chat_history_route(session_id: str):
    """Generate submission notes from chat history."""
    try:
        result = summarize_chat_history(session_id)
        return result
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