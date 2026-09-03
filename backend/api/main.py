"""Phase 5 FastAPI backend.

Run with: uv run uvicorn backend.api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger("main")

from backend.api.routes import boq, neural_render, render, segment

app = FastAPI(title="e2m-project API")
logger.info("e2m-project API starting up")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(boq.router, prefix="/api")
app.include_router(render.router, prefix="/api")
app.include_router(segment.router, prefix="/api")
app.include_router(neural_render.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
