"""FastAPI entrypoint.

POST /api/optimize
GET  /api/universe
GET  /api/presets
GET  /health
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.universe import router as universe_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="BlendGuard",
    version=__version__,
    description="Transparent Black-Litterman ETF portfolio optimizer.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(universe_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


def run() -> None:  # pragma: no cover - convenience entrypoint
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
