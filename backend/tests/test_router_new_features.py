from __future__ import annotations

import io
import json
import pytest
from fastapi.testclient import TestClient

from models.db import (
    set_db_path,
    init_db,
    create_chat_session,
    add_chat_message,
    get_chat_messages,
    get_setting,
)


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    """Provide a TestClient with temporary DB and patched model discovery to avoid network calls."""
    db_path = tmp_path / "test.db"
    set_db_path(db_path)
    init_db()

    # Patch model discovery to avoid network
    import llm

    async def fake_fetch_available_models():
        from llm import AVAILABLE_MODELS
        AVAILABLE_MODELS.clear()
        AVAILABLE_MODELS.extend(["gpt-oss:20b", "gpt-oss:120b", "local-test-model"])
        return AVAILABLE_MODELS

    async def fake_initialize_models():
        await fake_fetch_available_models()

    monkeypatch.setattr(llm, "fetch_available_models", fake_fetch_available_models)
    monkeypatch.setattr(llm, "initialize_models", fake_initialize_models)

    import main  # after monkeypatch
    return TestClient(main.app)


def test_chat_sessions_pagination(client: TestClient):
    for i in range(5):
        create_chat_session(f"session-{i}")
    r = client.get("/api/chat-sessions", params={"limit": 2, "offset": 1})
    assert r.status_code == 200
    data = r.json()
    assert data["limit"] == 2 and data["offset"] == 1
    assert len(data["sessions"]) == 2


def test_session_detail_pagination(client: TestClient):
    sid = "paging-session"
    create_chat_session(sid)
    for i in range(10):
        add_chat_message(sid, "user" if i % 2 == 0 else "assistant", f"msg-{i}")
    r = client.get(f"/api/chat-sessions/{sid}", params={"limit": 5, "offset": 2})
    assert r.status_code == 200
    data = r.json()
    assert data["limit"] == 5 and data["offset"] == 2
    assert len(data["messages"]) == 5
    assert data["messages"][0]["content"] == "msg-2"


def test_model_persistence(client: TestClient):
    resp = client.post("/api/ollama/model", data={"model": "local-test-model"})
    assert resp.status_code == 200, resp.text
    assert resp.json().get("model") == "local-test-model"
    assert get_setting("current_model") == "local-test-model"


def test_multi_file_ingestion_and_tool_calls(client: TestClient, monkeypatch):
    # Patch streaming to emit tool_calls + content deterministically
    import router as router_module

    async def fake_stream(prompt: str, **kwargs):
        yield {"type": "tool_calls", "tool_calls": [{"id": "call_1", "name": "list_todos", "arguments": "{}"}]}
        yield {"type": "content", "content": "Response after tool"}
        return

    monkeypatch.setattr(router_module, "generate_stream", fake_stream)

    files = [
        ("files", ("a.txt", io.BytesIO(b"Alpha content"), "text/plain")),
        ("files", ("b.txt", io.BytesIO(b"Beta content"), "text/plain")),
    ]
    data = {"user_input": "Test multi file"}

    session_id = None
    tool_calls_seen = False
    content_seen = False

    with client.stream("POST", "/api/chat-stream", data=data, files=files) as r:
        assert r.status_code == 200
        for raw_line in r.iter_lines():
            if not raw_line:
                continue
            # Support both bytes and str depending on TestClient backend
            if isinstance(raw_line, bytes) and raw_line.startswith(b"data: "):
                payload = json.loads(raw_line[6:])
            elif isinstance(raw_line, str) and raw_line.startswith("data: "):
                payload = json.loads(raw_line[6:])
            else:
                continue
            ptype = payload.get("type")
            if ptype == "session_info":
                session_id = payload.get("session_id")
            elif ptype == "tool_calls":
                tool_calls_seen = True
            elif ptype == "token" and "Response after tool" in payload.get("token", ""):
                content_seen = True
            if tool_calls_seen and content_seen and session_id:
                break

    assert tool_calls_seen, "Expected tool_calls SSE event"
    assert content_seen, "Expected content token"
    assert session_id, "Session id not received"

    # Verify stored user message contains markers for both files
    messages = get_chat_messages(session_id)
    user_msgs = [m for m in messages if m["role"] == "user"]
    assert any("[FILE:a.txt]" in m["content"] for m in user_msgs)
    assert any("[FILE:b.txt]" in m["content"] for m in user_msgs)


def test_url_text_plain_passthrough(client: TestClient, monkeypatch):
    # Patch generate_stream to avoid real LLM
    import router as router_module

    async def fake_stream(prompt: str, **kwargs):
        yield {"type": "content", "content": "OK"}

    monkeypatch.setattr(router_module, "generate_stream", fake_stream)

    resp = client.post("/api/chat-stream", data={"user_input": "Hi", "url_text": "just some notes"})
    assert resp.status_code == 200
