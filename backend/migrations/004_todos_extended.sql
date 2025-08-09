-- Extend existing legacy todos table (id, item) with new columns.
-- This file runs only once; subsequent runs are skipped by migration tracker.
-- We simply attempt to add columns; if they already exist the migration
-- would have been previously applied and this file not executed again.

ALTER TABLE todos ADD COLUMN status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','in_progress','done'));
ALTER TABLE todos ADD COLUMN priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5);
ALTER TABLE todos ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE todos ADD COLUMN created_at TEXT NOT NULL DEFAULT (datetime('now'));
ALTER TABLE todos ADD COLUMN updated_at TEXT NOT NULL DEFAULT (datetime('now'));
ALTER TABLE todos ADD COLUMN completed_at TEXT;

CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status);
CREATE INDEX IF NOT EXISTS idx_todos_priority ON todos(priority);
CREATE INDEX IF NOT EXISTS idx_todos_sort_order ON todos(sort_order);
