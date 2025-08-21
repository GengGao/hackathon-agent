"""Schema definitions for hackathon rule extraction."""

# Schema for extracting structured information from hackathon rules
HACKATHON_RULE_SCHEMA = """
Extract hackathon rules and categorize them into structured information.
Focus on identifying key rule components that participants need to understand.
Use exact text from the source for extractions - do not paraphrase.
"""

# Categories for rule classification
RULE_CATEGORIES = {
    "eligibility": "Rules about who can participate",
    "submission_requirements": "Requirements for project submissions",
    "judging_criteria": "How projects will be evaluated",
    "deadlines": "Important dates and time constraints",
    "constraints": "Technical or resource limitations",
    "team_rules": "Rules about team formation and size",
    "resources": "Allowed and prohibited resources",
    "demo_requirements": "Requirements for demonstrations"
}