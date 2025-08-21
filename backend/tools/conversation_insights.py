"""Tools for extracting and using conversation insights."""

import logging
from typing import Dict, Any, List, Optional
from models.db import get_chat_messages
from extractors.conversation_extractor import ConversationExtractor
from extractors.progress_extractor import ProgressExtractor

logger = logging.getLogger(__name__)

def analyze_conversation_insights(session_id: str, message_limit: Optional[int] = 50) -> Dict[str, Any]:
    """
    Analyze conversation insights from chat history.

    Args:
        session_id: Chat session ID to analyze
        message_limit: Maximum number of recent messages to analyze

    Returns:
        Dictionary containing conversation insights and analysis
    """
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    try:
        # Get recent chat messages
        messages = get_chat_messages(session_id, limit=message_limit)
        if not messages:
            return {"ok": False, "error": "No chat history found for this session"}

        # Initialize conversation extractor
        extractor = ConversationExtractor()

        # Extract insights from messages
        result = extractor.extract_from_messages(messages)

        # Get specific insight types
        key_decisions = extractor.get_key_decisions(result['insights'])
        current_blockers = extractor.get_current_blockers(result['insights'])
        next_actions = extractor.get_next_actions(result['insights'])

        return {
            "ok": True,
            "session_id": session_id,
            "insights": result['insights'],
            "categorized": result['categorized'],
            "summary": result['summary'],
            "key_decisions": key_decisions,
            "current_blockers": current_blockers,
            "next_actions": next_actions,
            "message_count_analyzed": len(messages)
        }

    except Exception as e:
        logger.error(f"Failed to analyze conversation insights: {e}")
        return {"ok": False, "error": str(e)}

def analyze_project_progress(session_id: str, message_limit: Optional[int] = 50) -> Dict[str, Any]:
    """
    Analyze project progress from chat history.

    Args:
        session_id: Chat session ID to analyze
        message_limit: Maximum number of recent messages to analyze

    Returns:
        Dictionary containing progress analysis and metrics
    """
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    try:
        # Get recent chat messages
        messages = get_chat_messages(session_id, limit=message_limit)
        if not messages:
            return {"ok": False, "error": "No chat history found for this session"}

        # Initialize progress extractor
        extractor = ProgressExtractor()

        # Extract progress information from messages
        result = extractor.extract_from_messages(messages)

        # Get specific progress metrics
        completion_status = extractor.get_completion_status(result['progress_items'])
        current_blockers = extractor.get_current_blockers(result['progress_items'])
        milestone_progress = extractor.get_milestone_progress(result['progress_items'])
        resource_needs = extractor.get_resource_needs(result['progress_items'])

        return {
            "ok": True,
            "session_id": session_id,
            "progress_items": result['progress_items'],
            "categorized": result['categorized'],
            "summary": result['summary'],
            "completion_status": completion_status,
            "current_blockers": current_blockers,
            "milestone_progress": milestone_progress,
            "resource_needs": resource_needs,
            "message_count_analyzed": len(messages)
        }

    except Exception as e:
        logger.error(f"Failed to analyze project progress: {e}")
        return {"ok": False, "error": str(e)}

def get_conversation_summary(session_id: str, focus: Optional[str] = None) -> Dict[str, Any]:
    """
    Get a focused summary of conversation insights.

    Args:
        session_id: Chat session ID to analyze
        focus: Optional focus area ('decisions', 'blockers', 'progress', 'technologies')

    Returns:
        Dictionary containing focused conversation summary
    """
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    try:
        # Get conversation insights
        insights_result = analyze_conversation_insights(session_id)
        if not insights_result["ok"]:
            return insights_result

        # Get progress analysis
        progress_result = analyze_project_progress(session_id)
        if not progress_result["ok"]:
            return progress_result

        # Create focused summary based on request
        summary = {
            "session_id": session_id,
            "total_insights": insights_result["summary"]["total_insights"],
            "total_progress_items": progress_result["summary"]["total_progress_items"],
            "project_health": progress_result["summary"]["project_health"],
            "completion_rate": progress_result["summary"]["completion_rate"]
        }

        if focus == "decisions" or focus is None:
            summary["key_decisions"] = insights_result["key_decisions"][:5]  # Top 5
            summary["technologies_chosen"] = [
                insight for insight in insights_result["insights"]
                if insight["category"] == "technologies_chosen"
            ][:3]  # Top 3

        if focus == "blockers" or focus is None:
            summary["current_blockers"] = insights_result["current_blockers"][:3]  # Top 3
            summary["progress_blockers"] = progress_result["current_blockers"][:3]  # Top 3

        if focus == "progress" or focus is None:
            summary["completed_tasks"] = progress_result["completion_status"]["completed"][:5]  # Top 5
            summary["in_progress_tasks"] = progress_result["completion_status"]["in_progress"][:3]  # Top 3
            summary["planned_tasks"] = progress_result["completion_status"]["planned"][:3]  # Top 3

        if focus == "technologies" or focus is None:
            summary["technologies_discussed"] = [
                insight for insight in insights_result["insights"]
                if insight["category"] == "technologies_chosen"
            ]
            summary["technical_problems_solved"] = [
                insight for insight in insights_result["insights"]
                if insight["category"] == "problems_solved"
            ][:3]  # Top 3

        return {
            "ok": True,
            "focus": focus or "comprehensive",
            "summary": summary,
            "generated_at": insights_result["summary"]["extracted_at"]
        }

    except Exception as e:
        logger.error(f"Failed to generate conversation summary: {e}")
        return {"ok": False, "error": str(e)}

def get_actionable_insights(session_id: str) -> Dict[str, Any]:
    """
    Get actionable insights and recommendations from conversation analysis.

    Args:
        session_id: Chat session ID to analyze

    Returns:
        Dictionary containing actionable insights and recommendations
    """
    if not session_id:
        return {"ok": False, "error": "Session ID is required"}

    try:
        # Get both conversation and progress insights
        insights_result = analyze_conversation_insights(session_id)
        progress_result = analyze_project_progress(session_id)

        if not insights_result["ok"] or not progress_result["ok"]:
            return {"ok": False, "error": "Failed to analyze conversation or progress"}

        # Generate actionable recommendations
        recommendations = []

        # Check for unresolved blockers
        if insights_result["current_blockers"] or progress_result["current_blockers"]:
            recommendations.append({
                "type": "blocker_resolution",
                "priority": "high",
                "title": "Address Current Blockers",
                "description": "There are unresolved blockers that need attention",
                "blockers": insights_result["current_blockers"] + progress_result["current_blockers"]
            })

        # Check for resource needs
        if progress_result["resource_needs"]:
            recommendations.append({
                "type": "resource_allocation",
                "priority": "medium",
                "title": "Resource Requirements Identified",
                "description": "Team has identified resource needs",
                "needs": progress_result["resource_needs"]
            })

        # Check for next actions
        if insights_result["next_actions"]:
            recommendations.append({
                "type": "action_planning",
                "priority": "medium",
                "title": "Planned Next Steps",
                "description": "Clear next actions have been identified",
                "actions": insights_result["next_actions"]
            })

        # Check project health
        project_health = progress_result["summary"]["project_health"]
        if project_health in ["at_risk", "needs_attention"]:
            recommendations.append({
                "type": "project_health",
                "priority": "high",
                "title": f"Project Health: {project_health.replace('_', ' ').title()}",
                "description": "Project may need additional attention or resources",
                "completion_rate": progress_result["summary"]["completion_rate"],
                "health_status": project_health
            })

        return {
            "ok": True,
            "session_id": session_id,
            "recommendations": recommendations,
            "project_health": project_health,
            "completion_rate": progress_result["summary"]["completion_rate"],
            "total_insights": insights_result["summary"]["total_insights"],
            "generated_at": insights_result["summary"]["extracted_at"]
        }

    except Exception as e:
        logger.error(f"Failed to generate actionable insights: {e}")
        return {"ok": False, "error": str(e)}

__all__ = [
    "analyze_conversation_insights",
    "analyze_project_progress",
    "get_conversation_summary",
    "get_actionable_insights"
]