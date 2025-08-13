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

    # Verify stored user message has tags stripped but metadata captured
    messages = get_chat_messages(session_id)
    user_msgs = [m for m in messages if m["role"] == "user"]
    assert any("[FILE:a.txt]" not in m["content"] for m in user_msgs)
    assert any("[FILE:b.txt]" not in m["content"] for m in user_msgs)


def test_url_text_plain_passthrough(client: TestClient, monkeypatch):
    # Patch generate_stream to avoid real LLM
    import router as router_module

    async def fake_stream(prompt: str, **kwargs):
        yield {"type": "content", "content": "OK"}

    monkeypatch.setattr(router_module, "generate_stream", fake_stream)

    resp = client.post("/api/chat-stream", data={"user_input": "Hi", "url_text": "just some notes"})
    assert resp.status_code == 200


def test_chat_sse_event_ordering(client: TestClient, monkeypatch):
    """Ensure SSE events follow the required order:
    session_info → rule_chunks → (thinking/tool_calls)* → token → end
    """
    import router as router_module

    async def fake_stream(prompt: str, **kwargs):
        # Middle phase may include multiple thinking/tool_calls in any order
        yield {"type": "thinking", "content": "Reasoning step 1"}
        yield {
            "type": "tool_calls",
            "tool_calls": [
                {"id": "call_1", "name": "list_todos", "arguments": "{}"}
            ],
        }
        yield {"type": "thinking", "content": "Reasoning step 2"}
        # Final content chunk
        yield {"type": "content", "content": "Final answer"}
        return

    monkeypatch.setattr(router_module, "generate_stream", fake_stream)

    data = {"user_input": "Check ordering"}
    event_types: list[str] = []

    with client.stream("POST", "/api/chat-stream", data=data) as r:
        assert r.status_code == 200
        for raw_line in r.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", "ignore") if isinstance(raw_line, (bytes, bytearray)) else raw_line
            if line.startswith(": "):
                # Heartbeat comment (": ping")
                continue
            if not line.startswith("data: "):
                continue
            payload = json.loads(line[6:])
            etype = payload.get("type")
            if etype:
                event_types.append(etype)
            if etype == "end":
                break

    assert len(event_types) >= 4, f"Unexpected event stream: {event_types}"
    assert event_types[0] == "session_info", event_types
    assert event_types[1] == "rule_chunks", event_types
    assert "token" in event_types, f"Missing token event: {event_types}"
    assert event_types[-1] == "end", event_types

    # token must occur after any thinking/tool_calls events
    first_token_idx = event_types.index("token")
    last_middle_idx = max([i for i, t in enumerate(event_types) if t in ("thinking", "tool_calls")] or [-1])
    assert first_token_idx > last_middle_idx, f"token appeared before thinking/tool_calls: {event_types}"
