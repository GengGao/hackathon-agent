from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterator, Optional, Sequence
from contextlib import contextmanager


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_PATH = DATA_DIR / "app.db"

_DB_PATH: Path = Path(os.getenv("HACKATHON_DB_PATH", str(DEFAULT_DB_PATH)))


def set_db_path(path: Path | str) -> None:
    global _DB_PATH
    _DB_PATH = Path(path)
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db_path() -> Path:
    return _DB_PATH


def _connect(path: Optional[Path] = None) -> sqlite3.Connection:
    target = Path(path) if path else get_db_path()
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enforce foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_connection(path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_schema_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )


def _get_applied_versions(conn: sqlite3.Connection) -> set[str]:
    _ensure_schema_migrations_table(conn)
    cur = conn.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def _record_applied(conn: sqlite3.Connection, version: str) -> None:
    conn.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)", (version,))


def _migration_files() -> Sequence[Path]:
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    files = sorted([p for p in migrations_dir.iterdir() if p.suffix == ".sql"])
    return files


def run_migrations(path: Optional[Path] = None) -> None:
    """Run pending SQL migrations found in backend/migrations/*.sql in sorted order."""
    with get_connection(path) as conn:
        applied = _get_applied_versions(conn)
        for sql_file in _migration_files():
            version = sql_file.stem
            if version in applied:
                continue
            sql = sql_file.read_text(encoding="utf-8")
            # Allow multiple statements per file
            try:
                conn.executescript(sql)
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                # Gracefully allow duplicate column additions (idempotent ALTER COLUMN attempts)
                if "duplicate column name" in msg:
                    pass
                else:
                    raise
            _record_applied(conn, version)


def init_db(path: Optional[Path] = None) -> None:
    """Initialize database by running migrations. Safe to call multiple times."""
    run_migrations(path)
    # Ensure settings table exists (lightweight key/value store)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )


# --- Convenience CRUD helpers used by tests and future routes ---

def create_project(name: str, description: Optional[str] = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO projects(name, description) VALUES(?, ?)", (name, description)
        )
        return int(cur.lastrowid)


def get_project_by_name(name: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM projects WHERE name = ?", (name,))
        row = cur.fetchone()
        return row


def add_project_file(
    project_id: int,
    filename: str,
    path: str,
    content_type: Optional[str] = None,
    size: Optional[int] = None,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO project_files(project_id, filename, path, content_type, size)
            VALUES(?, ?, ?, ?, ?)
            """,
            (project_id, filename, path, content_type, size),
        )
        return int(cur.lastrowid)


def list_project_files(project_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM project_files WHERE project_id = ? ORDER BY created_at ASC",
            (project_id,),
        )
        return list(cur.fetchall())


def list_todos_db() -> list[sqlite3.Row]:
    with get_connection() as conn:
        # Prefer ordering by status (pending first), priority, sort_order then id if columns exist
        try:
            cur = conn.execute(
                "SELECT * FROM todos ORDER BY "+
                "CASE WHEN status='pending' THEN 0 WHEN status='in_progress' THEN 1 ELSE 2 END, "
                "priority ASC, sort_order ASC, id ASC"
            )
        except Exception:
            # Legacy schema fallback
            cur = conn.execute("SELECT * FROM todos ORDER BY id ASC")
        return list(cur.fetchall())


def add_todo_db(item: str) -> int:
    with get_connection() as conn:
        # Attempt extended insert if columns exist
        try:
            cur = conn.execute(
                "INSERT INTO todos(item, status, priority, sort_order) VALUES(?, 'pending', 3, 0)",
                (item,)
            )
        except Exception:
            cur = conn.execute("INSERT INTO todos(item) VALUES(?)", (item,))
        return int(cur.lastrowid)


def clear_todos_db() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM todos")


def update_todo_db(todo_id: int, item: Optional[str] = None, status: Optional[str] = None,
                   priority: Optional[int] = None, sort_order: Optional[int] = None) -> bool:
    """Update fields on a todo. Returns True if a row was modified."""
    fields = []
    params: list[Any] = []  # type: ignore
    if item is not None:
        fields.append("item = ?")
        params.append(item)
    if status is not None:
        fields.append("status = ?")
        params.append(status)
        if status == 'done':
            fields.append("completed_at = datetime('now')")
        else:
            fields.append("completed_at = NULL")
    if priority is not None:
        fields.append("priority = ?")
        params.append(priority)
    if sort_order is not None:
        fields.append("sort_order = ?")
        params.append(sort_order)
    if not fields:
        return False
    sql = "UPDATE todos SET " + ", ".join(fields) + ", updated_at = datetime('now') WHERE id = ?"
    params.append(todo_id)
    with get_connection() as conn:
        try:
            cur = conn.execute(sql, params)
            return cur.rowcount > 0
        except Exception:
            # Legacy schema fallback (only item available)
            if item is not None:
                cur = conn.execute("UPDATE todos SET item=? WHERE id=?", (item, todo_id))
                return cur.rowcount > 0
            return False


def delete_todo_db(todo_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        return cur.rowcount > 0


# --- Chat history CRUD operations ---

def create_chat_session(session_id: str, title: Optional[str] = None) -> int:
    """Create a new chat session and return its internal ID."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO chat_sessions(session_id, title) VALUES(?, ?)",
            (session_id, title)
        )
        if cur.rowcount == 0:
            # Session already exists, get its ID
            cur = conn.execute("SELECT id FROM chat_sessions WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            return int(row["id"]) if row else 0
        return int(cur.lastrowid)


def get_chat_session(session_id: str) -> Optional[sqlite3.Row]:
    """Get chat session by session_id."""
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,))
        return cur.fetchone()


def update_chat_session_title(session_id: str, title: str) -> None:
    """Update the title of a chat session."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = datetime('now') WHERE session_id = ?",
            (title, session_id)
        )


def add_chat_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[dict] = None
) -> int:
    """Add a chat message to the database."""
    import json
    metadata_json = json.dumps(metadata) if metadata else None

    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO chat_messages(session_id, role, content, metadata) VALUES(?, ?, ?, ?)",
            (session_id, role, content, metadata_json)
        )
        return int(cur.lastrowid)


def get_chat_messages(session_id: str, limit: Optional[int] = None) -> list[sqlite3.Row]:
    """Get chat messages for a session, ordered by creation time."""
    query = "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC"
    params = [session_id]

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    with get_connection() as conn:
        cur = conn.execute(query, params)
        return list(cur.fetchall())


def get_recent_chat_sessions(limit: int = 10) -> list[sqlite3.Row]:
    """Get recent chat sessions ordered by last update."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM chat_sessions ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        )
        return list(cur.fetchall())


def delete_chat_session(session_id: str) -> None:
    """Delete a chat session and all its messages."""
    with get_connection() as conn:
        conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))


# --- Project artifacts CRUD operations ---

def save_project_artifact(
    session_id: str,
    artifact_type: str,
    content: str,
    metadata: Optional[dict] = None
) -> int:
    """Save or update a project artifact for a session."""
    import json
    metadata_json = json.dumps(metadata) if metadata else None

    with get_connection() as conn:
        # Check if artifact already exists for this session and type
        cur = conn.execute(
            "SELECT id FROM project_artifacts WHERE session_id = ? AND artifact_type = ?",
            (session_id, artifact_type)
        )
        existing = cur.fetchone()

        if existing:
            # Update existing artifact
            conn.execute(
                "UPDATE project_artifacts SET content = ?, metadata = ?, updated_at = datetime('now') WHERE id = ?",
                (content, metadata_json, existing["id"])
            )
            return existing["id"]
        else:
            # Create new artifact
            cur = conn.execute(
                "INSERT INTO project_artifacts(session_id, artifact_type, content, metadata) VALUES(?, ?, ?, ?)",
                (session_id, artifact_type, content, metadata_json)
            )
            return int(cur.lastrowid)


def get_project_artifact(session_id: str, artifact_type: str) -> Optional[sqlite3.Row]:
    """Get a specific project artifact by session and type."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM project_artifacts WHERE session_id = ? AND artifact_type = ? ORDER BY updated_at DESC LIMIT 1",
            (session_id, artifact_type)
        )
        return cur.fetchone()


def get_all_project_artifacts(session_id: str) -> list[sqlite3.Row]:
    """Get all project artifacts for a session."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM project_artifacts WHERE session_id = ? ORDER BY artifact_type, updated_at DESC",
            (session_id,)
        )
        return list(cur.fetchall())


def delete_project_artifact(session_id: str, artifact_type: str) -> None:
    """Delete a specific project artifact."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM project_artifacts WHERE session_id = ? AND artifact_type = ?",
            (session_id, artifact_type)
        )

# --- Settings helpers ---
def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO app_settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
            (key, value)
        )


def get_setting(key: str) -> Optional[str]:
    with get_connection() as conn:
        cur = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None


