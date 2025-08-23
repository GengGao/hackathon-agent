from typing import List, Dict, Any, Optional
import json
import threading
import time
import uuid

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from .common import get_generate_stream
from prompts import build_hackathon_system_prompt
from tools import get_tool_schemas, call_tool, generate_chat_title
from models.db import (
    create_chat_session,
    get_chat_session,
    add_chat_message,
    get_chat_messages,
)
from utils.text import strip_context_blocks
from .common import rag, extract_text_from_file, build_url_block


router = APIRouter()


@router.post("/chat-stream")
async def chat_stream(
    user_input: str = Form(...),
    files: List[UploadFile] = File(default=None),
    url_text: str = Form(None),
    session_id: str = Form(None),
):
    if not session_id:
        session_id = str(uuid.uuid4())

    create_chat_session(session_id)

    try:
        rag.set_session(session_id)
    except Exception as e:
        print(f"Warning: Failed to set RAG session {session_id}: {e}")

    try:
        rag.ensure_index()
    except Exception as e:
        print(f"Warning: Failed to ensure RAG index for session {session_id}: {e}")

    context_parts: List[str] = []
    metadata: Dict[str, Any] = {}

    collected_files: List[UploadFile] = []
    if files:
        collected_files.extend(files)
    if collected_files:
        file_meta = []
        for f in collected_files[:10]:
            extracted = extract_text_from_file(f)
            context_parts.append(f"[FILE:{f.filename}]\n{extracted}\n[/FILE]")
            # Get file size - try tell() method first, fallback to size attribute or 0
            file_size = 0
            try:
                if hasattr(f.file, 'tell'):
                    current_pos = f.file.tell()
                    f.file.seek(0, 2)  # Seek to end
                    file_size = f.file.tell()
                    f.file.seek(current_pos)  # Restore position
                elif hasattr(f, 'size'):
                    file_size = f.size
            except Exception:
                file_size = 0
            file_meta.append({"filename": f.filename, "size_bytes": file_size})
        metadata["files"] = file_meta

    if url_text:
        if url_text.startswith(("http://", "https://")):
            block = build_url_block(url_text)
            metadata["url"] = url_text
            context_parts.append(block)
        else:
            metadata["url_text"] = url_text[:100] + "..." if len(url_text) > 100 else url_text
            context_parts.append(f"[URL_TEXT]\n{url_text}\n[/URL_TEXT]")

    user_content = "\n".join(context_parts + [user_input])
    saved_user_content = strip_context_blocks(user_content)
    add_chat_message(session_id, "user", saved_user_content, metadata)
    try:
        session_row = get_chat_session(session_id)
        has_title = bool(
            session_row and (session_row["title"] or (hasattr(session_row, "get") and session_row.get("title")))
        )
        if not has_title:
            threading.Thread(target=lambda: generate_chat_title(session_id), daemon=True).start()
    except Exception as e:
        print(f"Warning: Failed to start title generation thread for session {session_id}: {e}")

    rule_hits = rag.retrieve(user_input, k=5)
    rule_text = "\n".join([f"Rule Chunk {i+1}:\n{chunk}" for i, (chunk, _) in enumerate(rule_hits)])
    system_prompt = build_hackathon_system_prompt(rule_text)

    chat_history = get_chat_messages(session_id, limit=20)
    tools = get_tool_schemas()
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for msg_row in chat_history[:-1]:
        messages.append({"role": msg_row["role"], "content": msg_row["content"]})
    messages.append({"role": "user", "content": user_content})

    async def token_generator():
        yield f"data: {json.dumps({'type': 'session_info', 'session_id': session_id})}\n\n"
        yield f"data: {json.dumps({'type': 'rule_chunks', 'rule_chunks': [c for c,_ in rule_hits]})}\n\n"

        assistant_response_parts: List[str] = []
        assistant_thinking_parts: List[str] = []
        tool_calls_logged: List[Dict[str, Any]] = []

        last_heartbeat = time.time()
        generate_stream = get_generate_stream()
        async for data in generate_stream(
            user_content,
            system=system_prompt,
            tools=tools,
            execute_tool=lambda fn, args: call_tool(
                fn, {**(args or {}), **({"session_id": session_id} if session_id else {})}
            ),
            seed_messages=messages,
        ):
            if isinstance(data, dict):
                if data.get("type") == "thinking":
                    yield f"data: {json.dumps({'type': 'thinking', 'content': data.get('content')})}\n\n"
                    content_piece = data.get("content")
                    if content_piece:
                        assistant_thinking_parts.append(content_piece)
                elif data.get("type") == "tool_calls":
                    calls = data.get("tool_calls", []) or []
                    yield f"data: {json.dumps({'type': 'tool_calls', 'tool_calls': calls})}\n\n"
                    for tc in calls:
                        try:
                            has_id = isinstance(tc, dict) and tc.get("id") is not None
                            if has_id:
                                if any(existing.get("id") == tc.get("id") for existing in tool_calls_logged):
                                    continue
                            else:
                                if any(
                                    (
                                        existing.get("name") == tc.get("name")
                                        and existing.get("arguments") == tc.get("arguments")
                                    )
                                    for existing in tool_calls_logged
                                ):
                                    continue
                            tool_calls_logged.append(tc)
                        except Exception as e:
                            print(f"Warning: Failed to process tool call {tc}: {e}")
                elif data.get("type") == "content" and data.get("content"):
                    content = data["content"]
                    assistant_response_parts.append(content)
                    yield f"data: {json.dumps({'type': 'token', 'token': content})}\n\n"
            elif isinstance(data, str) and data:
                assistant_response_parts.append(data)
                yield f"data: {json.dumps({'type': 'token', 'token': data})}\n\n"

            if time.time() - last_heartbeat > 15:
                yield f": ping\n\n"
                last_heartbeat = time.time()

        if assistant_response_parts:
            assistant_content = strip_context_blocks("".join(assistant_response_parts))
            assistant_metadata: Dict[str, Any] = {}
            full_thinking = "".join(assistant_thinking_parts).strip()
            if full_thinking:
                assistant_metadata["thinking"] = full_thinking
            if tool_calls_logged:
                assistant_metadata["tool_calls"] = tool_calls_logged
            add_chat_message(session_id, "assistant", assistant_content, assistant_metadata if assistant_metadata else None)
            try:
                session_row2 = get_chat_session(session_id)
                has_title2 = bool(
                    session_row2 and (session_row2["title"] or (hasattr(session_row2, "get") and session_row2.get("title")))
                )
                if not has_title2:
                    threading.Thread(target=lambda: generate_chat_title(session_id), daemon=True).start()
            except Exception as e:
                print(f"Warning: Failed to start second title generation thread for session {session_id}: {e}")

        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")


