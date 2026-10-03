"""PRESENTATION layer: FastAPI request/response schemas.

Schemas describe the API contract only. ETF metadata itself lives in
:mod:`app.universe`; these types project it for the wire.
"""

from __future__ import annotations

from app.models.universe import ETFOut, UniverseOut

__all__ = ["ETFOut", "UniverseOut"]
