-- Rollback extraction metadata changes
-- This undoes the changes from 008_extraction_metadata.sql

-- Drop the extraction metadata table and its indexes
DROP INDEX IF EXISTS idx_extraction_metadata_created;
DROP INDEX IF EXISTS idx_extraction_metadata_type;
DROP INDEX IF EXISTS idx_extraction_metadata_session;
DROP TABLE IF EXISTS extraction_metadata;

-- Remove extraction columns from rules_context table
-- Note: SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
-- First, create a backup of the current table structure without extraction columns

CREATE TABLE rules_context_backup AS
SELECT id, session_id, source, filename, content, active, created_at
FROM rules_context;

-- Drop the original table
DROP TABLE rules_context;

-- Recreate the table without extraction columns
CREATE TABLE rules_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    source TEXT NOT NULL,
    filename TEXT,
    content TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Restore the data
INSERT INTO rules_context (id, session_id, source, filename, content, active, created_at)
SELECT id, session_id, source, filename, content, active, created_at
FROM rules_context_backup;

-- Drop the backup table
DROP TABLE rules_context_backup;

-- Recreate the original index
CREATE INDEX IF NOT EXISTS idx_rules_context_session ON rules_context(session_id);
CREATE INDEX IF NOT EXISTS idx_rules_context_active ON rules_context(active);