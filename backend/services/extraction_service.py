"""Background extraction service for LangExtract operations."""

import asyncio
import threading
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import logging

from extractors.conversation_extractor import ConversationExtractor
from extractors.progress_extractor import ProgressExtractor
from models.db import (get_chat_messages, create_extraction_task,
    update_extraction_task_status, save_extraction_result, get_extraction_tasks, get_extraction_task_by_id, get_extraction_result)

logger = logging.getLogger(__name__)

class ExtractionTask:
    """Represents a background extraction task."""

    def __init__(self, task_id: str, session_id: str, task_type: str,
                 extractor_type: str, message_limit: int = 50):
        self.task_id = task_id
        self.session_id = session_id
        self.task_type = task_type  # 'conversation' or 'progress'
        self.extractor_type = extractor_type
        self.message_limit = message_limit

        # Status tracking
        self.status = "queued"  # queued, running, completed, failed
        self.progress = 0.0  # 0.0 to 1.0
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        # Results
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None

        # Progress details
        self.current_step = "Initializing..."
        self.total_steps = 5
        self.current_step_num = 0

class ExtractionService:
    """Service for managing background LangExtract operations."""

    def __init__(self, max_workers: int = 2):
        self.tasks: Dict[str, ExtractionTask] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="extraction")
        self._lock = threading.RLock()

    def start_conversation_extraction(self, session_id: str, message_limit: int = 50) -> str:
        """Start background conversation extraction."""
        task_id = str(uuid.uuid4())

        # Create task in database
        create_extraction_task(
            task_id=task_id,
            session_id=session_id,
            task_type="conversation",
            extractor_type="ConversationExtractor",
            message_limit=message_limit
        )

        # Submit to thread pool
        self.executor.submit(self._run_conversation_extraction, task_id, session_id, message_limit)

        logger.info(f"Started conversation extraction task {task_id} for session {session_id}")
        return task_id

    def start_progress_extraction(self, session_id: str, message_limit: int = 50) -> str:
        """Start background progress extraction."""
        task_id = str(uuid.uuid4())

        # Create task in database
        create_extraction_task(
            task_id=task_id,
            session_id=session_id,
            task_type="progress",
            extractor_type="ProgressExtractor",
            message_limit=message_limit
        )

        # Submit to thread pool
        self.executor.submit(self._run_progress_extraction, task_id, session_id, message_limit)

        logger.info(f"Started progress extraction task {task_id} for session {session_id}")
        return task_id

    def _run_conversation_extraction(self, task_id: str, session_id: str, message_limit: int):
        """Run conversation extraction in background thread."""
        try:
            # Update task status to running
            update_extraction_task_status(
                task_id=task_id,
                status="running",
                current_step="Loading chat messages...",
                current_step_num=1,
                progress=0.2
            )

            # Get messages
            messages = get_chat_messages(session_id, limit=message_limit)
            if not messages:
                raise Exception("No chat history found for this session")

            # Debug: Log messages being processed
            logger.info(f"Processing {len(messages)} messages for session {session_id}")
            for i, msg in enumerate(messages):
                logger.info(f"Message {i+1}: {msg['role']} - {msg['content'][:200]}...")

            # Update task status
            update_extraction_task_status(
                task_id=task_id,
                status="running",
                current_step="Initializing conversation extractor...",
                current_step_num=2,
                progress=0.4
            )

            # Initialize extractor
            extractor = ConversationExtractor()

            # Update task status
            update_extraction_task_status(
                task_id=task_id,
                status="running",
                current_step=f"Extracting insights from {len(messages)} messages...",
                current_step_num=3,
                progress=0.6
            )

            # Run extraction
            result = extractor.extract_from_messages(messages)

            # Debug: Log extraction results
            logger.info(f"Extraction completed: {len(result.get('insights', []))} insights found")
            if result.get('insights'):
                for i, insight in enumerate(result['insights']):
                    logger.info(f"Insight {i+1}: {insight.get('category', 'unknown')} - {insight.get('text', '')[:100]}...")

            # Update task status
            update_extraction_task_status(
                task_id=task_id,
                status="running",
                current_step="Processing extracted insights...",
                current_step_num=4,
                progress=0.8
            )

            # Get specific insight types
            key_decisions = extractor.get_key_decisions(result['insights'])
            current_blockers = extractor.get_current_blockers(result['insights'])
            next_actions = extractor.get_next_actions(result['insights'])

            # Prepare final result
            final_result = {
                "ok": True,
                "session_id": session_id,
                "insights": result['insights'],
                "categorized": result['categorized'],
                "summary": result['summary'],
                "key_decisions": key_decisions,
                "current_blockers": current_blockers,
                "next_actions": next_actions,
                "message_count_analyzed": len(messages),
                "extraction_time": 0  # Will be calculated when task is retrieved
            }

            # Debug: Log final results
            logger.info(f"Final result: {len(result['insights'])} insights, {len(key_decisions)} key decisions, {len(current_blockers)} blockers, {len(next_actions)} next actions")

            # Update task status to completed
            update_extraction_task_status(
                task_id=task_id,
                status="completed",
                current_step="Extraction completed!",
                current_step_num=5,
                progress=1.0
            )

            # Store result in database
            save_extraction_result(task_id, final_result)

            logger.info(f"Conversation extraction task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Conversation extraction task {task_id} failed: {e}")
            # Update task status to failed
            update_extraction_task_status(
                task_id=task_id,
                status="failed",
                error=str(e)
            )

    def _run_progress_extraction(self, task_id: str, session_id: str, message_limit: int):
        """Run progress extraction in background thread."""
        try:
            # Update task status to running
            update_extraction_task_status(
                task_id=task_id,
                status="running",
                current_step="Loading chat messages...",
                current_step_num=1,
                progress=0.2
            )

            # Get messages
            messages = get_chat_messages(session_id, limit=message_limit)
            if not messages:
                raise Exception("No chat history found for this session")

            # Debug: Log messages being processed
            logger.info(f"Processing {len(messages)} messages for session {session_id}")
            for i, msg in enumerate(messages):
                logger.info(f"Message {i+1}: {msg['role']} - {msg['content'][:200]}...")

            # Update task status
            update_extraction_task_status(
                task_id=task_id,
                status="running",
                current_step="Initializing progress extractor...",
                current_step_num=2,
                progress=0.4
            )

            # Initialize extractor
            extractor = ProgressExtractor()

            # Update task status
            update_extraction_task_status(
                task_id=task_id,
                status="running",
                current_step=f"Analyzing progress from {len(messages)} messages...",
                current_step_num=3,
                progress=0.6
            )

            # Run extraction
            result = extractor.extract_from_messages(messages)

            # Debug: Log extraction results
            logger.info(f"Extraction completed: {len(result.get('progress_items', []))} progress items found")
            if result.get('progress_items'):
                for i, item in enumerate(result['progress_items']):
                    logger.info(f"Progress item {i+1}: {item.get('category', 'unknown')} - {item.get('text', '')[:100]}...")

            # Update task status
            update_extraction_task_status(
                task_id=task_id,
                status="running",
                current_step="Processing progress metrics...",
                current_step_num=4,
                progress=0.8
            )

            # Get specific progress metrics
            completion_status = extractor.get_completion_status(result['progress_items'])
            current_blockers = extractor.get_current_blockers(result['progress_items'])
            milestone_progress = extractor.get_milestone_progress(result['progress_items'])
            resource_needs = extractor.get_resource_needs(result['progress_items'])

            # Prepare final result
            final_result = {
                "ok": True,
                "session_id": session_id,
                "progress_items": result['progress_items'],
                "categorized": result['categorized'],
                "summary": result['summary'],
                "completion_status": completion_status,
                "current_blockers": current_blockers,
                "milestone_progress": milestone_progress,
                "resource_needs": resource_needs,
                "message_count_analyzed": len(messages),
                "extraction_time": 0  # Will be calculated when task is retrieved
            }

            # Debug: Log final results
            logger.info(f"Final result: {len(result['progress_items'])} progress items, {len(current_blockers)} blockers, completion rate: {result['summary'].get('completion_rate', 0)}%")

            # Update task status to completed
            update_extraction_task_status(
                task_id=task_id,
                status="completed",
                current_step="Progress analysis completed!",
                current_step_num=5,
                progress=1.0
            )

            # Store result in database
            save_extraction_result(task_id, final_result)

            logger.info(f"Progress extraction task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Progress extraction task {task_id} failed: {e}")
            # Update task status to failed
            update_extraction_task_status(
                task_id=task_id,
                status="failed",
                error=str(e)
            )

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        return get_extraction_task_by_id(task_id)

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a completed task."""
        return get_extraction_result(task_id)

    def get_session_tasks(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all tasks for a specific session."""
        return get_extraction_tasks(session_id)

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed/failed tasks."""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)

        with self._lock:
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in ["completed", "failed"] and
                    task.completed_at and
                    task.completed_at.timestamp() < cutoff_time):
                    tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del self.tasks[task_id]

            if tasks_to_remove:
                logger.info(f"Cleaned up {len(tasks_to_remove)} old extraction tasks")

# Global service instance
_extraction_service: Optional[ExtractionService] = None

def get_extraction_service() -> ExtractionService:
    """Get the global extraction service instance."""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService()
    return _extraction_service