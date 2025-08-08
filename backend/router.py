from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict, Any
from llm import generate_stream
from rag import RuleRAG
from tools import get_tool_schemas, call_tool, list_todos, add_todo, clear_todos
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
):
    """
    Streaming version of the chat endpoint that returns Server-Sent Events.
    """
    # Gather context
    context_parts = []
    if file:
        extracted = extract_text_from_file(file)
        context_parts.append(f"[FILE_CONTENT]\n{extracted}\n[/FILE_CONTENT]")
    if url_text:
        #url_text can be a string of text or a URL
        if url_text.startswith('http'):
            # Download the URL content
            response = requests.get(url_text)
            url_text = response.text
        else:
            # Assume it's plain text
            pass

        context_parts.append(f"[URL_TEXT]\n{url_text}\n[/URL_TEXT]")

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

    # Build messages for tool-enabled streaming
    tools = get_tool_schemas()
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt + "\n\n" + rule_text},
        {"role": "user", "content": "\n".join(context_parts + [user_input])},
    ]

    async def token_generator():
        # Send rule chunks first
        yield f"data: {json.dumps({'type': 'rule_chunks', 'rule_chunks': [c for c,_ in rule_hits]})}\n\n"

        # Stream the assistant response, surface tool_calls events to UI as info
        async for data in generate_stream(
            "\n".join(context_parts + [user_input]),
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
                    yield f"data: {json.dumps({'type': 'token', 'token': data['content']})}\n\n"
            elif isinstance(data, str) and data:
                yield f"data: {json.dumps({'type': 'token', 'token': data})}\n\n"

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