"""Deterministic offline provider.

Used by tests and local development when no market data source is available.
Never returns real prices; guards against it being mistaken for production data.
Reference data is projected from the canonical universe so the model and the UI
can never disagree about an ETF's classification.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from app.providers.base import Asset, MarketDataProvider, PriceSeries
from app.universe import UNIVERSE, require_supported


class StubProvider(MarketDataProvider):
    name = "stub"

    def __init__(self, seed: int = 0) -> None:
        self._seed = seed

    def get_prices(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> dict[str, PriceSeries]:
        require_supported(tickers)
        index = pd.bdate_range(start, end)
        out: dict[str, PriceSeries] = {}
        for i, ticker in enumerate(tickers):
            rng = np.random.default_rng(self._seed + i)
            steps = rng.normal(0.0003, 0.008, index.size)
            closes = 100.0 * np.cumprod(1.0 + steps)
            out[ticker] = PriceSeries(
                ticker=ticker,
                start=index[0].date(),
                end=index[-1].date(),
                adjusted_close=pd.Series(closes, index=index, dtype=float),
            )
        return out

    def get_reference_data(self, tickers: list[str]) -> dict[str, Asset]:
        require_supported(tickers)
        return {t: UNIVERSE[t].to_asset() for t in tickers}
