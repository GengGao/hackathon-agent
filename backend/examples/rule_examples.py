"""Few-shot examples for hackathon rule extraction."""

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

# Few-shot examples for rule extraction
RULE_EXTRACTION_EXAMPLES = [
    lx.data.ExampleData(
        text="Rule 1.1 – Eligibility\nParticipants must adhere to the hackathon eligibility criteria as defined by the organizer.",
        extractions=[
            lx.data.Extraction(
                extraction_class="eligibility",
                extraction_text="Participants must adhere to the hackathon eligibility criteria as defined by the organizer",
                attributes={
                    "rule_number": "1.1",
                    "category": "eligibility",
                    "requirement_type": "general"
                }
            )
        ]
    ),
    lx.data.ExampleData(
        text="Rule 2.1 – Offline Demo Requirement\nAll demos must run locally without relying on cloud APIs. Allowed: Ollama, local models, local files.",
        extractions=[
            lx.data.Extraction(
                extraction_class="demo_requirements",
                extraction_text="All demos must run locally without relying on cloud APIs",
                attributes={
                    "rule_number": "2.1",
                    "category": "demo_requirements",
                    "constraint_type": "technical"
                }
            ),
            lx.data.Extraction(
                extraction_class="resources",
                extraction_text="Allowed: Ollama, local models, local files",
                attributes={
                    "rule_number": "2.1",
                    "category": "resources",
                    "resource_type": "allowed"
                }
            )
        ]
    ),
    lx.data.ExampleData(
        text="Rule 4.1 – Team Size\nTeams of up to 4 members are allowed unless specified otherwise.",
        extractions=[
            lx.data.Extraction(
                extraction_class="team_rules",
                extraction_text="Teams of up to 4 members are allowed unless specified otherwise",
                attributes={
                    "rule_number": "4.1",
                    "category": "team_rules",
                    "max_size": "4",
                    "flexibility": "conditional"
                }
            )
        ]
    )
]