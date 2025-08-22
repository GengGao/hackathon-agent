"""Conversation mining extractor using LangExtract."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from extractors.base_extractor import BaseExtractor
from schemas.conversation_schemas import CONVERSATION_MINING_SCHEMA, CONVERSATION_CATEGORIES
from examples.conversation_examples import CONVERSATION_MINING_EXAMPLES
from config.langextract_config import LANGEXTRACT_CONFIG

logger = logging.getLogger(__name__)

class ConversationExtractor(BaseExtractor):
    """Extractor for mining insights from chat conversations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the conversation extractor."""
        super().__init__(config)
        self.extraction_config = {**LANGEXTRACT_CONFIG, **(config or {})}

    def extract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract conversation insights using LangExtract with caching."""
        return self._cached_extract(text, **kwargs)

    def _extract_langextract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Perform LangExtract extraction without caching."""
        try:
            import langextract as lx

            # Run extraction with LangExtract
            result = lx.extract(
                text_or_documents=text,
                prompt_description=CONVERSATION_MINING_SCHEMA,
                examples=CONVERSATION_MINING_EXAMPLES,
                **self.extraction_config
            )

            # Convert LangExtract results to our format
            insights = []
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    insight = {
                        'text': extraction.extraction_text,
                        'category': extraction.extraction_class,
                        'attributes': getattr(extraction, 'attributes', {}),
                        'source': 'langextract',
                        'confidence': getattr(extraction, 'confidence', 1.0),
                        'extracted_at': datetime.utcnow().isoformat()
                    }
                    insights.append(insight)

            # If no extractions found, fall back to heuristic analysis
            if not insights:
                logger.info("No LangExtract insights found, using fallback method")
                return self.extract_fallback(text, **kwargs)

            return insights

        except Exception as e:
            logger.error(f"LangExtract conversation extraction failed: {e}")
            return self.extract_fallback(text, **kwargs)

    def extract_fallback(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Fallback conversation analysis using heuristic methods."""
        insights = []
        text_lower = text.lower()

        # Debug: Log what we're analyzing
        logger.debug(f"Fallback analysis of text ({len(text)} chars): {text_lower[:200]}...")

        # Define keyword patterns for each category (expanded for better matching)
        category_patterns = {
            'decisions_made': [
                'decided', 'let\'s go with', 'we\'ll use', 'agreed', 'final decision',
                'settled on', 'chose', 'picked', 'selected', 'choice', 'chosen'
            ],
            'technologies_chosen': [
                'react', 'vue', 'angular', 'python', 'javascript', 'html', 'css', 'canvas',
                'fastapi', 'django', 'flask', 'nodejs', 'database', 'api', 'framework',
                'library', 'web', 'game', 'mini-game', 'offline'
            ],
            'problems_solved': [
                'fixed', 'solved', 'resolved', 'working now', 'issue resolved',
                'bug fixed', 'problem solved', 'that worked', 'works now'
            ],
            'blockers_encountered': [
                'blocked', 'stuck', 'can\'t', 'won\'t work', 'failing', 'error',
                'issue', 'problem', 'trouble', 'broken', 'challenge'
            ],
            'next_steps_planned': [
                'next', 'then', 'after', 'will work on', 'plan to', 'going to',
                'need to', 'should', 'todo', 'action item', 'step', 'implement',
                'create', 'build', 'develop', 'make', 'set up', 'add'
            ],
            'requirements_identified': [
                'requirement', 'must', 'need', 'should', 'constraint', 'rule',
                'specification', 'criteria', 'want', 'feature', 'functionality'
            ]
        }

        # Analyze text for patterns
        sentences = text.split('.')
        logger.debug(f"Analyzing {len(sentences)} sentences for patterns")

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                continue

            sentence_lower = sentence.lower()

            # Check each category
            for category, patterns in category_patterns.items():
                matches = sum(1 for pattern in patterns if pattern in sentence_lower)
                if matches > 0:
                    logger.debug(f"Found {matches} pattern matches for '{category}' in: {sentence[:100]}...")

                    insight = {
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
                    insights.append(insight)
                    break  # Only assign to first matching category

        return insights

    def extract_from_messages(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Extract insights from a list of chat messages."""
        if not messages:
            return {"insights": [], "summary": {}}

        # Combine messages into conversation text
        conversation_parts = []
        for msg in messages:
            # Handle sqlite3.Row objects
            if hasattr(msg, 'keys'):  # sqlite3.Row object
                role = msg['role'] if 'role' in msg.keys() else 'unknown'
                content = msg['content'] if 'content' in msg.keys() else ''
            else:  # Dictionary object
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')

            if content and content.strip():
                conversation_parts.append(f"{role.title()}: {content}")

        conversation_text = '\n\n'.join(conversation_parts)

        # Extract insights
        insights = self.extract(conversation_text, **kwargs)

        # Categorize insights
        categorized = {}
        for insight in insights:
            category = insight['category']
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(insight)

        # Generate summary statistics
        summary = {
            'total_insights': len(insights),
            'categories_found': list(categorized.keys()),
            'message_count': len(messages),
            'extraction_method': 'structured' if any(i['source'] == 'langextract' for i in insights) else 'heuristic',
            'extracted_at': datetime.utcnow().isoformat()
        }

        return {
            'insights': insights,
            'categorized': categorized,
            'summary': summary
        }

    def get_key_decisions(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract key decisions from insights."""
        decisions = []
        for insight in insights:
            if insight['category'] in ['decisions_made', 'technologies_chosen']:
                decisions.append({
                    'decision': insight['text'],
                    'type': insight['category'],
                    'confidence': insight['confidence'],
                    'attributes': insight.get('attributes', {}),
                    'timestamp': insight.get('extracted_at')
                })
        return sorted(decisions, key=lambda x: x['confidence'], reverse=True)

    def get_current_blockers(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract current blockers from insights."""
        blockers = []
        for insight in insights:
            if insight['category'] == 'blockers_encountered':
                blockers.append({
                    'blocker': insight['text'],
                    'confidence': insight['confidence'],
                    'attributes': insight.get('attributes', {}),
                    'timestamp': insight.get('extracted_at')
                })
        return sorted(blockers, key=lambda x: x['confidence'], reverse=True)

    def get_next_actions(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract next actions from insights."""
        actions = []
        for insight in insights:
            if insight['category'] == 'next_steps_planned':
                actions.append({
                    'action': insight['text'],
                    'confidence': insight['confidence'],
                    'attributes': insight.get('attributes', {}),
                    'timestamp': insight.get('extracted_at')
                })
        return sorted(actions, key=lambda x: x['confidence'], reverse=True)