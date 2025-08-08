from __future__ import annotations

from pathlib import Path
import tempfile
import json

from models.db import (
    set_db_path,
    init_db,
    create_chat_session,
    get_chat_session,
    add_chat_message,
    get_chat_messages,
    update_chat_session_title,
    get_recent_chat_sessions,
    delete_chat_session,
)
from models.schemas import ChatSession, ChatMessage


def with_temp_db(func):
    def wrapper():
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test.db"
            set_db_path(db_path)
            init_db()
            func()
    return wrapper


@with_temp_db
def test_chat_session_crud():
    session_id = "test-session-123"

    # Create session
    internal_id = create_chat_session(session_id, "Test Chat")
    assert internal_id > 0

    # Get session
    row = get_chat_session(session_id)
    assert row is not None
    session = ChatSession.from_row(row)
    assert session.session_id == session_id
    assert session.title == "Test Chat"

    # Update title
    update_chat_session_title(session_id, "Updated Title")
    updated_row = get_chat_session(session_id)
    updated_session = ChatSession.from_row(updated_row)
    assert updated_session.title == "Updated Title"


@with_temp_db
def test_chat_messages_crud():
    session_id = "test-session-456"
    create_chat_session(session_id)

    # Add messages
    metadata = {"file": {"filename": "test.txt", "size": 100}}
    user_msg_id = add_chat_message(session_id, "user", "Hello!", metadata)
    assistant_msg_id = add_chat_message(session_id, "assistant", "Hi there!")

    assert user_msg_id > 0
    assert assistant_msg_id > 0

    # Get messages
    messages = get_chat_messages(session_id)
    assert len(messages) == 2

    user_msg = ChatMessage.from_row(messages[0])
    assistant_msg = ChatMessage.from_row(messages[1])

    assert user_msg.role == "user"
    assert user_msg.content == "Hello!"
    assert user_msg.metadata == metadata

    assert assistant_msg.role == "assistant"
    assert assistant_msg.content == "Hi there!"
    assert assistant_msg.metadata is None


@with_temp_db
def test_recent_chat_sessions():
    # Create multiple sessions
    create_chat_session("session-1", "Chat 1")
    create_chat_session("session-2", "Chat 2")
    create_chat_session("session-3", "Chat 3")

    # Get recent sessions
    recent = get_recent_chat_sessions(limit=3)
    assert len(recent) == 3

    # Verify all sessions are returned
    session_ids = [row["session_id"] for row in recent]
    assert "session-1" in session_ids
    assert "session-2" in session_ids
    assert "session-3" in session_ids

    # Test limit functionality
    limited = get_recent_chat_sessions(limit=2)
    assert len(limited) == 2


@with_temp_db
def test_delete_chat_session():
    session_id = "test-delete-session"
    create_chat_session(session_id)
    add_chat_message(session_id, "user", "Test message")

    # Verify session and message exist
    assert get_chat_session(session_id) is not None
    assert len(get_chat_messages(session_id)) == 1

    # Delete session
    delete_chat_session(session_id)

    # Verify session and messages are deleted
    assert get_chat_session(session_id) is None
    assert len(get_chat_messages(session_id)) == 0


@with_temp_db
def test_duplicate_session_creation():
    session_id = "duplicate-test"

    # Create session twice
    id1 = create_chat_session(session_id, "First")
    id2 = create_chat_session(session_id, "Second")

    # Should return the same internal ID, not create duplicate
    assert id1 == id2

    # Title should remain the original
    row = get_chat_session(session_id)
    session = ChatSession.from_row(row)
    assert session.title == "First"
