"""FastAPI entrypoint.

    uvicorn app.main:app --reload

Serves the API at http://localhost:8000 and the frontend dashboard as
static files at http://localhost:8000/ (see frontend/index.html).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes.pipeline import router as pipeline_router

app = FastAPI(title="Parley — Verified Agentic Supply Chain")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a hackathon demo; tighten if it matters later
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router, tags=["pipeline"])


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


# Serve the dashboard from /frontend at the root path.
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
