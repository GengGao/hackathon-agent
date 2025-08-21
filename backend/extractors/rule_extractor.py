"""Rule extractor for hackathon rules using LangExtract."""

import re
import logging
from typing import List, Dict, Any, Optional

from extractors.base_extractor import BaseExtractor
from schemas.rule_schemas import HACKATHON_RULE_SCHEMA, RULE_CATEGORIES
from examples.rule_examples import RULE_EXTRACTION_EXAMPLES
from config.langextract_config import LANGEXTRACT_CONFIG

logger = logging.getLogger(__name__)

class RuleExtractor(BaseExtractor):
    """Extractor for hackathon rules with structured categorization."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the rule extractor."""
        super().__init__(config)
        self.extraction_config = {**LANGEXTRACT_CONFIG, **(config or {})}

    def extract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract structured rules using LangExtract."""
        try:
            import langextract as lx

            # Run extraction with LangExtract
            result = lx.extract(
                text_or_documents=text,
                prompt_description=HACKATHON_RULE_SCHEMA,
                examples=RULE_EXTRACTION_EXAMPLES,
                **self.extraction_config
            )

            # Convert LangExtract results to our format
            structured_chunks = []
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    chunk_data = {
                        'text': extraction.extraction_text,
                        'category': extraction.extraction_class,
                        'attributes': getattr(extraction, 'attributes', {}),
                        'source': 'langextract',
                        'confidence': getattr(extraction, 'confidence', 1.0)
                    }
                    structured_chunks.append(chunk_data)

            # If no extractions found, fall back to simple chunking
            if not structured_chunks:
                logger.info("No LangExtract extractions found, using fallback method")
                return self.extract_fallback(text, **kwargs)

            return structured_chunks

        except Exception as e:
            logger.error(f"LangExtract extraction failed: {e}")
            return self.extract_fallback(text, **kwargs)

    def _safe_extract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Thread-safe wrapper for extract method."""
        try:
            return self.extract(text, **kwargs)
        except Exception as e:
            logger.error(f"Safe extraction failed: {e}")
            return self.extract_fallback(text, **kwargs)

    def extract_fallback(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Fallback rule extraction using heuristic methods."""
        chunks = []

        # Split by blank lines (current method)
        parts = [c.strip() for c in text.split('\n\n') if c.strip()]

        for part in parts:
            # Try to identify rule category using keywords
            category = self._classify_rule_heuristic(part)

            # Extract rule number if present
            rule_number = self._extract_rule_number(part)

            chunk_data = {
                'text': part,
                'category': category,
                'attributes': {
                    'rule_number': rule_number,
                    'extraction_method': 'heuristic'
                },
                'source': 'fallback',
                'confidence': 0.7  # Lower confidence for heuristic method
            }
            chunks.append(chunk_data)

        return chunks

    def _classify_rule_heuristic(self, text: str) -> str:
        """Classify rule category using keyword matching."""
        text_lower = text.lower()

        # Define keyword patterns for each category
        category_keywords = {
            'eligibility': ['eligibility', 'eligible', 'participant', 'qualify'],
            'submission_requirements': ['submission', 'submit', 'deliverable', 'provide', 'format'],
            'judging_criteria': ['judging', 'judge', 'criteria', 'evaluation', 'scoring'],
            'deadlines': ['deadline', 'due', 'timeline', 'schedule', 'date'],
            'constraints': ['constraint', 'limitation', 'restriction', 'prohibited', 'not allowed'],
            'team_rules': ['team', 'member', 'group', 'collaboration'],
            'resources': ['resource', 'allowed', 'permitted', 'library', 'tool'],
            'demo_requirements': ['demo', 'demonstration', 'presentation', 'show']
        }

        # Score each category based on keyword matches
        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score

        # Return category with highest score, or 'general' if no matches
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        else:
            return 'general'

    def _extract_rule_number(self, text: str) -> Optional[str]:
        """Extract rule number from text using regex."""
        # Look for patterns like "Rule 1.1", "Rule 2.3", etc.
        rule_pattern = r'Rule\s+(\d+\.\d+)'
        match = re.search(rule_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Look for patterns like "1.1 –", "2.3 -", etc.
        number_pattern = r'^(\d+\.\d+)\s*[–-]'
        match = re.search(number_pattern, text)
        if match:
            return match.group(1)

        return None

    def create_semantic_chunks(self, rules_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create semantic chunks from extracted rule data."""
        semantic_chunks = []

        # Group rules by category for better semantic coherence
        category_groups = {}
        for rule in rules_data:
            category = rule.get('category', 'general')
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(rule)

        # Create chunks for each category
        for category, rules in category_groups.items():
            if len(rules) == 1:
                # Single rule becomes its own chunk
                chunk = {
                    'text': rules[0]['text'],
                    'category': category,
                    'metadata': {
                        'rule_count': 1,
                        'category': category,
                        'extraction_source': rules[0]['source'],
                        'confidence': rules[0]['confidence']
                    }
                }
                semantic_chunks.append(chunk)
            else:
                # Multiple rules in same category get combined
                combined_text = '\n\n'.join(rule['text'] for rule in rules)
                avg_confidence = sum(rule['confidence'] for rule in rules) / len(rules)

                chunk = {
                    'text': combined_text,
                    'category': category,
                    'metadata': {
                        'rule_count': len(rules),
                        'category': category,
                        'extraction_source': 'combined',
                        'confidence': avg_confidence
                    }
                }
                semantic_chunks.append(chunk)

        return semantic_chunks