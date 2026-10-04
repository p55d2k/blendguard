"""Provider interface and normalized data model.

Provider-specific payloads are converted to these types *before* reaching the
mathematical layer. Nothing here may import an optimizer or model symbol.

``Asset`` is the provider-normalized shape of reference data: what a data vendor
can tell us about a security. BlendGuard's curated ETF metadata (portfolio role,
exposure kind, plain-language description, support status) lives in
:mod:`app.domain.etf` and is projected down to ``Asset`` by
:func:`asset_from_etf`.

The projection lives here rather than as a method on the domain type on purpose.
``Asset`` is a provider-boundary type, so a domain model that produced one would
be reaching back across the layer it exists to sit above.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd

from app.taxonomy import AssetClass, Region

if TYPE_CHECKING:
    from app.domain.etf import ETF


@dataclass(frozen=True, slots=True)
class Asset:
    """Normalized security reference data, as reported by a data provider."""

    ticker: str
    name: str
    asset_class: AssetClass
    region: Region


def asset_from_etf(etf: ETF) -> Asset:
    """Project curated ETF metadata onto the provider-normalized type.

    Drops role, exposure, description and support status: those are BlendGuard's
    own opinions, not vendor facts, and the provider layer has no use for them.
    """
    return Asset(
        ticker=str(etf.ticker),
        name=etf.name,
        asset_class=etf.asset_class,
        region=etf.region,
    )


@dataclass(frozen=True, slots=True)
class PriceSeries:
    """Normalized end-of-day adjusted closes for a single ticker."""

    ticker: str
    start: date
    end: date
    adjusted_close: pd.Series

    def __post_init__(self) -> None:
        if not self.adjusted_close.index.is_monotonic_increasing:
            raise ValueError(f"{self.ticker}: price series must be sorted ascending")


@dataclass(frozen=True, slots=True)
class MarketData:
    """Normalized end-of-day market data for the full universe.

    Attributes
    ----------
    prices:
        Wide frame of adjusted closes, index=date, columns=ticker.
    assets:
        Reference data keyed by ticker.
    market_caps:
        Optional market caps in USD, used for the market-implied prior.
    as_of:
        Last date present in ``prices``.
    """

    prices: pd.DataFrame
    assets: dict[str, Asset]
    market_caps: dict[str, float] = field(default_factory=dict)
    as_of: date | None = None

    def __post_init__(self) -> None:
        missing = [t for t in self.prices.columns if t not in self.assets]
        if missing:
            raise ValueError(f"prices reference unknown tickers: {missing}")
        if self.as_of is None and len(self.prices.index) > 0:
            object.__setattr__(self, "as_of", self.prices.index[-1].date())

    def returns(self) -> pd.DataFrame:
        """Simple daily returns ``r_t = P_t / P_(t-1) - 1``."""
        return self.prices.pct_change().iloc[1:].dropna(how="any")

    def tickers(self) -> list[str]:
        return list(self.prices.columns)


class MarketDataProvider(ABC):
    """Abstraction boundary between DATA and everything above it."""

    name: str = "abstract"

    @abstractmethod
    def get_prices(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> dict[str, PriceSeries]:
        """Return normalized end-of-day adjusted closes per ticker."""

    @abstractmethod
    def get_reference_data(self, tickers: list[str]) -> dict[str, Asset]:
        """Return normalized reference data per ticker."""

    def get_market_caps(self, tickers: list[str]) -> dict[str, float]:
        """Return market caps in USD.

        Default implementation reports that caps are unavailable; providers
        that can supply caps (e.g. Bloomberg, in development) override this.
        """
        return {}

    def get_market_data(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> MarketData:
        """Assemble a :class:`MarketData` bundle from the provider."""
        prices = self.get_prices(tickers, start, end)
        assets = self.get_reference_data(tickers)

        frame = pd.DataFrame(
            {t: ps.adjusted_close for t, ps in prices.items()},
            dtype=float,
        ).sort_index()

        return MarketData(
            prices=frame,
            assets=assets,
            market_caps=self.get_market_caps(tickers),
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} name={self.name!r}>"
