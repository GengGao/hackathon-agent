"""Few-shot examples for conversation mining extraction."""

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False
    # Create mock classes for when LangExtract is not available
    class MockExampleData:
        def __init__(self, text, extractions):
            self.text = text
            self.extractions = extractions

    class MockExtraction:
        def __init__(self, extraction_class, extraction_text, attributes):
            self.extraction_class = extraction_class
            self.extraction_text = extraction_text
            self.attributes = attributes

    lx = type('MockLX', (), {
        'data': type('MockData', (), {
            'ExampleData': MockExampleData,
            'Extraction': MockExtraction
        })()
    })()

# Few-shot examples for conversation mining
CONVERSATION_MINING_EXAMPLES = [
    lx.data.ExampleData(
        text="User: I think we should use React for the frontend and FastAPI for the backend. Assistant: That's a great choice! React will give you a modern UI and FastAPI is perfect for rapid API development. User: Agreed, let's go with that stack.",
        extractions=[
            lx.data.Extraction(
                extraction_class="technologies_chosen",
                extraction_text="we should use React for the frontend and FastAPI for the backend",
                attributes={
                    "technologies": ["React", "FastAPI"],
                    "decision_context": "frontend and backend technology selection",
                    "confidence": "high",
                    "participants": ["user", "assistant"]
                }
            ),
            lx.data.Extraction(
                extraction_class="decisions_made",
                extraction_text="let's go with that stack",
                attributes={
                    "decision_type": "technology_stack",
                    "finality": "confirmed",
                    "reasoning": "modern UI and rapid API development"
                }
            )
        ]
    ),
    lx.data.ExampleData(
        text="User: We're having trouble with the authentication system. The JWT tokens keep expiring too quickly. Assistant: You can adjust the token expiration time in your JWT configuration. Try setting it to 24 hours instead of 1 hour. User: That worked! Authentication is now stable.",
        extractions=[
            lx.data.Extraction(
                extraction_class="problems_solved",
                extraction_text="JWT tokens keep expiring too quickly",
                attributes={
                    "problem_type": "authentication",
                    "solution": "adjust token expiration time to 24 hours",
                    "status": "resolved",
                    "impact": "authentication stability"
                }
            ),
            lx.data.Extraction(
                extraction_class="blockers_encountered",
                extraction_text="having trouble with the authentication system",
                attributes={
                    "blocker_type": "technical",
                    "component": "authentication",
                    "resolution_time": "immediate"
                }
            )
        ]
    ),
    lx.data.ExampleData(
        text="User: For the hackathon, we need to make sure our demo runs completely offline. No external API calls allowed. Assistant: Good point! We should use local models like Ollama and store all data locally. User: Right, and we need to have a backup plan if the internet goes down during the demo.",
        extractions=[
            lx.data.Extraction(
                extraction_class="requirements_identified",
                extraction_text="demo runs completely offline. No external API calls allowed",
                attributes={
                    "requirement_type": "technical_constraint",
                    "scope": "demo",
                    "criticality": "mandatory",
                    "source": "hackathon_rules"
                }
            ),
            lx.data.Extraction(
                extraction_class="next_steps_planned",
                extraction_text="need to have a backup plan if the internet goes down during the demo",
                attributes={
                    "action_type": "contingency_planning",
                    "priority": "high",
                    "timeline": "before_demo"
                }
            )
        ]
    )
]

# Few-shot examples for progress tracking
PROGRESS_TRACKING_EXAMPLES = [
    lx.data.ExampleData(
        text="User: I finished implementing the user authentication system. All tests are passing and it's ready for integration. Next, I'll work on the dashboard UI.",
        extractions=[
            lx.data.Extraction(
                extraction_class="completed_tasks",
                extraction_text="finished implementing the user authentication system. All tests are passing",
                attributes={
                    "task": "user authentication system",
                    "completion_status": "fully_complete",
                    "quality_indicator": "all tests passing",
                    "ready_for": "integration"
                }
            ),
            lx.data.Extraction(
                extraction_class="planned_tasks",
                extraction_text="Next, I'll work on the dashboard UI",
                attributes={
                    "task": "dashboard UI",
                    "priority": "next",
                    "assignee": "current_user",
                    "dependency": "authentication_complete"
                }
            )
        ]
    ),
    lx.data.ExampleData(
        text="User: We're blocked on the database integration because the schema migration is failing. The foreign key constraints are causing issues. We might need to redesign the data model.",
        extractions=[
            lx.data.Extraction(
                extraction_class="current_blockers",
                extraction_text="blocked on the database integration because the schema migration is failing",
                attributes={
                    "blocker_type": "technical",
                    "component": "database",
                    "root_cause": "foreign key constraints",
                    "severity": "high",
                    "impact": "integration_blocked"
                }
            ),
            lx.data.Extraction(
                extraction_class="risk_factors",
                extraction_text="might need to redesign the data model",
                attributes={
                    "risk_type": "scope_change",
                    "potential_impact": "significant_rework",
                    "mitigation_needed": "data_model_review"
                }
            )
        ]
    ),
    lx.data.ExampleData(
        text="User: Great news! We're ahead of schedule. The MVP is 80% complete and we still have 3 days left. We can now focus on polishing the UI and adding some nice-to-have features.",
        extractions=[
            lx.data.Extraction(
                extraction_class="milestone_updates",
                extraction_text="MVP is 80% complete and we still have 3 days left",
                attributes={
                    "milestone": "MVP",
                    "completion_percentage": 80,
                    "time_remaining": "3 days",
                    "status": "ahead_of_schedule"
                }
            ),
            lx.data.Extraction(
                extraction_class="planned_tasks",
                extraction_text="focus on polishing the UI and adding some nice-to-have features",
                attributes={
                    "task_type": "enhancement",
                    "priority": "nice_to_have",
                    "focus_areas": ["UI polish", "additional features"],
                    "enabled_by": "ahead_of_schedule"
                }
            )
        ]
    )
]