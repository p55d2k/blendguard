"""Smoke tests for the DATA layer invariants.

Financial calculations get real tests here; these guard the normalized contract
that every provider must satisfy (see docs/architecture.md).
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from app.providers.base import Asset, AssetClass, MarketData
from app.providers.stub import StubProvider


def test_stub_provider_returns_requested_tickers(tickers: list[str]) -> None:
    provider = StubProvider()
    prices = provider.get_prices(tickers, date(2020, 1, 1), date(2021, 12, 31))
    assert set(prices) == set(tickers)


def test_market_data_assets_must_cover_price_columns() -> None:
    index = pd.to_datetime(["2024-01-01", "2024-01-02"])
    frame = pd.DataFrame({"VOO": [1.0, 2.0]}, index=index)
    with pytest.raises(ValueError, match="unknown tickers"):
        MarketData(prices=frame, assets={})


def test_returns_drop_first_observation(synthetic_market_data: MarketData) -> None:
    returns = synthetic_market_data.returns()
    assert len(returns) == len(synthetic_market_data.prices) - 1
    assert not returns.isna().any().any()


def test_price_series_rejects_unsorted_index() -> None:
    from app.providers.base import PriceSeries

    index = pd.to_datetime(["2024-01-02", "2024-01-01"])
    series = pd.Series([2.0, 1.0], index=index, dtype=float)
    with pytest.raises(ValueError, match="sorted ascending"):
        PriceSeries(
            ticker="VOO", start=date(2024, 1, 1), end=date(2024, 1, 2), adjusted_close=series
        )


def test_universe_matches_fixed_ticker_set() -> None:
    from app.universe import TICKERS

    assert TICKERS == ["VOO", "VTI", "VEA", "VWO", "HYG", "JNK", "SHY", "IEF", "TLT"]


def test_asset_classes_are_partitioned_by_universe() -> None:
    from app.universe import EQUITIES, HIGH_YIELD, TICKERS, TREASURIES

    groups = [EQUITIES, HIGH_YIELD, TREASURIES]
    assert len(EQUITIES) == 4
    assert len(HIGH_YIELD) == 2
    assert len(TREASURIES) == 3
    assert sorted(t for g in groups for t in g) == sorted(TICKERS)


def test_asset_dataclass_is_immutable() -> None:
    asset = Asset(ticker="VOO", name="Vanguard S&P 500 ETF", asset_class=AssetClass.EQUITY)
    with pytest.raises(AttributeError):
        asset.ticker = "VTI"  # type: ignore[misc]
