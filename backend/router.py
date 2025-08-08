from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict, Any
from llm import generate_stream, check_ollama_status, get_current_model, set_model
from rag import RuleRAG
from tools import get_tool_schemas, call_tool, list_todos, add_todo, clear_todos
from models import (
    create_chat_session,
    get_chat_session,
    add_chat_message,
    get_chat_messages,
    update_chat_session_title,
    get_recent_chat_sessions,
    delete_chat_session,
    ChatSession,
    ChatMessage,
)
import uuid
from pathlib import Path
import json, io
import pdfminer.high_level
import docx
import pytesseract
from PIL import Image
import requests

router = APIRouter()
# Initialise RAG with default rule file (user can replace via API call later)
rag = RuleRAG(Path(__file__).parent / "docs" / "rules.txt")

def extract_text_from_file(file: UploadFile) -> str:
    filename = file.filename.lower()
    content = file.file.read()
    if filename.endswith('.pdf'):
        return pdfminer.high_level.extract_text(io.BytesIO(content))
    elif filename.endswith('.docx') or filename.endswith('.doc'):
        doc = docx.Document(io.BytesIO(content))
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        # Assume plain text
        return content.decode('utf-8', errors='ignore')


@router.post("/chat-stream")
async def chat_stream(
    user_input: str = Form(...),
    file: UploadFile = File(None),
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

    if file:
        extracted = extract_text_from_file(file)
        context_parts.append(f"[FILE_CONTENT]\n{extracted}\n[/FILE_CONTENT]")
        metadata["file"] = {"filename": file.filename, "size": len(extracted)}

    if url_text:
        #url_text can be a string of text or a URL
        if url_text.startswith('http'):
            # Download the URL content
            response = requests.get(url_text)
            url_text = response.text
            metadata["url"] = url_text[:100] + "..." if len(url_text) > 100 else url_text
        else:
            # Assume it's plain text
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
        # Send session_id and rule chunks first
        yield f"data: {json.dumps({'type': 'session_info', 'session_id': session_id})}\n\n"
        yield f"data: {json.dumps({'type': 'rule_chunks', 'rule_chunks': [c for c,_ in rule_hits]})}\n\n"

        # Collect assistant response for saving to database
        assistant_response_parts = []

        # Stream the assistant response, surface tool_calls events to UI as info
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

        # Save assistant response to database
        if assistant_response_parts:
            assistant_content = "".join(assistant_response_parts)
            add_chat_message(session_id, "assistant", assistant_content)

        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")





@router.get("/todos")
def get_todos():
    return {"todos": list_todos()}


@router.post("/todos")
def post_todo(item: str = Form(...)):
    res = add_todo(item)
    return {"ok": res.get("ok", True), "todos": list_todos()}


@router.delete("/todos")
def delete_todos():
    res = clear_todos()
    return {"ok": res.get("ok", True)}


@router.post("/rules")
def upload_rules(file: UploadFile = File(...)):
    """
    Replace the current rules file used by RAG.
    """
    target = Path(__file__).parent / "docs" / "rules.txt"
    content = file.file.read()
    target.write_bytes(content)
    # Reload RAG index
    global rag
    rag = RuleRAG(target)
    return {"ok": True}


@router.get("/chat-sessions")
def get_chat_sessions():
    """Get recent chat sessions."""
    sessions = get_recent_chat_sessions(limit=20)
    return {
        "sessions": [ChatSession.from_row(row).model_dump() for row in sessions]
    }


@router.get("/chat-sessions/{session_id}")
def get_chat_session_detail(session_id: str):
    """Get a specific chat session with its messages."""
    session = get_chat_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    messages = get_chat_messages(session_id)
    return {
        "session": ChatSession.from_row(session).model_dump(),
        "messages": [ChatMessage.from_row(row).model_dump() for row in messages]
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