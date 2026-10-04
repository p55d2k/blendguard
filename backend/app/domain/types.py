"""Shared financial types and conventions for the domain layer.

Every numeric convention BlendGuard uses is fixed here and stated once.

============================  ==========================================
Convention                    Meaning
============================  ==========================================
Weight                        A fraction of the portfolio. ``0.25`` is 25%.
Return                        A fractional change. ``0.05`` is +5%.
Price                         A plain number in the stated currency.
                              ``123.45`` is 123.45 units, never ``"$123.45"``.
Annualised expected return    Per-year fraction. ``0.07`` is 7% a year.
Outperformance (relative view)Fractional excess return. ``0.02`` is 2 points.
Ticker                        Upper-case exchange symbol, always a :class:`Ticker`.
Date                          A ``datetime.date``; never a formatted string.
============================  ==========================================

A formatted string is a *presentation* concern. Nothing in the domain layer
produces one, so no arithmetic anywhere has to parse one back.

Deliberately absent
-------------------
There is no ``Weight``, ``Return`` or ``Price`` wrapper class. A wrapper that
only re-exposes a float adds ceremony without preventing a mistake; the range
checks below catch the mistakes that actually happen. Strong contracts, not
type-system theatre.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from enum import StrEnum

from app.taxonomy import AssetClass, Exposure, Region, Role

__all__ = [
    "AssetClass",
    "Currency",
    "DomainValidationError",
    "Exposure",
    "Region",
    "Role",
    "Ticker",
    "require_date",
    "require_finite",
    "require_non_negative",
    "require_positive",
    "require_unit_interval",
]


class DomainValidationError(ValueError):
    """Raised when a domain invariant is violated.

    Subclasses :class:`ValueError` so ordinary ``except ValueError`` handling
    keeps working, while giving callers a way to distinguish a malformed domain
    object from, say, an I/O error.

    Every message names the offending field so a failure is actionable without
    a debugger.
    """


class Ticker(str):
    """A validated exchange ticker.

    Subclasses :class:`str` so a ticker can be used anywhere a string is
    expected -- as a mapping key, in JSON, in SQL -- while still being a
    distinct type that cannot be confused with a free-form label or a fund name.

    Normalised to upper case, so ``Ticker("voo")`` and ``Ticker("VOO")`` are the
    same ticker and a lowercase symbol from a data provider is corrected at the
    boundary rather than silently failing to match the universe.

    >>> Ticker("voo") == "VOO"
    True
    """

    #: Upper-case letters and digits, optionally with a class separator. The
    #: separator keeps room for share classes such as ``BRK.B``.
    _PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)*$")

    __slots__ = ()

    def __new__(cls, value: str) -> Ticker:
        if not isinstance(value, str):  # pragma: no cover - guards misuse
            raise DomainValidationError(f"ticker must be a string, got {type(value).__name__}")
        normalised = value.strip().upper()
        if not normalised:
            raise DomainValidationError("ticker must not be empty")
        if len(normalised) > 12:
            raise DomainValidationError(
                f"ticker {normalised!r} is too long ({len(normalised)} characters, max 12)"
            )
        if not cls._PATTERN.match(normalised):
            raise DomainValidationError(
                f"ticker {normalised!r} is not a valid exchange symbol "
                "(upper-case letters and digits, optionally separated by '.' or '-')"
            )
        return super().__new__(cls, normalised)


class Currency(StrEnum):
    """Currency of a monetary value.

    One member per currency a supported ETF is *priced* in. ``SGD`` exists
    because the Straits Times ETF trades in Singapore dollars: without it, an SGD
    price series would be indistinguishable from a USD one. Note that this is the
    trading currency, not the exposure -- ``LEMB`` is ``USD`` even though it holds
    emerging-market bonds in their local currencies.
    """

    USD = "usd"
    SGD = "sgd"


# ---------------------------------------------------------------------------
# Shared validation helpers
# ---------------------------------------------------------------------------
def _require_real(value: float, field: str) -> float:
    """Reject non-numbers, and reject ``bool`` in particular.

    ``bool`` subclasses ``int``, so without this an accidental ``True`` is
    silently accepted as the number 1 -- a 100% weight, a 100% expected return.
    Those are exactly the mistakes that reach a user as a confident, wrong number.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DomainValidationError(f"{field} must be a real number, got {value!r}")
    return value


def require_finite(value: float, field: str) -> float:
    """Reject NaN and infinity.

    A NaN weight silently poisons every downstream sum and comparison, and only
    surfaces much later as an unexplained numerical failure.
    """
    _require_real(value, field)
    if not math.isfinite(value):
        raise DomainValidationError(f"{field} must be a finite number, got {value!r}")
    return value


def require_non_negative(value: float, field: str) -> float:
    """Reject negative values. BlendGuard assumes long-only throughout."""
    require_finite(value, field)
    if value < 0.0:
        raise DomainValidationError(f"{field} must be >= 0, got {value}")
    return value


def require_positive(value: float, field: str) -> float:
    """Reject zero and negative values, for quantities like a price."""
    require_finite(value, field)
    if value <= 0.0:
        raise DomainValidationError(f"{field} must be > 0, got {value}")
    return value


def require_unit_interval(value: float, field: str) -> float:
    """Require a fraction in ``[0, 1]``.

    Weights, allocations and target weights are all fractions: ``0.25`` is 25%.
    Catching ``25`` here is the whole point -- it is the single most likely
    percentage/decimal mistake, and it is otherwise invisible until the
    optimizer produces a nonsense portfolio.
    """
    require_finite(value, field)
    if not 0.0 <= value <= 1.0:
        raise DomainValidationError(
            f"{field} must be a fraction between 0 and 1 (got {value}); "
            f"{value:g} looks like a percentage"
        )
    return value


def require_date(value: date, field: str) -> date:
    """Guard against a ``datetime`` leaking into a date-only field.

    ``datetime`` subclasses ``date``, so a plain ``isinstance`` check would let a
    timestamp through and make day-boundary comparisons silently wrong.
    """
    if isinstance(value, datetime) or not isinstance(value, date):
        raise DomainValidationError(
            f"{field} must be a datetime.date without a time component, got {value!r}"
        )
    return value
