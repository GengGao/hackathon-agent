from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from llm import generate_async
from rag import RuleRAG
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
    elif filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
        img = Image.open(io.BytesIO(content))
        return pytesseract.image_to_string(img)
    else:
        # Assume plain text
        return content.decode('utf-8', errors='ignore')

@router.post("/chat")
async def chat(
    user_input: str = Form(...),
    file: UploadFile = File(None),
    url_text: str = Form(None)  # you can paste copied content from a URL
) -> JSONResponse:
    """
    Main entry point:
    - user_input: the natural‑language prompt
    - optional file upload (PDF, DOCX, image)
    - optional pasted url_text for any offline copy of a web page
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

    # Build system prompt for the LLM
    system_prompt = f"""You are **HackathonGPT**, an expert assistant that helps participants create, refine, and submit hackathon projects completely offline.

    - Use ONLY the information supplied in the {rule_text} (the official competition rules you have been given as factual reference). Do not hallucinate external policies.
    - When a user asks for an idea, suggest 3–5 distinct concepts that can be built with *gpt‑oss‑20b* locally and that satisfy the “Best Local Agent” category.
    - When checking compliance, quote the exact rule number (e.g., “Rule 4.1 – Eligibility”) and explain if the draft violates it.
    - When building a submission, fill in the required fields:
    * Title (≤ 100 chars)
    * Short description (≤ 300 words)
    * Project URL (optional)
    * Eligibility summary
    * Technical stack (must include Ollama + gpt‑oss‑20b)
    * Timeline (weekly milestones)
    * How the project will be demonstrated offline.
    - Keep the tone clear, concise, and encouraging. Do not mention any external APIs or internet resources.
    - When responding, cite the rule chunk numbers in brackets if you refer to a specific rule."""

    # Assemble final prompt
    full_prompt = "\n".join(context_parts + [user_input])

    # Call LLM
    response = await generate_async(full_prompt, system=system_prompt)

    return JSONResponse(content={"response": response, "rule_chunks": [c for c,_ in rule_hits]})


# @router.post("/chat-stream")
# async def chat_stream(
#     user_input: str = Form(...),
#     file: UploadFile = File(None),
#     url_text: str = Form(None),
# ):
#     # Same context/rag steps as before (omitted for brevity)
#     # ...

#     async def token_generator():
#         # `generate_stream` yields token strings
#         async for token in generate_stream(full_prompt, system=system_prompt):
#             # Wrap each token as a JSON line for SSE
#             yield f"data: {json.dumps({'token': token})}\n\n"

#     return StreamingResponse(token_generator(), media_type="text/event-stream")