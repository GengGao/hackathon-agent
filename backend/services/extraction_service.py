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
from models.db import get_chat_messages

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

        with self._lock:
            task = ExtractionTask(
                task_id=task_id,
                session_id=session_id,
                task_type="conversation",
                extractor_type="ConversationExtractor",
                message_limit=message_limit
            )
            self.tasks[task_id] = task

        # Submit to thread pool
        self.executor.submit(self._run_conversation_extraction, task)

        logger.info(f"Started conversation extraction task {task_id} for session {session_id}")
        return task_id

    def start_progress_extraction(self, session_id: str, message_limit: int = 50) -> str:
        """Start background progress extraction."""
        task_id = str(uuid.uuid4())

        with self._lock:
            task = ExtractionTask(
                task_id=task_id,
                session_id=session_id,
                task_type="progress",
                extractor_type="ProgressExtractor",
                message_limit=message_limit
            )
            self.tasks[task_id] = task

        # Submit to thread pool
        self.executor.submit(self._run_progress_extraction, task)

        logger.info(f"Started progress extraction task {task_id} for session {session_id}")
        return task_id

    def _run_conversation_extraction(self, task: ExtractionTask):
        """Run conversation extraction in background thread."""
        try:
            with self._lock:
                task.status = "running"
                task.started_at = datetime.utcnow()
                task.current_step = "Loading chat messages..."
                task.current_step_num = 1
                task.progress = 0.2

            # Get messages
            messages = get_chat_messages(task.session_id, limit=task.message_limit)
            if not messages:
                raise Exception("No chat history found for this session")

            with self._lock:
                task.current_step = "Initializing conversation extractor..."
                task.current_step_num = 2
                task.progress = 0.4

            # Initialize extractor
            extractor = ConversationExtractor()

            with self._lock:
                task.current_step = f"Extracting insights from {len(messages)} messages..."
                task.current_step_num = 3
                task.progress = 0.6

            # Run extraction
            result = extractor.extract_from_messages(messages)

            with self._lock:
                task.current_step = "Processing extracted insights..."
                task.current_step_num = 4
                task.progress = 0.8

            # Get specific insight types
            key_decisions = extractor.get_key_decisions(result['insights'])
            current_blockers = extractor.get_current_blockers(result['insights'])
            next_actions = extractor.get_next_actions(result['insights'])

            # Prepare final result
            final_result = {
                "ok": True,
                "session_id": task.session_id,
                "insights": result['insights'],
                "categorized": result['categorized'],
                "summary": result['summary'],
                "key_decisions": key_decisions,
                "current_blockers": current_blockers,
                "next_actions": next_actions,
                "message_count_analyzed": len(messages),
                "extraction_time": time.time() - task.started_at.timestamp()
            }

            with self._lock:
                task.current_step = "Extraction completed!"
                task.current_step_num = 5
                task.progress = 1.0
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                task.result = final_result

            logger.info(f"Conversation extraction task {task.task_id} completed successfully")

        except Exception as e:
            logger.error(f"Conversation extraction task {task.task_id} failed: {e}")
            with self._lock:
                task.status = "failed"
                task.error = str(e)
                task.completed_at = datetime.utcnow()

    def _run_progress_extraction(self, task: ExtractionTask):
        """Run progress extraction in background thread."""
        try:
            with self._lock:
                task.status = "running"
                task.started_at = datetime.utcnow()
                task.current_step = "Loading chat messages..."
                task.current_step_num = 1
                task.progress = 0.2

            # Get messages
            messages = get_chat_messages(task.session_id, limit=task.message_limit)
            if not messages:
                raise Exception("No chat history found for this session")

            with self._lock:
                task.current_step = "Initializing progress extractor..."
                task.current_step_num = 2
                task.progress = 0.4

            # Initialize extractor
            extractor = ProgressExtractor()

            with self._lock:
                task.current_step = f"Analyzing progress from {len(messages)} messages..."
                task.current_step_num = 3
                task.progress = 0.6

            # Run extraction
            result = extractor.extract_from_messages(messages)

            with self._lock:
                task.current_step = "Processing progress metrics..."
                task.current_step_num = 4
                task.progress = 0.8

            # Get specific progress metrics
            completion_status = extractor.get_completion_status(result['progress_items'])
            current_blockers = extractor.get_current_blockers(result['progress_items'])
            milestone_progress = extractor.get_milestone_progress(result['progress_items'])
            resource_needs = extractor.get_resource_needs(result['progress_items'])

            # Prepare final result
            final_result = {
                "ok": True,
                "session_id": task.session_id,
                "progress_items": result['progress_items'],
                "categorized": result['categorized'],
                "summary": result['summary'],
                "completion_status": completion_status,
                "current_blockers": current_blockers,
                "milestone_progress": milestone_progress,
                "resource_needs": resource_needs,
                "message_count_analyzed": len(messages),
                "extraction_time": time.time() - task.started_at.timestamp()
            }

            with self._lock:
                task.current_step = "Progress analysis completed!"
                task.current_step_num = 5
                task.progress = 1.0
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                task.result = final_result

            logger.info(f"Progress extraction task {task.task_id} completed successfully")

        except Exception as e:
            logger.error(f"Progress extraction task {task.task_id} failed: {e}")
            with self._lock:
                task.status = "failed"
                task.error = str(e)
                task.completed_at = datetime.utcnow()

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return None

            return {
                "task_id": task.task_id,
                "session_id": task.session_id,
                "task_type": task.task_type,
                "extractor_type": task.extractor_type,
                "status": task.status,
                "progress": task.progress,
                "current_step": task.current_step,
                "current_step_num": task.current_step_num,
                "total_steps": task.total_steps,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error": task.error,
                "has_result": task.result is not None
            }

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a completed task."""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task or task.status != "completed":
                return None
            return task.result

    def get_session_tasks(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all tasks for a specific session."""
        with self._lock:
            session_tasks = []
            for task in self.tasks.values():
                if task.session_id == session_id:
                    session_tasks.append(self.get_task_status(task.task_id))

            # Sort by creation time, newest first
            session_tasks.sort(key=lambda x: x['created_at'], reverse=True)
            return session_tasks

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