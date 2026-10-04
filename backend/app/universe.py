"""The canonical ETF universe: one authoritative, hand-written table.

Every downstream layer reads this module. The MODEL layer, the OPTIMIZER layer,
the API, and the UI all enumerate from here; none of them keeps its own list.

Design rules for this file:

* Exactly one literal table: :data:`UNIVERSE`. Do not duplicate ticker lists.
* Metadata only. No finance, no optimization, no presentation logic.
* Adding an ETF is a deliberate universe expansion: update this table, the
  documentation, and the tests together.

The :class:`ETF` type itself lives in :mod:`app.domain.etf` and is re-exported
here, so importing it from either module works. This module owns the *table*;
the domain module owns the *type*.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.etf import ETF
from app.domain.types import Currency, Ticker
from app.taxonomy import (
    TREASURY_DURATION_ORDER,
    AssetClass,
    Exposure,
    Region,
    Role,
)

__all__ = [
    "EMERGING_DEBT",
    "EQUITIES",
    "ETF",
    "HIGH_YIELD",
    "INVESTMENT_GRADE",
    "TICKERS",
    "TREASURIES",
    "UNIVERSE",
    "UnsupportedTickerError",
    "by_asset_class",
    "by_exposure",
    "by_region",
    "by_role",
    "get",
    "require_supported",
    "select_tickers",
    "supported_tickers",
    "tickers_by_asset_class",
    "treasuries_by_duration",
]


class UnsupportedTickerError(ValueError):
    """Raised when a ticker is unknown to, or unsupported in, the universe.

    The universe is never silently widened. Unsupported tickers are an error so
    that no allocation can be produced for an instrument BlendGuard does not
    actually model.
    """

    def __init__(self, tickers: Iterable[str]) -> None:
        self.tickers: tuple[str, ...] = tuple(sorted(set(tickers)))
        plural = "s" if len(self.tickers) != 1 else ""
        super().__init__(
            f"ticker{plural} not supported by the BlendGuard universe: {', '.join(self.tickers)}"
        )


# ---------------------------------------------------------------------------
# The universe. Fourteen ETFs, five asset classes, four regions, eleven roles.
# ---------------------------------------------------------------------------
#: Keyed by plain ``str`` so a caller holding an unvalidated symbol can look a
#: record up without a cast; :class:`~app.domain.types.Ticker` hashes equal to its
#: own text, so validated and raw symbols index the same table.
UNIVERSE: dict[str, ETF] = {
    str(etf.ticker): etf
    for etf in (
        # --- Equity -----------------------------------------------------------
        ETF(
            ticker=Ticker("VOO"),
            name="Vanguard S&P 500 ETF",
            asset_class=AssetClass.EQUITY,
            region=Region.US,
            currency=Currency.USD,
            role=Role.US_LARGE_CAP_CORE,
            exposure=Exposure.CORE,
            description="US large-company stocks. The default engine of a US equity core.",
        ),
        ETF(
            ticker=Ticker("SPY"),
            name="SPDR S&P 500 ETF Trust",
            asset_class=AssetClass.EQUITY,
            region=Region.US,
            currency=Currency.USD,
            role=Role.US_LARGE_CAP_CORE,
            exposure=Exposure.CORE,
            description="The oldest S&P 500 tracker. Holds the same large US companies as VOO.",
        ),
        ETF(
            ticker=Ticker("VTI"),
            name="Vanguard Total Stock Market ETF",
            asset_class=AssetClass.EQUITY,
            region=Region.US,
            currency=Currency.USD,
            role=Role.US_TOTAL_MARKET,
            exposure=Exposure.CORE,
            description="All US stocks, large and small. Broader and cheaper than VOO.",
        ),
        ETF(
            ticker=Ticker("VEA"),
            name="Vanguard FTSE Developed Markets ETF",
            asset_class=AssetClass.EQUITY,
            region=Region.DEVELOPED_EX_US,
            currency=Currency.USD,
            role=Role.DEVELOPED_INTERNATIONAL,
            exposure=Exposure.CORE,
            description="Stocks from developed markets outside the United States.",
        ),
        ETF(
            ticker=Ticker("VWO"),
            name="Vanguard FTSE Emerging Markets ETF",
            asset_class=AssetClass.EQUITY,
            region=Region.EMERGING_MARKETS,
            currency=Currency.USD,
            role=Role.EMERGING_MARKETS,
            exposure=Exposure.CORE,
            description="Stocks from emerging markets. Higher risk, higher long-run growth.",
        ),
        ETF(
            ticker=Ticker("STTF"),
            name="State Street SPDR Straits Times Index ETF",
            asset_class=AssetClass.EQUITY,
            region=Region.SINGAPORE,
            currency=Currency.SGD,
            role=Role.SINGAPORE_LARGE_CAP,
            exposure=Exposure.CORE,
            description=(
                "The blue-chip companies listed in Singapore, in one fund. Priced in "
                "Singapore dollars, so it carries currency risk the rest of the "
                "universe does not."
            ),
        ),
        # --- High yield -------------------------------------------------------
        ETF(
            ticker=Ticker("HYG"),
            name="iShares iBoxx $ High Yield Corporate Bond ETF",
            asset_class=AssetClass.HIGH_YIELD,
            region=Region.US,
            currency=Currency.USD,
            role=Role.HIGH_YIELD_CREDIT,
            exposure=Exposure.SATELLITE,
            description="Lower-rated corporate bonds. More income and default risk than Treasuries.",
        ),
        ETF(
            ticker=Ticker("JNK"),
            name="SPDR Bloomberg High Yield Bond ETF",
            asset_class=AssetClass.HIGH_YIELD,
            region=Region.US,
            currency=Currency.USD,
            role=Role.HIGH_YIELD_CREDIT,
            exposure=Exposure.SATELLITE,
            description="A second high-yield fund that overlaps HYG. A way to compare like-for-like.",
        ),
        ETF(
            ticker=Ticker("USHY"),
            name="iShares Broad USD High Yield Corporate Bond ETF",
            asset_class=AssetClass.HIGH_YIELD,
            region=Region.US,
            currency=Currency.USD,
            role=Role.HIGH_YIELD_CREDIT,
            exposure=Exposure.SATELLITE,
            description=(
                "High-yield bonds issued in dollars, including issuers outside the "
                "United States. The widest of the three high-yield funds here."
            ),
        ),
        # --- Investment grade -------------------------------------------------
        ETF(
            ticker=Ticker("LQD"),
            name="iShares iBoxx $ Investment Grade Corporate Bond ETF",
            asset_class=AssetClass.INVESTMENT_GRADE,
            region=Region.US,
            currency=Currency.USD,
            role=Role.INVESTMENT_GRADE_CREDIT,
            exposure=Exposure.CORE,
            description=(
                "Higher-quality corporate bonds. More income than Treasuries and far "
                "less default risk than high yield."
            ),
        ),
        # --- Treasuries -------------------------------------------------------
        ETF(
            ticker=Ticker("SHY"),
            name="iShares 1-3 Year Treasury Bond ETF",
            asset_class=AssetClass.TREASURY,
            region=Region.US,
            currency=Currency.USD,
            role=Role.SHORT_DURATION_TREASURY,
            exposure=Exposure.CORE,
            description="Short-dated US government bonds. The least rate-sensitive sleeve.",
        ),
        ETF(
            ticker=Ticker("IEF"),
            name="iShares 7-10 Year Treasury Bond ETF",
            asset_class=AssetClass.TREASURY,
            region=Region.US,
            currency=Currency.USD,
            role=Role.INTERMEDIATE_TREASURY,
            exposure=Exposure.CORE,
            description="Medium-dated US government bonds. The middle of the duration range.",
        ),
        ETF(
            ticker=Ticker("TLT"),
            name="iShares 20+ Year Treasury Bond ETF",
            asset_class=AssetClass.TREASURY,
            region=Region.US,
            currency=Currency.USD,
            role=Role.LONG_DURATION_TREASURY,
            exposure=Exposure.CORE,
            description="Long-dated US government bonds. Most sensitive to interest-rate moves.",
        ),
        # --- Emerging-market debt ---------------------------------------------
        ETF(
            ticker=Ticker("LEMB"),
            name="iShares J.P. Morgan EM Local Currency Bond ETF",
            asset_class=AssetClass.EMERGING_DEBT,
            region=Region.EMERGING_MARKETS,
            currency=Currency.USD,
            role=Role.EM_LOCAL_CURRENCY_DEBT,
            exposure=Exposure.SATELLITE,
            description=(
                "Emerging-market bonds held in their own local currencies. Currency "
                "risk on top of the credit risk of the issuers."
            ),
        ),
    )
}

#: Every ticker in the universe, in display order.
TICKERS: list[str] = list(UNIVERSE)


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
def get(ticker: str) -> ETF:
    """Return an ETF, raising :class:`KeyError` for an unknown ticker."""
    return UNIVERSE[ticker]


def require_supported(tickers: Iterable[str]) -> None:
    """Validate that every ticker is known and currently supported.

    Raises
    ------
    UnsupportedTickerError
        If any ticker is absent from the universe or marked unsupported.
    """
    rejected = [t for t in tickers if t not in UNIVERSE or not UNIVERSE[t].supported]
    if rejected:
        raise UnsupportedTickerError(rejected)


def supported_tickers() -> list[str]:
    """Tickers BlendGuard currently supports, in display order."""
    return [t for t, etf in UNIVERSE.items() if etf.supported]


def select_tickers(tickers: Iterable[str]) -> list[str]:
    """Validate ``tickers`` and return them in universe display order."""
    unique = set(tickers)
    require_supported(unique)
    return [t for t in TICKERS if t in unique]


def by_asset_class(asset_class: AssetClass) -> list[str]:
    return [t for t, etf in UNIVERSE.items() if etf.asset_class is asset_class]


def by_region(region: Region) -> list[str]:
    return [t for t, etf in UNIVERSE.items() if etf.region is region]


def by_role(role: Role) -> list[str]:
    """Tickers sharing a role. Overlapping instruments appear together."""
    return [t for t, etf in UNIVERSE.items() if etf.role is role]


def by_exposure(exposure: Exposure) -> list[str]:
    return [t for t, etf in UNIVERSE.items() if etf.exposure is exposure]


def tickers_by_asset_class() -> dict[AssetClass, list[str]]:
    return {ac: by_asset_class(ac) for ac in AssetClass}


def treasuries_by_duration() -> list[str]:
    """Treasuries ordered short -> long duration."""
    return [t for role in TREASURY_DURATION_ORDER for t in by_role(role)]


EQUITIES: list[str] = by_asset_class(AssetClass.EQUITY)
HIGH_YIELD: list[str] = by_asset_class(AssetClass.HIGH_YIELD)
INVESTMENT_GRADE: list[str] = by_asset_class(AssetClass.INVESTMENT_GRADE)
TREASURIES: list[str] = by_asset_class(AssetClass.TREASURY)
EMERGING_DEBT: list[str] = by_asset_class(AssetClass.EMERGING_DEBT)
