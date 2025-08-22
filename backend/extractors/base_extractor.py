"""Base extractor class for structured information extraction."""

import hashlib
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """Base class for all extractors using LangExtract with caching support."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the extractor with configuration."""
        self.config = config or {}
        self.langextract_available = self._check_langextract_availability()

        # Initialize extraction cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_enabled = self.config.get('cache_enabled', True)
        self._cache_max_size = self.config.get('cache_max_size', 100)

    def _check_langextract_availability(self) -> bool:
        """Check if LangExtract is available."""
        try:
            import langextract
            return True
        except ImportError:
            logger.warning("LangExtract not available, falling back to heuristic methods")
            return False

    def _get_cache_key(self, text: str, **kwargs) -> str:
        """Generate a cache key for the given text and parameters."""
        # Create a hash of the text and sorted kwargs
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        kwargs_str = str(sorted(kwargs.items()))
        kwargs_hash = hashlib.md5(kwargs_str.encode('utf-8')).hexdigest()
        return f"{text_hash}_{kwargs_hash}"

    def _get_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached extraction result if available and not expired."""
        if not self._cache_enabled or cache_key not in self._cache:
            return None

        cached = self._cache[cache_key]
        # Simple cache expiry check (optional enhancement)
        return cached.get('result')

    def _set_cache(self, cache_key: str, result: List[Dict[str, Any]]) -> None:
        """Cache the extraction result."""
        if not self._cache_enabled:
            return

        # Manage cache size - remove oldest entries if over limit
        if len(self._cache) >= self._cache_max_size:
            # Remove oldest 10% of entries
            remove_count = max(1, int(self._cache_max_size * 0.1))
            oldest_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k].get('timestamp', 0)
            )[:remove_count]
            for key in oldest_keys:
                del self._cache[key]

        # Store result with timestamp
        import time
        self._cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }

    def _cached_extract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract with caching support."""
        if not text or not text.strip():
            return []

        cache_key = self._get_cache_key(text, **kwargs)
        cached_result = self._get_cache(cache_key)

        if cached_result is not None:
            logger.debug(f"Cache hit for extraction, returning cached result")
            return cached_result

        # Perform extraction
        result = self._safe_extract(text, **kwargs)

        # Cache the result
        self._set_cache(cache_key, result)

        return result

    def clear_cache(self) -> None:
        """Clear the extraction cache."""
        self._cache.clear()
        logger.debug("Extraction cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'enabled': self._cache_enabled,
            'size': len(self._cache),
            'max_size': self._cache_max_size,
            'cache_hit_rate': 0.0  # Could be implemented with counters
        }

    def set_cache_config(self, enabled: bool = None, max_size: int = None) -> None:
        """Update cache configuration."""
        if enabled is not None:
            self._cache_enabled = enabled
        if max_size is not None:
            self._cache_max_size = max_size
        if not enabled:
            self.clear_cache()

    @abstractmethod
    def extract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract structured information from text (with caching)."""
        pass

    @abstractmethod
    def _extract_langextract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract using LangExtract (without caching)."""
        pass

    @abstractmethod
    def extract_fallback(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Fallback extraction method when LangExtract is not available."""
        pass

    def _safe_extract(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """Safely extract with fallback to heuristic methods."""
        if self.langextract_available:
            try:
                # Call the concrete extraction method (to be implemented by subclasses)
                return self._extract_langextract(text, **kwargs)
            except Exception as e:
                logger.warning(f"LangExtract extraction failed: {e}, falling back to heuristic method")
                return self.extract_fallback(text, **kwargs)
        else:
            return self.extract_fallback(text, **kwargs)