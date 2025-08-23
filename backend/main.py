import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router
from models.db import init_db
from llm import initialize_models

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    await initialize_models()
    yield
    # Shutdown - add cleanup logic here if needed

app = FastAPI(
    title="HackathonHero",
    description="Zero‑to‑hero offline agent for hackathon idea → submission.",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware with more restrictive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)