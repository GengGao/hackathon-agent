-- Add session association to todos to scope items per chat session (similar to project_artifacts)
-- Note: SQLite cannot add a foreign key constraint via ALTER, so we only add a TEXT column and index.

ALTER TABLE todos ADD COLUMN session_id TEXT;

CREATE INDEX IF NOT EXISTS idx_todos_session_id ON todos(session_id);


