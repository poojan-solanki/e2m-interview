"""Phase 5 FastAPI backend.

Run with: uv run uvicorn backend.api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import boq, render

app = FastAPI(title="e2m-project API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(boq.router, prefix="/api")
app.include_router(render.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
