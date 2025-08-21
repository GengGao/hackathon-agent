"""API endpoints for background extraction operations."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import logging

from services.extraction_service import get_extraction_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/extractions/conversation/start")
def start_conversation_extraction(
    session_id: str,
    message_limit: int = 50
) -> Dict[str, Any]:
    """Start background conversation extraction."""
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    try:
        service = get_extraction_service()
        task_id = service.start_conversation_extraction(session_id, message_limit)

        return {
            "ok": True,
            "task_id": task_id,
            "message": "Conversation extraction started in background"
        }
    except Exception as e:
        logger.error(f"Failed to start conversation extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extractions/progress/start")
def start_progress_extraction(
    session_id: str,
    message_limit: int = 50
) -> Dict[str, Any]:
    """Start background progress extraction."""
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    try:
        service = get_extraction_service()
        task_id = service.start_progress_extraction(session_id, message_limit)

        return {
            "ok": True,
            "task_id": task_id,
            "message": "Progress extraction started in background"
        }
    except Exception as e:
        logger.error(f"Failed to start progress extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/extractions/task/{task_id}/status")
def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get status of a specific extraction task."""
    try:
        service = get_extraction_service()
        status = service.get_task_status(task_id)

        if not status:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "ok": True,
            "status": status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/extractions/task/{task_id}/result")
def get_task_result(task_id: str) -> Dict[str, Any]:
    """Get result of a completed extraction task."""
    try:
        service = get_extraction_service()
        result = service.get_task_result(task_id)

        if not result:
            # Check if task exists but isn't completed
            status = service.get_task_status(task_id)
            if not status:
                raise HTTPException(status_code=404, detail="Task not found")
            elif status["status"] in ["queued", "running"]:
                raise HTTPException(status_code=202, detail="Task not yet completed")
            elif status["status"] == "failed":
                raise HTTPException(status_code=500, detail=status.get("error", "Task failed"))
            else:
                raise HTTPException(status_code=404, detail="No result available")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/extractions/session/{session_id}")
def get_session_extractions(session_id: str) -> Dict[str, Any]:
    """Get all extraction tasks for a specific session."""
    try:
        service = get_extraction_service()
        tasks = service.get_session_tasks(session_id)

        return {
            "ok": True,
            "session_id": session_id,
            "tasks": tasks,
            "total_tasks": len(tasks)
        }
    except Exception as e:
        logger.error(f"Failed to get session extractions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/extractions/cleanup")
def cleanup_old_tasks(max_age_hours: int = Query(24, ge=1, le=168)) -> Dict[str, Any]:
    """Clean up old completed/failed tasks."""
    try:
        service = get_extraction_service()
        service.cleanup_old_tasks(max_age_hours)

        return {
            "ok": True,
            "message": f"Cleaned up tasks older than {max_age_hours} hours"
        }
    except Exception as e:
        logger.error(f"Failed to cleanup tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))