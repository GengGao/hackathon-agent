import uvicorn
from fastapi import FastAPI
from router import router

app = FastAPI(
    title="Local Hackathon Agent",
    description="Zero‑to‑hero offline assistant for hackathon idea → submission.",
    version="0.1.0"
)

app.include_router(router, prefix="/api")
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)