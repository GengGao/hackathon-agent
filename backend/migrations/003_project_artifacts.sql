-- Project artifacts table for storing generated content like project ideas, tech stacks, and summaries
CREATE TABLE IF NOT EXISTS project_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL CHECK (artifact_type IN ('project_idea', 'tech_stack', 'submission_summary')),
    content TEXT NOT NULL,
    metadata TEXT, -- JSON for additional data like confidence scores, keywords, etc.
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_artifacts_session_id ON project_artifacts(session_id);
CREATE INDEX IF NOT EXISTS idx_project_artifacts_type ON project_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_project_artifacts_updated_at ON project_artifacts(updated_at);
