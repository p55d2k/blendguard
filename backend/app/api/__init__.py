"""PRESENTATION layer: FastAPI routes.

Routers are thin. They project the canonical data held in :mod:`app.universe`
and :mod:`app.optimizer` onto the API contract and must contain no finance.
"""

from __future__ import annotations

from app.api.universe import router as universe_router

__all__ = ["universe_router"]
