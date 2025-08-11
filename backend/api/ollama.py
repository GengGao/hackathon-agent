from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse

from llm import check_ollama_status, get_current_model, set_model


router = APIRouter()


@router.get("/ollama/status")
async def get_ollama_status():
    try:
        status = await check_ollama_status()
        return {
            "connected": status["connected"],
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
    return {"model": get_current_model()}


@router.post("/ollama/model")
async def set_ollama_model(model: str = Form(...)):
    try:
        success = await set_model(model)
        if success:
            return {"ok": True, "model": get_current_model()}
        return JSONResponse(status_code=400, content={"error": "Invalid model"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


