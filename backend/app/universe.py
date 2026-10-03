"""The fixed initial ETF universe (see docs/model.md).

Deliberately small and explicit so the model stays validatable and the UI stays
explainable. Expanding the universe is a documented, deliberate change.
"""

from __future__ import annotations

from app.providers.base import Asset, AssetClass

UNIVERSE: dict[str, Asset] = {
    # Equities
    "VOO": Asset("VOO", "Vanguard S&P 500 ETF", AssetClass.EQUITY, "US"),
    "VTI": Asset("VTI", "Vanguard Total Stock Market ETF", AssetClass.EQUITY, "US"),
    "VEA": Asset(
        "VEA", "Vanguard FTSE Developed Markets ETF", AssetClass.EQUITY, "Developed ex-US"
    ),
    "VWO": Asset("VWO", "Vanguard FTSE Emerging Markets ETF", AssetClass.EQUITY, "Emerging"),
    # High yield
    "HYG": Asset("HYG", "iShares iBoxx High Yield Corporate Bond ETF", AssetClass.HIGH_YIELD, "US"),
    "JNK": Asset("JNK", "SPDR Bloomberg High Yield Bond ETF", AssetClass.HIGH_YIELD, "US"),
    # Treasuries
    "SHY": Asset("SHY", "iShares 1-3 Year Treasury Bond ETF", AssetClass.TREASURY, "US"),
    "IEF": Asset("IEF", "iShares 7-10 Year Treasury Bond ETF", AssetClass.TREASURY, "US"),
    "TLT": Asset("TLT", "iShares 20+ Year Treasury Bond ETF", AssetClass.TREASURY, "US"),
}

TICKERS: list[str] = list(UNIVERSE)


def assets_by_class(asset_class: AssetClass) -> list[str]:
    return [a.ticker for a in UNIVERSE.values() if a.asset_class is asset_class]


EQUITIES: list[str] = assets_by_class(AssetClass.EQUITY)
HIGH_YIELD: list[str] = assets_by_class(AssetClass.HIGH_YIELD)
TREASURIES: list[str] = assets_by_class(AssetClass.TREASURY)
