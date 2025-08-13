from __future__ import annotations

import types
from typing import Iterable, List, Optional
import sys
import importlib
import importlib.util
import os

import requests

def _make_fake_session(
    *,
    head_headers: Optional[dict] = None,
    get_headers: Optional[dict] = None,
    get_chunks: Optional[List[bytes]] = None,
    head_exc: Optional[BaseException] = None,
    get_exc: Optional[BaseException] = None,
):
    class FakeResponse:
        def __init__(self, headers: Optional[dict] = None, chunks: Optional[List[bytes]] = None):
            self.headers = headers or {}
            self._chunks = chunks or []

        def iter_content(self, chunk_size: int = 8192) -> Iterable[bytes]:
            for c in self._chunks:
                yield c

        def close(self) -> None:
            return None

    class FakeSession:
        def __init__(self):
            self.max_redirects = 30

        def head(self, url: str, timeout: int = 5, allow_redirects: bool = True):
            if head_exc:
                raise head_exc
            return FakeResponse(headers=head_headers, chunks=None)

        def get(self, url: str, timeout: int = 5, stream: bool = True, allow_redirects: bool = True):
            if get_exc:
                raise get_exc
            return FakeResponse(headers=get_headers, chunks=get_chunks)

        def close(self) -> None:
            return None

    fake_requests = types.SimpleNamespace()
    fake_requests.Session = FakeSession
    return fake_requests


def _import_common_with_stubs(monkeypatch):
    # Stub heavy deps so import succeeds without installing extras
    fastapi_mod = types.ModuleType("fastapi")
    class _DummyAPIRouter:
        def __init__(self, *args, **kwargs):
            pass
        def include_router(self, *args, **kwargs):
            pass
    def _dummy_marker(default=None, *args, **kwargs):
        return default
    setattr(fastapi_mod, "APIRouter", _DummyAPIRouter)
    setattr(fastapi_mod, "UploadFile", object)
    setattr(fastapi_mod, "File", _dummy_marker)
    setattr(fastapi_mod, "Form", _dummy_marker)
    setattr(fastapi_mod, "Query", _dummy_marker)
    # responses submodule with minimal stubs
    fastapi_responses = types.ModuleType("fastapi.responses")
    class _Dummy:
        def __init__(self, *args, **kwargs):
            pass
    setattr(fastapi_responses, "StreamingResponse", _Dummy)
    setattr(fastapi_responses, "JSONResponse", _Dummy)
    setattr(fastapi_responses, "FileResponse", _Dummy)
    monkeypatch.setitem(sys.modules, "fastapi.responses", fastapi_responses)
    monkeypatch.setitem(sys.modules, "fastapi", fastapi_mod)

    docx_mod = types.ModuleType("docx")
    setattr(docx_mod, "Document", lambda *_args, **_kwargs: None)
    monkeypatch.setitem(sys.modules, "docx", docx_mod)

    pdfminer_mod = types.ModuleType("pdfminer")
    pdfminer_high = types.ModuleType("pdfminer.high_level")
    setattr(pdfminer_high, "extract_text", lambda *_args, **_kwargs: "")
    monkeypatch.setitem(sys.modules, "pdfminer", pdfminer_mod)
    monkeypatch.setitem(sys.modules, "pdfminer.high_level", pdfminer_high)

    pytesseract_mod = types.ModuleType("pytesseract")
    ptes = types.SimpleNamespace()
    setattr(pytesseract_mod, "pytesseract", ptes)
    setattr(pytesseract_mod, "image_to_string", lambda *_args, **_kwargs: "")
    monkeypatch.setitem(sys.modules, "pytesseract", pytesseract_mod)

    pil_pkg = types.ModuleType("PIL")
    pil_image = types.ModuleType("PIL.Image")
    pil_imageops = types.ModuleType("PIL.ImageOps")
    setattr(pil_pkg, "Image", pil_image)
    setattr(pil_pkg, "ImageOps", pil_imageops)
    setattr(pil_image, "open", lambda *_args, **_kwargs: types.SimpleNamespace(mode="RGB"))
    setattr(pil_imageops, "exif_transpose", lambda img: img)
    monkeypatch.setitem(sys.modules, "PIL", pil_pkg)
    monkeypatch.setitem(sys.modules, "PIL.Image", pil_image)
    monkeypatch.setitem(sys.modules, "PIL.ImageOps", pil_imageops)

    # Stub rag module used by common.py
    rag_mod = types.ModuleType("rag")
    class _DummyRuleRAG:
        def __init__(self, *args, **kwargs):
            self.chunks = []
        def set_session(self, *args, **kwargs):
            pass
        def rebuild(self, *args, **kwargs):
            return False
    setattr(rag_mod, "RuleRAG", _DummyRuleRAG)
    monkeypatch.setitem(sys.modules, "rag", rag_mod)

    # Load common.py by file path to avoid importing package initializers
    this_dir = os.path.dirname(__file__)
    backend_dir = os.path.abspath(os.path.join(this_dir, ".."))
    common_path = os.path.join(backend_dir, "api", "common.py")
    spec = importlib.util.spec_from_file_location("common_under_test", common_path)
    assert spec and spec.loader, "Failed to create spec for common.py"
    common_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common_mod)  # type: ignore[attr-defined]
    return common_mod


def test_blocked_non_text_from_head(monkeypatch):
    common_mod = _import_common_with_stubs(monkeypatch)
    fake_requests = _make_fake_session(head_headers={"Content-Type": "application/octet-stream"})
    monkeypatch.setattr(common_mod, "requests", fake_requests, raising=True)

    result = common_mod.build_url_block("http://example.com/binary")
    assert "Blocked non-text content-type application/octet-stream" in result


def test_blocked_by_head_content_length(monkeypatch):
    common_mod = _import_common_with_stubs(monkeypatch)
    # Head says text but size exceeds limit
    fake_requests = _make_fake_session(head_headers={"Content-Type": "text/plain", "Content-Length": "200000"})
    monkeypatch.setattr(common_mod, "requests", fake_requests, raising=True)

    result = common_mod.build_url_block("http://example.com/huge.txt")
    assert "Blocked: content-length" in result
    assert "> 100000" not in result  # exact message should include numeric values


def test_streaming_truncation_html(monkeypatch):
    common_mod = _import_common_with_stubs(monkeypatch)
    html_prefix = b"<html><body>"
    payload = b"x" * 150_000
    html_suffix = b"</body></html>"
    fake_requests = _make_fake_session(
        head_headers={"Content-Type": "text/html"},
        get_headers={"Content-Type": "text/html"},
        get_chunks=[html_prefix, payload, html_suffix],
    )
    monkeypatch.setattr(common_mod, "requests", fake_requests, raising=True)

    result = common_mod.build_url_block("http://example.com/large.html")
    assert result.startswith("[URL:http://example.com/large.html]")
    assert "[Truncated]" in result
    assert result.rstrip().endswith("[/URL]")


def test_too_many_redirects_on_head(monkeypatch):
    common_mod = _import_common_with_stubs(monkeypatch)
    exc = requests.exceptions.TooManyRedirects("redirect loop")
    fake_requests = _make_fake_session(head_exc=exc)
    monkeypatch.setattr(common_mod, "requests", fake_requests, raising=True)

    result = common_mod.build_url_block("http://example.com/loop")
    assert "too many redirects" in result.lower()


def test_xhtml_allowed(monkeypatch):
    common_mod = _import_common_with_stubs(monkeypatch)
    body = b"<html xmlns=\"http://www.w3.org/1999/xhtml\"><body>Hello</body></html>"
    fake_requests = _make_fake_session(
        head_headers={"Content-Type": "application/xhtml+xml"},
        get_headers={"Content-Type": "application/xhtml+xml"},
        get_chunks=[body],
    )
    monkeypatch.setattr(common_mod, "requests", fake_requests, raising=True)

    result = common_mod.build_url_block("http://example.com/x.xhtml")
    assert "Blocked" not in result
    assert "Hello" in result


