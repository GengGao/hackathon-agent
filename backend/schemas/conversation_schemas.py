"""Schema definitions for conversation mining extraction."""

# Schema for extracting structured information from chat conversations
CONVERSATION_MINING_SCHEMA = """
Extract key insights from hackathon team conversations and chat history.
Focus on identifying decisions made, technologies chosen, problems solved, and requirements identified.
Use exact text from the conversation for extractions - do not paraphrase.
Capture the context and reasoning behind decisions.
"""

# Categories for conversation classification
CONVERSATION_CATEGORIES = {
    "decisions_made": "Important decisions made by the team",
    "technologies_chosen": "Technologies, frameworks, or tools selected",
    "problems_solved": "Technical problems that were resolved",
    "requirements_identified": "Project requirements that were discovered or clarified",
    "blockers_encountered": "Obstacles or challenges that blocked progress",
    "next_steps_planned": "Action items or next steps that were planned",
    "ideas_generated": "Creative ideas or solutions that were proposed",
    "resources_found": "Useful resources, links, or references discovered"
}

# Progress tracking schema
PROGRESS_TRACKING_SCHEMA = """
Extract project progress information from conversations and updates.
Focus on completed tasks, current blockers, timeline updates, and milestone progress.
Use exact text for progress updates - maintain original context.
Track both positive progress and obstacles.
"""

# Categories for progress classification
PROGRESS_CATEGORIES = {
    "completed_tasks": "Tasks or features that have been completed",
    "current_blockers": "Current obstacles preventing progress",
    "in_progress_tasks": "Tasks currently being worked on",
    "planned_tasks": "Tasks planned for future work",
    "milestone_updates": "Progress updates on major milestones",
    "timeline_changes": "Changes to project timeline or deadlines",
    "resource_needs": "Additional resources or help needed",
    "risk_factors": "Potential risks or concerns identified"
}