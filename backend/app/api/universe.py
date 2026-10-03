"""PRESENTATION layer: universe routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.universe import UniverseOut, universe_payload

router = APIRouter(tags=["universe"])


@router.get("/api/universe", response_model=UniverseOut, summary="Canonical ETF universe")
def get_universe() -> UniverseOut:
    """Return the canonical ETF universe.

    Single source of truth for the UI. No ticker list is hardcoded client-side.
    """
    return universe_payload()
