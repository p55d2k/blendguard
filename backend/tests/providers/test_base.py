"""DATA layer invariants.

Financial calculations get real tests elsewhere; these guard the normalized
contract every provider must satisfy (see docs/architecture.md).
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from app.providers.base import Asset, MarketData, PriceSeries
from app.providers.stub import StubProvider
from app.taxonomy import AssetClass
from app.universe import UNIVERSE, UnsupportedTickerError


def test_stub_provider_returns_requested_tickers(tickers: list[str]) -> None:
    provider = StubProvider()
    prices = provider.get_prices(tickers, date(2020, 1, 1), date(2021, 12, 31))
    assert set(prices) == set(tickers)


def test_stub_provider_reference_data_comes_from_the_canonical_universe(
    tickers: list[str],
) -> None:
    assets = StubProvider().get_reference_data(tickers)
    assert assets == {t: UNIVERSE[t].to_asset() for t in tickers}


def test_stub_provider_rejects_unsupported_tickers_in_prices() -> None:
    with pytest.raises(UnsupportedTickerError):
        StubProvider().get_prices(["QQQ"], date(2020, 1, 1), date(2021, 12, 31))


def test_stub_provider_rejects_unsupported_tickers_in_reference_data() -> None:
    with pytest.raises(UnsupportedTickerError):
        StubProvider().get_reference_data(["QQQ"])


def test_stub_provider_is_deterministic(tickers: list[str]) -> None:
    args = (tickers, date(2020, 1, 1), date(2020, 6, 30))
    first = StubProvider().get_prices(*args)
    second = StubProvider().get_prices(*args)
    pd.testing.assert_frame_equal(
        first["VOO"].adjusted_close.to_frame(),
        second["VOO"].adjusted_close.to_frame(),
    )


def test_stub_provider_assembles_market_data(tickers: list[str]) -> None:
    market_data = StubProvider().get_market_data(tickers, date(2020, 1, 1), date(2020, 12, 31))

    assert isinstance(market_data, MarketData)
    assert market_data.tickers() == tickers
    assert set(market_data.assets) == set(tickers)
    assert market_data.as_of == date(2020, 12, 31)
    assert not market_data.returns().empty


def test_market_data_assets_must_cover_price_columns() -> None:
    index = pd.to_datetime(["2024-01-01", "2024-01-02"])
    frame = pd.DataFrame({"VOO": [1.0, 2.0]}, index=index)
    with pytest.raises(ValueError, match="unknown tickers"):
        MarketData(prices=frame, assets={})


def test_market_data_infers_as_of_from_the_last_observation() -> None:
    index = pd.to_datetime(["2024-01-02", "2024-01-03"])
    frame = pd.DataFrame({"VOO": [1.0, 2.0]}, index=index)
    assert MarketData(prices=frame, assets={"VOO": UNIVERSE["VOO"].to_asset()}).as_of == date(
        2024, 1, 3
    )


def test_returns_drop_first_observation(synthetic_market_data: MarketData) -> None:
    returns = synthetic_market_data.returns()
    assert len(returns) == len(synthetic_market_data.prices) - 1
    assert not returns.isna().any().any()


def test_price_series_rejects_unsorted_index() -> None:
    index = pd.to_datetime(["2024-01-02", "2024-01-01"])
    series = pd.Series([2.0, 1.0], index=index, dtype=float)
    with pytest.raises(ValueError, match="sorted ascending"):
        PriceSeries(
            ticker="VOO",
            start=date(2024, 1, 1),
            end=date(2024, 1, 2),
            adjusted_close=series,
        )


def test_asset_requires_a_classification() -> None:
    with pytest.raises(TypeError):
        Asset(ticker="VOO", name="Vanguard S&P 500 ETF", asset_class=AssetClass.EQUITY)  # type: ignore[call-arg]


def test_asset_dataclass_is_immutable() -> None:
    asset = UNIVERSE["VOO"].to_asset()
    with pytest.raises(AttributeError):
        asset.ticker = "VTI"  # type: ignore[misc]
