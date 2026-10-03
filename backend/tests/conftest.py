"""Pytest fixtures.

Tests must never require a Bloomberg Terminal or network access unless marked
``integration`` or ``bloomberg`` (see docs/architecture.md).
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.providers.base import MarketData
from app.taxonomy import AssetClass, Region
from app.universe import TICKERS, UNIVERSE


@pytest.fixture
def tickers() -> list[str]:
    """The full canonical universe."""
    return list(TICKERS)


@pytest.fixture
def synthetic_prices(tickers: list[str]) -> pd.DataFrame:
    """Deterministic synthetic end-of-day closes with no look-ahead."""
    rng = np.random.default_rng(42)
    index = pd.bdate_range("2020-01-01", periods=500)
    data = {}
    for i, t in enumerate(tickers):
        drift = 0.0004 - 0.00005 * i
        vol = 0.010 + 0.0006 * (i % 3)
        shocks = rng.normal(drift, vol, index.size)
        data[t] = 100.0 * np.exp(np.cumsum(shocks))
    return pd.DataFrame(data, index=index)


@pytest.fixture
def synthetic_market_data(synthetic_prices: pd.DataFrame, tickers: list[str]) -> MarketData:
    """Market data for the canonical universe, using canonical reference data.

    Reference data comes from the universe so fixtures cannot drift from what
    the API and the model report.
    """
    assets = {t: UNIVERSE[t].to_asset() for t in tickers}
    return MarketData(
        prices=synthetic_prices,
        assets=assets,
        market_caps=dict.fromkeys(tickers, 100000000000.0),
        as_of=date(2021, 12, 31),
    )


@pytest.fixture
def equity_tickers() -> list[str]:
    return [t for t in TICKERS if UNIVERSE[t].asset_class is AssetClass.EQUITY]


@pytest.fixture
def treasury_tickers() -> list[str]:
    return [t for t in TICKERS if UNIVERSE[t].region is Region.US and UNIVERSE[t].is_treasury]


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
