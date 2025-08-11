from pathlib import Path
from typing import List

from fastapi import UploadFile
import io
import docx  # type: ignore
import pdfminer.high_level  # type: ignore
import pytesseract  # type: ignore
from PIL import Image  # type: ignore

from rag import RuleRAG


# Shared RAG instance (scoped per-session by callers)
rag = RuleRAG(Path(__file__).resolve().parents[1] / "docs" / "rules.txt", lazy=False)


MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB limit per file
ALLOWED_FILE_EXT = {".txt", ".md", ".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"}


def extract_text_from_file(file: UploadFile) -> str:
    filename = file.filename
    lower = filename.lower()
    ext = "".join([".", filename.split(".")[-1].lower()]) if "." in filename else ""
    raw = file.file.read()
    if len(raw) > MAX_FILE_BYTES:
        return f"[File '{filename}' skipped: exceeds size limit]"
    if ext and ext not in ALLOWED_FILE_EXT:
        return f"[File '{filename}' skipped: extension not allowed]"
    try:
        if lower.endswith(".pdf"):
            return pdfminer.high_level.extract_text(io.BytesIO(raw))
        elif lower.endswith(".docx") or lower.endswith(".doc"):
            d = docx.Document(io.BytesIO(raw))
            return "\n".join(p.text for p in d.paragraphs)
        elif lower.endswith((".png", ".jpg", ".jpeg")):
            try:
                img = Image.open(io.BytesIO(raw))
                text = pytesseract.image_to_string(img)
                return text or f"[No text detected in image {filename}]"
            except Exception as e:  # pragma: no cover - best-effort OCR
                return f"[Image OCR failed for {filename}: {e}]"
        else:
            return raw.decode("utf-8", errors="ignore")
    except Exception as e:  # pragma: no cover - best-effort extraction
        return f"[Failed to process {filename}: {e}]"


def build_url_block(url: str, *, timeout: int = 5, max_bytes: int = 100_000) -> str:
    import requests

    try:
        resp = requests.get(url, timeout=timeout, stream=True)
        ctype = resp.headers.get("Content-Type", "")
        if "text" not in ctype.lower():
            snippet = f"[Blocked non-text content-type {ctype}]"
        else:
            content_bytes = resp.content[:max_bytes]
            if len(resp.content) > max_bytes:
                snippet = content_bytes.decode("utf-8", errors="ignore") + "\n[Truncated]"
            else:
                snippet = content_bytes.decode("utf-8", errors="ignore")
        return f"[URL:{url}]\n{snippet}\n[/URL]"
    except Exception as e:
        return f"[URL_FETCH_FAILED:{url}]\nError: {e}"


def get_generate_stream():
    """Return the streaming function used by chat routes.

    Tests monkeypatch `router.generate_stream`; to preserve backward compatibility
    after refactor, fetch from `router` module when available, otherwise fall back
    to the implementation in `llm`.
    """
    try:
        import router as router_module  # type: ignore

        gs = getattr(router_module, "generate_stream", None)
        if callable(gs):
            return gs
    except Exception:
        pass
    from llm import generate_stream as real_generate_stream  # lazy import to avoid cycles

    return real_generate_stream


