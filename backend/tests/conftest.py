"""Pytest fixtures.

Tests must never require a Bloomberg Terminal or network access unless marked
``integration`` or ``bloomberg`` (see docs/architecture.md).
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def tickers() -> list[str]:
    return ["VOO", "VTI", "VEA", "VWO", "HYG", "JNK", "SHY", "IEF", "TLT"]


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
def synthetic_market_data(synthetic_prices: pd.DataFrame, tickers: list[str]):
    from app.providers.base import Asset, AssetClass, MarketData

    classes = {
        "VOO": AssetClass.EQUITY,
        "VTI": AssetClass.EQUITY,
        "VEA": AssetClass.EQUITY,
        "VWO": AssetClass.EQUITY,
        "HYG": AssetClass.HIGH_YIELD,
        "JNK": AssetClass.HIGH_YIELD,
        "SHY": AssetClass.TREASURY,
        "IEF": AssetClass.TREASURY,
        "TLT": AssetClass.TREASURY,
    }
    assets = {t: Asset(ticker=t, name=f"{t} Test ETF", asset_class=classes[t]) for t in tickers}
    return MarketData(
        prices=synthetic_prices,
        assets=assets,
        market_caps=dict.fromkeys(tickers, 100000000000.0),
        as_of=date(2021, 12, 31),
    )


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
