-- Store rules and arbitrary user-provided context (files, pasted text, URLs)
-- Each row is a logical source item that can be toggled active/inactive.
-- RAG index will be (re)built from all active rows.

CREATE TABLE IF NOT EXISTS rules_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL CHECK (source IN ('initial','file','text','url')),
    filename TEXT,
    content TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_rules_context_active ON rules_context(active);
CREATE INDEX IF NOT EXISTS idx_rules_context_source ON rules_context(source);
