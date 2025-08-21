"""LLM-callable tools for conversation and progress insights."""

import json
from typing import Dict, Any
from tools.conversation_insights import (
    analyze_conversation_insights,
    analyze_project_progress,
    get_conversation_summary,
    get_actionable_insights
)
from services.extraction_service import get_extraction_service

def get_conversation_insights(session_id: str, message_limit: int = 50, async_mode: bool = True) -> str:
    """
    Analyze conversation insights from chat history.

    This tool extracts key insights from the conversation including:
    - Important decisions made by the team
    - Technologies and tools chosen
    - Problems that were solved
    - Current blockers and obstacles
    - Next steps and action items

    Args:
        session_id: The chat session ID to analyze
        message_limit: Maximum number of recent messages to analyze (default: 50)
        async_mode: Whether to run extraction in background (default: True)

    Returns:
        JSON string containing conversation insights and analysis or task info if async
    """
    if async_mode:
        # Start background extraction
        service = get_extraction_service()
        task_id = service.start_conversation_extraction(session_id, message_limit)

        result = {
            "ok": True,
            "async": True,
            "task_id": task_id,
            "message": "Conversation extraction started in background. Use get_extraction_status to check progress.",
            "session_id": session_id
        }
        return json.dumps(result, indent=2)
    else:
        # Run synchronously (original behavior)
        result = analyze_conversation_insights(session_id, message_limit)
        return json.dumps(result, indent=2)

def get_project_progress(session_id: str, message_limit: int = 50) -> str:
    """
    Analyze project progress from chat history.

    This tool tracks project progress including:
    - Completed tasks and achievements
    - Current blockers and obstacles
    - Tasks in progress
    - Planned future work
    - Milestone progress and timeline updates
    - Resource needs and requirements

    Args:
        session_id: The chat session ID to analyze
        message_limit: Maximum number of recent messages to analyze (default: 50)

    Returns:
        JSON string containing progress analysis and metrics
    """
    result = analyze_project_progress(session_id, message_limit)
    return json.dumps(result, indent=2)

def get_focused_summary(session_id: str, focus: str = "comprehensive") -> str:
    """
    Get a focused summary of conversation insights.

    This tool provides targeted summaries based on specific focus areas:
    - "decisions": Key decisions and technology choices
    - "blockers": Current obstacles and challenges
    - "progress": Task completion and project status
    - "technologies": Technical discussions and solutions
    - "comprehensive": All areas combined (default)

    Args:
        session_id: The chat session ID to analyze
        focus: Focus area for the summary (decisions|blockers|progress|technologies|comprehensive)

    Returns:
        JSON string containing focused conversation summary
    """
    result = get_conversation_summary(session_id, focus if focus != "comprehensive" else None)
    return json.dumps(result, indent=2)

def get_actionable_recommendations(session_id: str) -> str:
    """
    Get actionable insights and recommendations from conversation analysis.

    This tool analyzes the conversation and progress to provide:
    - High-priority recommendations for addressing blockers
    - Resource allocation suggestions
    - Action planning based on identified next steps
    - Project health assessment and warnings
    - Prioritized list of items needing attention

    Args:
        session_id: The chat session ID to analyze

    Returns:
        JSON string containing actionable insights and recommendations
    """
    result = get_actionable_insights(session_id)
    return json.dumps(result, indent=2)

def analyze_team_decisions(session_id: str) -> str:
    """
    Extract and analyze key decisions made by the team.

    This tool focuses specifically on decision-making patterns:
    - Technology and framework choices
    - Architecture and design decisions
    - Process and workflow decisions
    - Resource allocation decisions
    - Timeline and scope decisions

    Args:
        session_id: The chat session ID to analyze

    Returns:
        JSON string containing decision analysis
    """
    insights_result = analyze_conversation_insights(session_id)

    if not insights_result["ok"]:
        return json.dumps(insights_result, indent=2)

    # Focus on decision-related insights
    decisions = insights_result["key_decisions"]
    tech_choices = [
        insight for insight in insights_result["insights"]
        if insight["category"] == "technologies_chosen"
    ]

    decision_analysis = {
        "ok": True,
        "session_id": session_id,
        "total_decisions": len(decisions),
        "technology_decisions": len(tech_choices),
        "key_decisions": decisions,
        "technology_choices": tech_choices,
        "decision_confidence": sum(d["confidence"] for d in decisions) / len(decisions) if decisions else 0,
        "analysis_summary": {
            "decision_making_activity": "high" if len(decisions) > 5 else "moderate" if len(decisions) > 2 else "low",
            "technology_focus": "high" if len(tech_choices) > 3 else "moderate" if len(tech_choices) > 1 else "low",
            "decision_quality": "high" if (sum(d["confidence"] for d in decisions) / len(decisions) if decisions else 0) > 0.7 else "moderate"
        }
    }

    return json.dumps(decision_analysis, indent=2)

def track_problem_resolution(session_id: str) -> str:
    """
    Track problems encountered and their resolution status.

    This tool analyzes problem-solving patterns:
    - Problems and blockers encountered
    - Solutions that were implemented
    - Resolution success rate
    - Recurring issues
    - Problem categories and types

    Args:
        session_id: The chat session ID to analyze

    Returns:
        JSON string containing problem resolution analysis
    """
    insights_result = analyze_conversation_insights(session_id)

    if not insights_result["ok"]:
        return json.dumps(insights_result, indent=2)

    # Focus on problem-related insights
    problems_solved = [
        insight for insight in insights_result["insights"]
        if insight["category"] == "problems_solved"
    ]
    current_blockers = insights_result["current_blockers"]

    resolution_analysis = {
        "ok": True,
        "session_id": session_id,
        "problems_solved": len(problems_solved),
        "current_blockers": len(current_blockers),
        "solved_problems": problems_solved,
        "active_blockers": current_blockers,
        "resolution_rate": len(problems_solved) / (len(problems_solved) + len(current_blockers)) * 100 if (problems_solved or current_blockers) else 0,
        "problem_solving_summary": {
            "resolution_effectiveness": "high" if len(problems_solved) > len(current_blockers) else "moderate" if len(problems_solved) == len(current_blockers) else "needs_improvement",
            "blocker_severity": "high" if len(current_blockers) > 3 else "moderate" if len(current_blockers) > 1 else "low",
            "problem_solving_activity": "high" if len(problems_solved) > 5 else "moderate" if len(problems_solved) > 2 else "low"
        }
    }

    return json.dumps(resolution_analysis, indent=2)

def get_extraction_status(task_id: str) -> str:
    """
    Get the status of a background extraction task.

    This tool checks the progress of conversation or progress extraction tasks
    that are running in the background.

    Args:
        task_id: The task ID returned from starting an extraction

    Returns:
        JSON string containing task status and progress information
    """
    service = get_extraction_service()
    status = service.get_task_status(task_id)

    if not status:
        result = {
            "ok": False,
            "error": "Task not found",
            "task_id": task_id
        }
    else:
        result = {
            "ok": True,
            "task_id": task_id,
            "status": status
        }

    return json.dumps(result, indent=2)

def get_extraction_result(task_id: str) -> str:
    """
    Get the result of a completed extraction task.

    This tool retrieves the final results from a background extraction task
    that has completed successfully.

    Args:
        task_id: The task ID of the completed extraction

    Returns:
        JSON string containing extraction results or error if not ready
    """
    service = get_extraction_service()
    result = service.get_task_result(task_id)

    if not result:
        # Check task status to provide better error message
        status = service.get_task_status(task_id)
        if not status:
            error_result = {
                "ok": False,
                "error": "Task not found",
                "task_id": task_id
            }
        elif status["status"] in ["queued", "running"]:
            error_result = {
                "ok": False,
                "error": "Task not yet completed",
                "task_id": task_id,
                "current_status": status["status"],
                "progress": status["progress"]
            }
        elif status["status"] == "failed":
            error_result = {
                "ok": False,
                "error": f"Task failed: {status.get('error', 'Unknown error')}",
                "task_id": task_id
            }
        else:
            error_result = {
                "ok": False,
                "error": "No result available",
                "task_id": task_id
            }
        return json.dumps(error_result, indent=2)

    return json.dumps(result, indent=2)

def list_session_extractions(session_id: str) -> str:
    """
    List all extraction tasks for a specific session.

    This tool shows all background extraction tasks (conversation and progress)
    that have been started for a particular chat session.

    Args:
        session_id: The chat session ID to check

    Returns:
        JSON string containing list of extraction tasks and their status
    """
    service = get_extraction_service()
    tasks = service.get_session_tasks(session_id)

    result = {
        "ok": True,
        "session_id": session_id,
        "tasks": tasks,
        "total_tasks": len(tasks),
        "active_tasks": len([t for t in tasks if t["status"] in ["queued", "running"]]),
        "completed_tasks": len([t for t in tasks if t["status"] == "completed"]),
        "failed_tasks": len([t for t in tasks if t["status"] == "failed"])
    }

    return json.dumps(result, indent=2)

__all__ = [
    "get_conversation_insights",
    "get_project_progress",
    "get_focused_summary",
    "get_actionable_recommendations",
    "analyze_team_decisions",
    "track_problem_resolution",
    "get_extraction_status",
    "get_extraction_result",
    "list_session_extractions"
]