from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse

from llm import (
    check_ollama_status,
    get_current_model,
    set_model,
    get_provider,
    set_provider,
    get_provider_base_url,
)


router = APIRouter()


@router.get("/ollama/status")
async def get_ollama_status():
    """Backward-compatible endpoint: returns provider-aware status."""
    try:
        status = await check_ollama_status()
        return {
            "connected": status.get("connected", False),
            "provider": status.get("provider"),
            "base_url": status.get("base_url"),
            "model": status.get("model"),
            "available_models": status.get("available_models", []),
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "model": None,
            "available_models": [],
        }


@router.get("/ollama/model")
def get_ollama_model():
    return {"model": get_current_model(), "provider": get_provider(), "base_url": get_provider_base_url()}


@router.post("/ollama/model")
async def set_ollama_model(model: str = Form(...)):
    try:
        success = await set_model(model)
        if success:
            return {"ok": True, "model": get_current_model()}
        return JSONResponse(status_code=400, content={"error": "Invalid model"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/provider")
def get_provider_info():
    return {"provider": get_provider(), "base_url": get_provider_base_url(), "model": get_current_model()}


@router.post("/provider")
async def post_set_provider(provider: str = Form(...), base_url: str | None = Form(None)):
    """Set the LLM provider ('ollama' or 'lmstudio') and optional base_url."""
    try:
        ok = await set_provider(provider, base_url)
        if ok:
            return {"ok": True, "provider": provider, "base_url": base_url}
        return JSONResponse(status_code=400, content={"error": "Invalid provider"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


