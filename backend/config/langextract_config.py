"""Configuration for LangExtract integration."""

import os

# LangExtract configuration for local Ollama integration
LANGEXTRACT_CONFIG = {
    "model_id": "gemma2:2b",  # Use local Ollama model
    "model_url": "http://localhost:11434",
    "fence_output": False,
    "use_schema_constraints": False,
    "extraction_passes": 3,
    "max_workers": 10,
    "max_char_buffer": 1000
}

# Fallback configuration for when LangExtract is not available
FALLBACK_ENABLED = True

# Cache configuration
EXTRACTION_CACHE_ENABLED = True
EXTRACTION_SCHEMA_VERSION = 1