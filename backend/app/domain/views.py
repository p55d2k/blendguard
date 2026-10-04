"""Investor views and confidence.

A :class:`View` is what the user believes, expressed precisely enough to be
useful. It is deliberately *not* a Black-Litterman view matrix row: the mapping
from "moderately bullish on US equities" to ``(P, Q, Omega)`` belongs to the
MODEL layer, so this type stays readable and the math stays free to change how
it consumes a belief.

Confidence
----------
:class:`Confidence` is an **ordinal label with no numeric meaning**. Nothing
here knows that ``HIGH`` might become a low Omega. That mapping belongs to the
modeling layer, which keeps UI wording from quietly becoming a mathematical
assumption.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.types import DomainValidationError, Ticker, require_finite


class Confidence(StrEnum):
    """How sure the user is about a view.

    Ordinal: ``LOW`` < ``MEDIUM`` < ``HIGH``. No numeric weight is attached, by
    design; see the module docstring.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ViewKind(StrEnum):
    """Whether a view is about the asset itself or its relation to another."""

    ABSOLUTE = "absolute"
    RELATIVE = "relative"


@dataclass(frozen=True, slots=True)
class View:
    """One expressed opinion about one ETF.

    Two shapes, distinguished by :attr:`kind`:

    * ``ABSOLUTE`` -- "I expect VOO to return 8% a year." Sets
      :attr:`expected_return`.
    * ``RELATIVE`` -- "I expect VOO to beat VEA by 2%." Sets
      :attr:`relative_to` and :attr:`outperformance`.

    Whichever shape is used, the fields that do not apply must stay ``None``;
    silently ignoring a stray value would let a contradictory view through.

    Attributes
    ----------
    ticker:
        The ETF the opinion is about.
    kind:
        Absolute or relative.
    expected_return:
        Absolute only. Annualised fractional return, ``0.08`` is 8%.
    relative_to:
        Relative only. The comparison ETF.
    outperforming:
        Relative only. Fractional excess return, ``0.02`` is 2 points better.
    confidence:
        How sure the user is. Required.
    rationale:
        Optional free-text reason, shown back to the user so a portfolio stays
        explainable.
    """

    ticker: Ticker
    kind: ViewKind
    expected_return: float | None = None
    relative_to: Ticker | None = None
    outperforming: float | None = None
    confidence: Confidence = Confidence.MEDIUM
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.ticker, Ticker):
            raise DomainValidationError(f"view.ticker must be a Ticker, got {self.ticker!r}")
        if self.relative_to is not None and not isinstance(self.relative_to, Ticker):
            raise DomainValidationError(
                f"view.relative_to must be a Ticker, got {self.relative_to!r}"
            )
        if not isinstance(self.confidence, Confidence):
            raise DomainValidationError(
                f"view.confidence must be a Confidence, got {self.confidence!r}"
            )

        if self.kind is ViewKind.ABSOLUTE:
            if self.expected_return is None:
                raise DomainValidationError(
                    f"an absolute view on {self.ticker} requires expected_return"
                )
            if self.relative_to is not None or self.outperforming is not None:
                raise DomainValidationError(
                    f"an absolute view on {self.ticker} must not set relative_to or "
                    "outperforming; use a relative view instead"
                )
            require_finite(self.expected_return, f"view.expected_return for {self.ticker}")
        else:
            if self.relative_to is None:
                raise DomainValidationError(
                    f"a relative view on {self.ticker} requires relative_to"
                )
            if self.outperforming is None:
                raise DomainValidationError(
                    f"a relative view on {self.ticker} requires outperforming"
                )
            if self.expected_return is not None:
                raise DomainValidationError(
                    f"a relative view on {self.ticker} must not set expected_return; "
                    "the level is implied by the comparison"
                )
            if self.relative_to == self.ticker:
                raise DomainValidationError(
                    f"a relative view on {self.ticker} cannot compare it to itself"
                )
            require_finite(self.outperforming, f"view.outperforming for {self.ticker}")

    @classmethod
    def absolute(
        cls,
        ticker: Ticker | str,
        expected_return: float,
        confidence: Confidence = Confidence.MEDIUM,
        rationale: str | None = None,
    ) -> View:
        """ "I expect ``ticker`` to return ``expected_return`` a year."

        ``expected_return`` is a fraction: ``0.08`` is 8%.
        """
        return cls(
            ticker=Ticker(ticker),
            kind=ViewKind.ABSOLUTE,
            expected_return=expected_return,
            confidence=confidence,
            rationale=rationale,
        )

    @classmethod
    def relative(
        cls,
        ticker: Ticker | str,
        relative_to: Ticker | str,
        outperforming: float,
        confidence: Confidence = Confidence.MEDIUM,
        rationale: str | None = None,
    ) -> View:
        """ "I expect ``ticker`` to beat ``relative_to`` by ``outperforming``."

        ``outperforming`` is a fraction: ``0.02`` is 2 percentage points.
        """
        return cls(
            ticker=Ticker(ticker),
            kind=ViewKind.RELATIVE,
            relative_to=Ticker(relative_to),
            outperforming=outperforming,
            confidence=confidence,
            rationale=rationale,
        )

    def describe(self) -> str:
        """One plain-language sentence, for the explanation layer.

        No jargon, no mathematics: this is the sentence a user reads back.
        """
        if self.kind is ViewKind.ABSOLUTE:
            body = f"expected to return {self.expected_return * 100:.1f}% a year"  # type: ignore[operator]
        else:
            body = (
                f"expected to beat {self.relative_to} by "
                f"{self.outperforming * 100:.1f} points"  # type: ignore[operator]
            )
        return f"{self.ticker} is {body} ({self.confidence.value} confidence)"
