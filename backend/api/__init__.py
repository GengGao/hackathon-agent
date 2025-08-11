from fastapi import APIRouter

# Subrouters are imported and re-exported for convenience
from .chat import router as chat_router  # noqa: F401
from .context import router as context_router  # noqa: F401
from .todos import router as todos_router  # noqa: F401
from .sessions import router as sessions_router  # noqa: F401
from .ollama import router as ollama_router  # noqa: F401
from .artifacts import router as artifacts_router  # noqa: F401

__all__ = [
    "APIRouter",
    "chat_router",
    "context_router",
    "todos_router",
    "sessions_router",
    "ollama_router",
    "artifacts_router",
]


