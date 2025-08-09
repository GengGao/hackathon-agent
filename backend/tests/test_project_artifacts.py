import pytest
import tempfile
import os
from pathlib import Path
from models.db import (
    init_db, get_connection, set_db_path,
    create_chat_session, add_chat_message,
    save_project_artifact, get_project_artifact, get_all_project_artifacts
)
from tools import derive_project_idea, create_tech_stack, summarize_chat_history


@pytest.fixture
def test_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db_path = tmp.name

    try:
        set_db_path(test_db_path)
        init_db()
        yield test_db_path
    finally:
        # Clean up
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)


def test_project_artifacts_crud(test_db):
    """Test project artifacts CRUD operations."""
    # Create a test session and add some messages
    session_id = "test-session-123"
    create_chat_session(session_id, "Test Session")

    add_chat_message(session_id, "user", "I want to build a web app with React and FastAPI")
    add_chat_message(session_id, "assistant", "Great! That's a modern tech stack.")
    add_chat_message(session_id, "user", "It should have user authentication and a dashboard")

    # Test saving project artifacts
    artifact_id = save_project_artifact(
        session_id,
        "project_idea",
        "A web application with user authentication",
        {"keywords": ["web", "auth"]}
    )
    assert artifact_id > 0

    # Test retrieving specific artifact
    artifact = get_project_artifact(session_id, "project_idea")
    assert artifact is not None
    assert artifact["content"] == "A web application with user authentication"
    assert artifact["session_id"] == session_id
    assert artifact["artifact_type"] == "project_idea"

    # Test updating existing artifact
    new_artifact_id = save_project_artifact(
        session_id,
        "project_idea",
        "Updated web application with advanced features",
        {"keywords": ["web", "auth", "dashboard"]}
    )
    assert new_artifact_id == artifact_id  # Should be same ID (update, not insert)

    # Verify update
    updated_artifact = get_project_artifact(session_id, "project_idea")
    assert updated_artifact["content"] == "Updated web application with advanced features"

    # Test getting all artifacts
    save_project_artifact(session_id, "tech_stack", "React + FastAPI + SQLite")
    all_artifacts = get_all_project_artifacts(session_id)
    assert len(all_artifacts) == 2

    artifact_types = [a["artifact_type"] for a in all_artifacts]
    assert "project_idea" in artifact_types
    assert "tech_stack" in artifact_types


def test_derive_project_idea_tool(test_db):
    """Test the derive_project_idea function."""
    # Create a test session with relevant messages
    session_id = "test-session-456"
    create_chat_session(session_id, "Project Planning Session")

    add_chat_message(session_id, "user", "I want to create a web app for tracking fitness goals")
    add_chat_message(session_id, "assistant", "That sounds like a great idea!")
    add_chat_message(session_id, "user", "It should have charts and analytics")
    add_chat_message(session_id, "assistant", "You could use React for the frontend")

    # Test deriving project idea
    result = derive_project_idea(session_id)

    assert result["ok"] is True
    assert "project_idea" in result
    assert len(result["project_idea"]) > 0
    assert "based_on_messages" in result
    assert result["based_on_messages"] == 4

    # Verify it was saved to database
    saved_artifact = get_project_artifact(session_id, "project_idea")
    assert saved_artifact is not None
    assert saved_artifact["content"] == result["project_idea"]


def test_create_tech_stack_tool(test_db):
    """Test the create_tech_stack function."""
    # Create a test session with tech mentions
    session_id = "test-session-789"
    create_chat_session(session_id, "Tech Discussion")

    add_chat_message(session_id, "user", "I'm thinking of using React for frontend")
    add_chat_message(session_id, "assistant", "React is a great choice!")
    add_chat_message(session_id, "user", "And FastAPI for the backend with SQLite database")
    add_chat_message(session_id, "assistant", "That's a solid tech stack")

    # Test creating tech stack
    result = create_tech_stack(session_id)

    assert result["ok"] is True
    assert "tech_stack" in result
    assert "technologies" in result
    assert len(result["tech_stack"]) > 0

    # Check that it detected the mentioned technologies
    tech_stack = result["tech_stack"].lower()
    assert "react" in tech_stack or "frontend" in tech_stack
    assert "fastapi" in tech_stack or "backend" in tech_stack
    assert "sqlite" in tech_stack or "database" in tech_stack


def test_summarize_chat_history_tool(test_db):
    """Test the summarize_chat_history function."""
    # Create a test session with varied content
    session_id = "test-session-summary"
    create_chat_session(session_id, "Development Session")

    add_chat_message(session_id, "user", "Let's start building our app")
    add_chat_message(session_id, "assistant", "Great! I'll help you plan this out.")
    add_chat_message(session_id, "user", "We need user authentication first")
    add_chat_message(session_id, "assistant", "I'll add that to your todo list")
    add_chat_message(session_id, "user", "Then we can work on the dashboard")

    # Test summarizing chat history
    result = summarize_chat_history(session_id)

    assert result["ok"] is True
    assert "submission_summary" in result
    assert "statistics" in result
    assert len(result["submission_summary"]) > 0

    # Check statistics
    stats = result["statistics"]
    assert stats["total_messages"] == 5
    assert stats["user_messages"] == 3
    assert stats["assistant_messages"] == 2

    # Verify summary contains expected sections
    summary = result["submission_summary"]
    assert "## Hackathon Project Summary" in summary
    assert "Total Messages:" in summary


def test_tool_error_handling(test_db):
    """Test error handling for tools with invalid session."""
    # Test with empty session ID
    result = derive_project_idea("")
    assert result["ok"] is False
    assert "error" in result

    result = create_tech_stack("")
    assert result["ok"] is False
    assert "error" in result

    result = summarize_chat_history("")
    assert result["ok"] is False
    assert "error" in result

    # Test with non-existent session
    result = derive_project_idea("non-existent-session")
    assert result["ok"] is False
    assert "No chat history found" in result["error"]
