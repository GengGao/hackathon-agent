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
    # Seed initial rules into rules_context table if not already present
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) as c FROM rules_context WHERE source='initial'")
            row = cur.fetchone()
            if row and row[0] == 0:
                # Read default rules file
                rules_path = Path(__file__).resolve().parents[1] / 'docs' / 'rules.txt'
                if rules_path.exists():
                    content = rules_path.read_text(encoding='utf-8')
                    conn.execute(
                        "INSERT INTO rules_context(source, filename, content) VALUES(?,?,?)",
                        ("initial", "rules.txt", content)
                    )
    except Exception:
        # Non-fatal; table might not exist yet in certain migration ordering contexts
        pass


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


def list_todos_db(session_id: Optional[str] = None) -> list[sqlite3.Row]:
    with get_connection() as conn:
        # Prefer ordering by status (pending first), sort_order then id if columns exist
        try:
            if session_id is None:
                cur = conn.execute(
                    "SELECT * FROM todos WHERE (session_id IS NULL OR session_id = '') ORDER BY "
                    "CASE WHEN status='pending' THEN 0 WHEN status='in_progress' THEN 1 ELSE 2 END, "
                    "sort_order ASC, id ASC"
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM todos WHERE session_id = ? ORDER BY "
                    "CASE WHEN status='pending' THEN 0 WHEN status='in_progress' THEN 1 ELSE 2 END, "
                    "sort_order ASC, id ASC",
                    (session_id,)
                )
        except Exception:
            # Legacy schema fallback (no status/sort columns or session_id column)
            if session_id is None:
                cur = conn.execute("SELECT * FROM todos ORDER BY id ASC")
            else:
                # If session_id column doesn't exist, there can't be scoped rows; return empty
                try:
                    cur = conn.execute("SELECT * FROM todos WHERE session_id = ? ORDER BY id ASC", (session_id,))
                except Exception:
                    return []
        return list(cur.fetchall())


def add_todo_db(item: str, session_id: Optional[str] = None) -> int:
    with get_connection() as conn:
        # Attempt extended insert if columns exist
        try:
            cur = conn.execute(
                "INSERT INTO todos(item, status, sort_order, session_id) VALUES(?, 'pending', 0, ?)",
                (item, session_id)
            )
        except Exception:
            # Fallback to legacy schemas
            try:
                cur = conn.execute("INSERT INTO todos(item, status, sort_order) VALUES(?, 'pending', 0)", (item,))
            except Exception:
                cur = conn.execute("INSERT INTO todos(item) VALUES(?)", (item,))
        return int(cur.lastrowid)


def clear_todos_db(session_id: Optional[str] = None) -> int:
    """Delete todos.

    - When session_id is provided, delete only that session's todos.
    - When session_id is None, delete all todos (back-compat for tests and maintenance utilities).
    Returns number of rows deleted.
    """
    with get_connection() as conn:
        try:
            if session_id:
                cur = conn.execute("DELETE FROM todos WHERE session_id = ?", (session_id,))
            else:
                cur = conn.execute("DELETE FROM todos")
            return cur.rowcount or 0
        except Exception:
            # Legacy schema fallback (no session_id column)
            cur = conn.execute("DELETE FROM todos")
            return cur.rowcount or 0


def update_todo_db(todo_id: int, item: Optional[str] = None, status: Optional[str] = None,
                   sort_order: Optional[int] = None, session_id: Optional[str] = None) -> bool:
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
    if sort_order is not None:
        fields.append("sort_order = ?")
        params.append(sort_order)
    if not fields:
        return False
    where_clause = "id = ?"
    params.append(todo_id)
    if session_id is not None:
        where_clause += " AND session_id = ?"
        params.append(session_id)
    sql = "UPDATE todos SET " + ", ".join(fields) + ", updated_at = datetime('now') WHERE " + where_clause
    with get_connection() as conn:
        try:
            cur = conn.execute(sql, params)
            if cur.rowcount > 0:
                return True
            # If no rows were reported as changed, it might be a no-op (values identical).
            # Consider this a success if the todo exists.
            try:
                if session_id is not None:
                    chk = conn.execute("SELECT 1 FROM todos WHERE id = ? AND session_id = ?", (todo_id, session_id)).fetchone()
                else:
                    chk = conn.execute("SELECT 1 FROM todos WHERE id = ?", (todo_id,)).fetchone()
                return chk is not None
            except Exception:
                return False
        except Exception:
            # Legacy schema fallback (only item available)
            if item is not None:
                cur = conn.execute("UPDATE todos SET item=? WHERE id=?", (item, todo_id))
                if cur.rowcount > 0:
                    return True
                try:
                    chk = conn.execute("SELECT 1 FROM todos WHERE id = ?", (todo_id,)).fetchone()
                    return chk is not None
                except Exception:
                    return False
            return False


def delete_todo_db(todo_id: int, session_id: Optional[str] = None) -> bool:
    with get_connection() as conn:
        try:
            if session_id is not None:
                cur = conn.execute("DELETE FROM todos WHERE id = ? AND session_id = ?", (todo_id, session_id))
            else:
                cur = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            return cur.rowcount > 0
        except Exception:
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


# --- Rules / Context storage helpers ---

def add_rule_context(
    source: str,
    content: str,
    filename: Optional[str] = None,
    active: bool = True,
    session_id: Optional[str] = None,
) -> int:
    """Insert a context row. If session_id is provided, associate it with that chat session.

    When session_id is None, the row is considered global and may be included for all sessions.
    """
    with get_connection() as conn:
        # Backward compatible insert for older DBs without session_id
        try:
            cur = conn.execute(
                "INSERT INTO rules_context(source, filename, content, active, session_id) VALUES(?,?,?,?,?)",
                (source, filename, content, 1 if active else 0, session_id)
            )
        except Exception:
            cur = conn.execute(
                "INSERT INTO rules_context(source, filename, content, active) VALUES(?,?,?,?)",
                (source, filename, content, 1 if active else 0)
            )
        return int(cur.lastrowid)


def list_active_rules(session_id: Optional[str] = None) -> list[str]:
    """Return active rule contents.

    If session_id is provided, include rows that are either global (NULL session_id)
    or explicitly for that session. Otherwise, include all active rows (legacy behavior).
    """
    with get_connection() as conn:
        if session_id is None:
            cur = conn.execute("SELECT content FROM rules_context WHERE active=1 ORDER BY id ASC")
            return [r[0] for r in cur.fetchall()]
        try:
            cur = conn.execute(
                "SELECT content FROM rules_context WHERE active=1 AND (session_id IS NULL OR session_id = ?) ORDER BY id ASC",
                (session_id,)
            )
            return [r[0] for r in cur.fetchall()]
        except Exception:
            # Fallback for legacy schema without session_id column
            cur = conn.execute("SELECT content FROM rules_context WHERE active=1 ORDER BY id ASC")
            return [r[0] for r in cur.fetchall()]


def list_active_rule_rows(session_id: Optional[str] = None) -> list[dict]:
    """Return active rule rows with id/source/filename/content for RAG metadata.

    This avoids changing existing list_active_rules() behavior while enabling
    richer context. Returns a list of dictionaries.
    """
    with get_connection() as conn:
        try:
            if session_id is None:
                cur = conn.execute(
                    "SELECT id, source, filename, content, session_id FROM rules_context WHERE active=1 ORDER BY id ASC"
                )
            else:
                cur = conn.execute(
                    "SELECT id, source, filename, content, session_id FROM rules_context WHERE active=1 AND (session_id IS NULL OR session_id = ?) ORDER BY id ASC",
                    (session_id,)
                )
        except Exception:
            # Legacy schema without session_id
            cur = conn.execute(
                "SELECT id, source, filename, content FROM rules_context WHERE active=1 ORDER BY id ASC"
            )
        rows: list[dict] = []
        for r in cur.fetchall():
            try:
                rows.append({
                    "id": r[0],
                    "source": r[1],
                    "filename": r[2],
                    "content": r[3],
                    "session_id": r[4],
                })
            except Exception:
                rows.append({
                    "id": r[0],
                    "source": r[1],
                    "filename": r[2],
                    "content": r[3],
                })
        return rows


def deactivate_rule(rule_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("UPDATE rules_context SET active=0 WHERE id=?", (rule_id,))
        return cur.rowcount > 0


def get_rules_rows(session_id: Optional[str] = None) -> list[dict]:
    with get_connection() as conn:
        try:
            if session_id is None:
                cur = conn.execute("SELECT id, source, filename, active, created_at, length(content) as size, session_id FROM rules_context ORDER BY id ASC")
            else:
                cur = conn.execute(
                    "SELECT id, source, filename, active, created_at, length(content) as size, session_id FROM rules_context WHERE session_id IS NULL OR session_id = ? ORDER BY id ASC",
                    (session_id,)
                )
            rows = []
            for r in cur.fetchall():
                rows.append({
                    "id": r[0],
                    "source": r[1],
                    "filename": r[2],
                    "active": bool(r[3]),
                    "created_at": r[4],
                    "size": r[5],
                    "session_id": r[6],
                })
            return rows
        except Exception:
            cur = conn.execute("SELECT id, source, filename, active, created_at, length(content) as size FROM rules_context ORDER BY id ASC")
            rows = []
            for r in cur.fetchall():
                rows.append({"id": r[0], "source": r[1], "filename": r[2], "active": bool(r[3]), "created_at": r[4], "size": r[5]})
            return rows


