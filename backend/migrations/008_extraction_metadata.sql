-- Add structured extraction support to rules_context table
-- These fields support LangExtract integration for enhanced rule processing

ALTER TABLE rules_context ADD COLUMN extraction_data TEXT; -- JSON field for structured extraction results
ALTER TABLE rules_context ADD COLUMN extraction_schema TEXT; -- Schema identifier used for extraction
ALTER TABLE rules_context ADD COLUMN extraction_version INTEGER DEFAULT 1; -- Schema version for cache invalidation

-- Create table for extraction metadata and analytics
CREATE TABLE IF NOT EXISTS extraction_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    extraction_type TEXT NOT NULL, -- 'rules', 'documents', 'conversation', etc.
    schema_version INTEGER NOT NULL DEFAULT 1,
    extraction_method TEXT, -- 'langextract', 'fallback', 'heuristic'
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_confidence REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT -- JSON field for additional extraction statistics
);

-- Index for efficient querying of extraction metadata
CREATE INDEX IF NOT EXISTS idx_extraction_metadata_session ON extraction_metadata(session_id);
CREATE INDEX IF NOT EXISTS idx_extraction_metadata_type ON extraction_metadata(extraction_type);
CREATE INDEX IF NOT EXISTS idx_extraction_metadata_created ON extraction_metadata(created_at);