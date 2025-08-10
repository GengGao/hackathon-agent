import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router
from models.db import init_db
from llm import initialize_models

app = FastAPI(
    title="HackathonHero",
    description="Zero‑to‑hero offline agent for hackathon idea → submission.",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# Initialize DB and models at startup
@app.on_event("startup")
async def _init_startup() -> None:
    init_db()
    await initialize_models()
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)