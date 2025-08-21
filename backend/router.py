from fastapi import APIRouter

# Re-export generate_stream symbol so tests monkeypatch it via `import router as router_module`
from llm import generate_stream as generate_stream  # noqa: F401

# Compose modular sub-routers
from api import (
    chat_router,
    context_router,
    todos_router,
    sessions_router,
    ollama_router,
    artifacts_router,
    export_router,
)
from api.extractions import router as extractions_router


router = APIRouter()

# main.py applies `/api` prefix; keep original paths identical by mounting at root
router.include_router(chat_router)
router.include_router(context_router)
router.include_router(todos_router)
router.include_router(sessions_router)
router.include_router(ollama_router)
router.include_router(artifacts_router)
router.include_router(export_router)
router.include_router(extractions_router)


