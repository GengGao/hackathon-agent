-- Create extraction_tasks table for background extraction tasks
-- This table stores extraction tasks and their results for persistence

CREATE TABLE IF NOT EXISTS extraction_tasks (
    task_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    task_type TEXT NOT NULL, -- 'conversation', 'progress', 'rules', etc.
    extractor_type TEXT NOT NULL, -- 'ConversationExtractor', 'ProgressExtractor', etc.
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    progress REAL DEFAULT 0.0, -- Progress percentage (0.0 to 1.0)
    current_step TEXT, -- Current step description
    current_step_num INTEGER DEFAULT 0, -- Current step number
    total_steps INTEGER DEFAULT 0, -- Total number of steps
    error TEXT, -- Error message if failed
    result_data TEXT, -- JSON result data when completed
    message_limit INTEGER DEFAULT 50, -- Message limit for extraction
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    has_result BOOLEAN DEFAULT FALSE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_extraction_tasks_session ON extraction_tasks(session_id);
CREATE INDEX IF NOT EXISTS idx_extraction_tasks_status ON extraction_tasks(status);
CREATE INDEX IF NOT EXISTS idx_extraction_tasks_created ON extraction_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_extraction_tasks_type ON extraction_tasks(task_type);
