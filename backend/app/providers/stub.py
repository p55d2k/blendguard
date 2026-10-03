"""Deterministic offline provider.

Used by tests and local development when no market data source is available.
Never returns real prices; guards against it being mistaken for production data
see docs/architecture.md.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from app.providers.base import Asset, MarketDataProvider, PriceSeries


class StubProvider(MarketDataProvider):
    name = "stub"

    def __init__(self, seed: int = 0) -> None:
        self._seed = seed

    def get_prices(self, tickers: list[str], start: date, end: date) -> dict[str, PriceSeries]:
        index = pd.bdate_range(start, end)
        out: dict[str, PriceSeries] = {}
        for i, ticker in enumerate(tickers):
            rng = np.random.default_rng(self._seed + i)
            steps = rng.normal(0.0003, 0.008, index.size)
            closes = 100.0 * np.exp(np.cumsum(steps))
            out[ticker] = PriceSeries(
                ticker=ticker,
                start=index[0].date(),
                end=index[-1].date(),
                adjusted_close=pd.Series(closes, index=index, dtype=float),
            )
        return out

    def get_reference_data(self, tickers: list[str]) -> dict[str, Asset]:
        from app.universe import UNIVERSE

        return {t: UNIVERSE[t] for t in tickers if t in UNIVERSE}
