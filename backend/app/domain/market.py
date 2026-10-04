"""Price and return observations.

Both are *observations of one ETF on one date*. A series is an ordered
collection of observations, not a different type: nothing here assumes there is
only one current price, and a ``Price`` with a date is a historical observation.

Representation
--------------
A return is a fractional change, so ``0.05`` is **+5%** everywhere and never
``5``. Only *simple* returns exist (``r_t = P_t / P_(t-1) - 1``), which is what
:mod:`app.optimizer.risk` computes. A cumulative-return type is deliberately
absent until something needs it -- compounding two representations is how
double-counting happens.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.domain.types import (
    Currency,
    DomainValidationError,
    Ticker,
    require_date,
    require_finite,
    require_positive,
)


class PriceKind(StrEnum):
    """Which price a :class:`Price` carries.

    BlendGuard models total return, so ``ADJUSTED_CLOSE`` is the only kind the
    optimizer consumes. ``RAW_CLOSE`` exists because providers report both and
    confusing them is a silent source of wrong returns.
    """

    ADJUSTED_CLOSE = "adjusted_close"
    RAW_CLOSE = "raw_close"


class ReturnFrequency(StrEnum):
    """Period each return covers."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass(frozen=True, slots=True)
class Price:
    """One end-of-day price observation.

    Attributes
    ----------
    ticker:
        Which ETF this prices.
    date:
        Trading date. Date-only, so no timezone ambiguity.
    price:
        A plain number in ``currency``. Never a formatted string: ``123.45``
        means 123.45 units, and formatting belongs to the presentation layer.
    currency:
        Currency of ``price``.
    kind:
        Whether this is an adjusted or raw close.
    """

    ticker: Ticker
    date: date
    price: float
    currency: Currency = Currency.USD
    kind: PriceKind = PriceKind.ADJUSTED_CLOSE

    def __post_init__(self) -> None:
        if not isinstance(self.ticker, Ticker):
            raise DomainValidationError(f"price.ticker must be a Ticker, got {self.ticker!r}")
        require_date(self.date, "price.date")
        require_positive(self.price, f"price.price for {self.ticker}")

    def simple_return_to(self, previous: Price) -> float:
        """Simple return from ``previous`` to ``self``: ``P_t / P_(t-1) - 1``.

        ``0.05`` means +5%. The date order is checked, because a "return" into
        the past is always a bug.
        """
        if self.ticker != previous.ticker:
            raise DomainValidationError(
                f"cannot compute a return from {previous.ticker} to {self.ticker}"
            )
        if self.date <= previous.date:
            raise DomainValidationError(
                f"return must move forward in time, got {previous.date} -> {self.date}"
            )
        if self.kind is not previous.kind:
            raise DomainValidationError(
                f"cannot mix {previous.kind} and {self.kind} when computing a return"
            )
        return self.price / previous.price - 1.0


@dataclass(frozen=True, slots=True)
class Return:
    """One simple return observation.

    Attributes
    ----------
    ticker:
        Which ETF this return belongs to.
    date:
        The period *end* date the return covers.
    value:
        Fractional change. ``0.05`` is +5%, ``-0.02`` is -2%.
    frequency:
        Period the return covers.
    """

    ticker: Ticker
    date: date
    value: float
    frequency: ReturnFrequency = ReturnFrequency.DAILY

    def __post_init__(self) -> None:
        if not isinstance(self.ticker, Ticker):
            raise DomainValidationError(f"return.ticker must be a Ticker, got {self.ticker!r}")
        require_date(self.date, "return.date")
        require_finite(self.value, f"return.value for {self.ticker}")
        # Returns are genuinely negative more often than not, so only finiteness
        # is enforced here -- not a unit-interval check.
        if self.value <= -1.0:
            raise DomainValidationError(
                f"return.value for {self.ticker} must be greater than -1 "
                f"(a total loss is -1), got {self.value}"
            )

    def as_percent(self) -> float:
        """Presentation helper: ``0.05`` -> ``5.0``.

        A convenience for the presentation layer. Never used in arithmetic.
        """
        return self.value * 100.0
