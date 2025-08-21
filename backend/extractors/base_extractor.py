"""Base extractor class for structured information extraction."""

import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """Base class for all extractors using LangExtract."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the extractor with configuration."""
        self.config = config or {}
        self.langextract_available = self._check_langextract_availability()

    def _check_langextract_availability(self) -> bool:
        """Check if LangExtract is available."""
        try:
            import langextract
            return True
        except ImportError:
            logger.warning("LangExtract not available, falling back to heuristic methods")
            return False

    @abstractmethod
    def extract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract structured information from text."""
        pass

    @abstractmethod
    def extract_fallback(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Fallback extraction method when LangExtract is not available."""
        pass

    def _safe_extract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Safely extract with fallback to heuristic methods."""
        if self.langextract_available:
            try:
                return self.extract(text, **kwargs)
            except Exception as e:
                logger.warning(f"LangExtract extraction failed: {e}, falling back to heuristic method")
                return self.extract_fallback(text, **kwargs)
        else:
            return self.extract_fallback(text, **kwargs)