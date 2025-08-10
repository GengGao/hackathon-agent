-- Add session association to rules_context to scope context per chat session
-- Note: SQLite supports adding a column but not adding a foreign key constraint post-hoc
-- We add an indexed TEXT column for session_id. Application code ensures referential integrity.

ALTER TABLE rules_context ADD COLUMN session_id TEXT;

CREATE INDEX IF NOT EXISTS idx_rules_context_session_id ON rules_context(session_id);


