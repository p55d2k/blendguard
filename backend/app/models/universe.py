"""PRESENTATION layer: request/response schemas for the ETF universe."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.taxonomy import AssetClass, Exposure, Region, Role
from app.universe import ETF, TICKERS, UNIVERSE, supported_tickers, tickers_by_asset_class


class ETFOut(BaseModel):
    """One universe entry as the UI sees it."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    name: str
    asset_class: AssetClass
    region: Region
    role: Role
    exposure: Exposure
    description: str
    supported: bool


class UniverseOut(BaseModel):
    """The whole canonical universe.

    The UI enumerates from this payload instead of maintaining its own ticker
    list. Ordering is stable and matches the canonical table.
    """

    model_config = ConfigDict(frozen=True)

    tickers: list[str]
    supported_tickers: list[str]
    etfs: list[ETFOut]
    by_asset_class: dict[AssetClass, list[str]]
    by_region: dict[Region, list[str]]
    asset_class_counts: dict[AssetClass, int]
    region_counts: dict[Region, int]


def to_out(etf: ETF) -> ETFOut:
    return ETFOut(
        ticker=etf.ticker,
        name=etf.name,
        asset_class=etf.asset_class,
        region=etf.region,
        role=etf.role,
        exposure=etf.exposure,
        description=etf.description,
        supported=etf.supported,
    )


def universe_payload() -> UniverseOut:
    """Build the API payload straight from the canonical table."""
    by_class = tickers_by_asset_class()
    by_region: dict[Region, list[str]] = {r: [] for r in Region}
    for etf in UNIVERSE.values():
        by_region[etf.region].append(etf.ticker)

    return UniverseOut(
        tickers=list(TICKERS),
        supported_tickers=supported_tickers(),
        etfs=[to_out(etf) for etf in UNIVERSE.values()],
        by_asset_class=by_class,
        by_region=by_region,
        asset_class_counts={ac: len(ts) for ac, ts in by_class.items()},
        region_counts={r: len(ts) for r, ts in by_region.items()},
    )
