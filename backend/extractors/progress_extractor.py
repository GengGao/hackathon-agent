"""Progress tracking extractor using LangExtract."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from extractors.base_extractor import BaseExtractor
from schemas.conversation_schemas import PROGRESS_TRACKING_SCHEMA, PROGRESS_CATEGORIES
from examples.conversation_examples import PROGRESS_TRACKING_EXAMPLES
from config.langextract_config import LANGEXTRACT_CONFIG

logger = logging.getLogger(__name__)

class ProgressExtractor(BaseExtractor):
    """Extractor for tracking project progress from conversations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the progress extractor."""
        super().__init__(config)
        self.extraction_config = {**LANGEXTRACT_CONFIG, **(config or {})}

    def extract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract progress information using LangExtract."""
        try:
            import langextract as lx

            # Run extraction with LangExtract
            result = lx.extract(
                text_or_documents=text,
                prompt_description=PROGRESS_TRACKING_SCHEMA,
                examples=PROGRESS_TRACKING_EXAMPLES,
                **self.extraction_config
            )

            # Convert LangExtract results to our format
            progress_items = []
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    item = {
                        'text': extraction.extraction_text,
                        'category': extraction.extraction_class,
                        'attributes': getattr(extraction, 'attributes', {}),
                        'source': 'langextract',
                        'confidence': getattr(extraction, 'confidence', 1.0),
                        'extracted_at': datetime.utcnow().isoformat()
                    }
                    progress_items.append(item)

            # If no extractions found, fall back to heuristic analysis
            if not progress_items:
                logger.info("No LangExtract progress items found, using fallback method")
                return self.extract_fallback(text, **kwargs)

            return progress_items

        except Exception as e:
            logger.error(f"LangExtract progress extraction failed: {e}")
            return self.extract_fallback(text, **kwargs)

    def extract_fallback(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Fallback progress analysis using heuristic methods."""
        progress_items = []
        text_lower = text.lower()

        # Define keyword patterns for each progress category
        progress_patterns = {
            'completed_tasks': [
                'completed', 'finished', 'done', 'ready', 'implemented', 'built',
                'created', 'deployed', 'working', 'tests passing'
            ],
            'current_blockers': [
                'blocked', 'stuck', 'can\'t', 'failing', 'broken', 'issue',
                'problem', 'error', 'not working', 'trouble'
            ],
            'in_progress_tasks': [
                'working on', 'currently', 'in progress', 'developing', 'building',
                'implementing', 'coding', 'designing'
            ],
            'planned_tasks': [
                'will', 'going to', 'plan to', 'next', 'todo', 'need to',
                'should', 'upcoming', 'scheduled'
            ],
            'milestone_updates': [
                'milestone', 'progress', 'percent', '%', 'ahead', 'behind',
                'on track', 'schedule', 'deadline'
            ],
            'resource_needs': [
                'need help', 'require', 'missing', 'lack', 'don\'t have',
                'would like', 'could use', 'assistance'
            ]
        }

        # Analyze text for progress patterns
        sentences = text.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                continue

            sentence_lower = sentence.lower()

            # Check each progress category
            for category, patterns in progress_patterns.items():
                matches = sum(1 for pattern in patterns if pattern in sentence_lower)
                if matches > 0:
                    item = {
                        'text': sentence,
                        'category': category,
                        'attributes': {
                            'extraction_method': 'heuristic',
                            'pattern_matches': matches,
                            'confidence_score': min(matches * 0.3, 1.0)
                        },
                        'source': 'fallback',
                        'confidence': min(matches * 0.3, 0.8),  # Cap fallback confidence
                        'extracted_at': datetime.utcnow().isoformat()
                    }
                    progress_items.append(item)
                    break  # Only assign to first matching category

        return progress_items

    def extract_from_messages(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Extract progress information from a list of chat messages."""
        if not messages:
            return {"progress_items": [], "summary": {}}

        # Combine messages into conversation text
        conversation_parts = []
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if content and content.strip():
                conversation_parts.append(f"{role.title()}: {content}")

        conversation_text = '\n\n'.join(conversation_parts)

        # Extract progress items
        progress_items = self.extract(conversation_text, **kwargs)

        # Categorize progress items
        categorized = {}
        for item in progress_items:
            category = item['category']
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(item)

        # Generate progress summary
        summary = self._generate_progress_summary(categorized, len(messages))

        return {
            'progress_items': progress_items,
            'categorized': categorized,
            'summary': summary
        }

    def _generate_progress_summary(self, categorized: Dict[str, List], message_count: int) -> Dict[str, Any]:
        """Generate a summary of project progress."""
        completed_count = len(categorized.get('completed_tasks', []))
        blocker_count = len(categorized.get('current_blockers', []))
        in_progress_count = len(categorized.get('in_progress_tasks', []))
        planned_count = len(categorized.get('planned_tasks', []))

        # Calculate progress indicators
        total_tasks = completed_count + in_progress_count + planned_count
        completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0

        # Determine project health
        health = "good"
        if blocker_count > completed_count:
            health = "at_risk"
        elif blocker_count > 0 and completion_rate < 50:
            health = "needs_attention"
        elif completion_rate > 80:
            health = "excellent"

        return {
            'total_progress_items': sum(len(items) for items in categorized.values()),
            'completed_tasks': completed_count,
            'current_blockers': blocker_count,
            'in_progress_tasks': in_progress_count,
            'planned_tasks': planned_count,
            'completion_rate': round(completion_rate, 1),
            'project_health': health,
            'categories_found': list(categorized.keys()),
            'message_count': message_count,
            'extracted_at': datetime.utcnow().isoformat()
        }

    def get_completion_status(self, progress_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get current completion status from progress items."""
        completed = [item for item in progress_items if item['category'] == 'completed_tasks']
        in_progress = [item for item in progress_items if item['category'] == 'in_progress_tasks']
        planned = [item for item in progress_items if item['category'] == 'planned_tasks']

        return {
            'completed': sorted(completed, key=lambda x: x['confidence'], reverse=True),
            'in_progress': sorted(in_progress, key=lambda x: x['confidence'], reverse=True),
            'planned': sorted(planned, key=lambda x: x['confidence'], reverse=True),
            'total_tasks': len(completed) + len(in_progress) + len(planned)
        }

    def get_current_blockers(self, progress_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get current blockers from progress items."""
        blockers = [item for item in progress_items if item['category'] == 'current_blockers']
        return sorted(blockers, key=lambda x: x['confidence'], reverse=True)

    def get_milestone_progress(self, progress_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get milestone progress from progress items."""
        milestones = [item for item in progress_items if item['category'] == 'milestone_updates']
        return sorted(milestones, key=lambda x: x['confidence'], reverse=True)

    def get_resource_needs(self, progress_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get resource needs from progress items."""
        needs = [item for item in progress_items if item['category'] == 'resource_needs']
        return sorted(needs, key=lambda x: x['confidence'], reverse=True)