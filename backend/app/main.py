"""FastAPI entrypoint.

POST /api/optimize
GET  /api/universe
GET  /api/presets
GET  /health
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.universe import router as universe_router
from app.config import Settings, get_settings, validate_for_startup

logger = logging.getLogger("blendguard")

_TEXT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_JSON_FORMAT = (
    '{"ts": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "msg": "%(message)s"}'
)


def configure_logging(settings: Settings) -> None:
    """Install root logging from configuration.

    Idempotent: repeated calls replace the root handler rather than stacking
    duplicates, which matters under ``--reload``.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(_JSON_FORMAT if settings.logging.format == "json" else _TEXT_FORMAT)
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.logging.level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Validate configuration before serving traffic.

    Raises before the first request, so a missing production credential is a
    startup failure rather than a confusing 500 later.
    """
    settings = get_settings()
    configure_logging(settings)
    validate_for_startup(settings)
    logger.info(
        "BlendGuard %s starting in %s environment (provider=%s)",
        __version__,
        settings.environment,
        settings.market_data.provider,
    )
    yield


settings = get_settings()

app = FastAPI(
    title="BlendGuard",
    version=__version__,
    description="Transparent Black-Litterman ETF portfolio optimizer.",
    lifespan=lifespan,
)

# An empty cors_origins list means no cross-origin access, which is the correct
# default for a same-origin deployment.
if settings.api.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.api.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

app.include_router(universe_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe.

    Reports environment so a deployment can confirm which profile it is running.
    Deliberately carries no configuration detail and no secrets.
    """
    return {
        "status": "ok",
        "version": __version__,
        "environment": str(settings.environment),
    }


def run() -> None:  # pragma: no cover - convenience entrypoint
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=not settings.is_production,
    )
