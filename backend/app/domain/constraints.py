"""Portfolio construction constraints.

A constraint says what the optimizer is *not allowed* to do. Two ideas matter
here.

**A constraint names its subject.** It applies either to one ETF or to a whole
asset class, and the domain keeps those distinguishable:

    "VOO maximum = 40%"                    -> ticker=VOO
    "Equity asset class maximum = 70%"     -> asset_class=equity

Collapsing both into "a constraint with a value" would force the optimizer to
guess, and guessing here silently produces a portfolio that violates a limit the
user set.

**Constraints are checked against each other.** A minimum above a maximum is
contradictory, and no solver should be asked to resolve it. That cross-check
lives on :class:`ConstraintSet`, which is the natural owner because it is the
thing that can see the whole picture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.types import (
    AssetClass,
    DomainValidationError,
    Ticker,
    require_unit_interval,
)

#: Tolerance when comparing a target weight against a bound, so that
#: ``target == max`` is not treated as a contradiction by float noise.
_EPS = 1e-9


class ConstraintKind(StrEnum):
    """What kind of limit this is."""

    MIN_WEIGHT = "min_weight"
    MAX_WEIGHT = "max_weight"
    TARGET_WEIGHT = "target_weight"


@dataclass(frozen=True, slots=True)
class Constraint:
    """One limit on one subject.

    Exactly one of :attr:`ticker` or :attr:`asset_class` must be set, which is
    what keeps "VOO max 40%" distinct from "equity max 70%".

    Attributes
    ----------
    kind:
        Minimum, maximum or target weight.
    value:
        A fraction: ``0.40`` is 40%. Always in ``[0, 1]``.
    ticker:
        Single-ETF subject, if any.
    asset_class:
        Whole-asset-class subject, if any.
    description:
        Optional plain-language explanation, shown to the user.
    """

    kind: ConstraintKind
    value: float
    ticker: Ticker | None = None
    asset_class: AssetClass | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ConstraintKind):
            raise DomainValidationError(
                f"constraint.kind must be a ConstraintKind, got {self.kind!r}"
            )
        if self.ticker is not None and not isinstance(self.ticker, Ticker):
            raise DomainValidationError(f"constraint.ticker must be a Ticker, got {self.ticker!r}")
        if (self.ticker is None) == (self.asset_class is None):
            raise DomainValidationError(
                "a constraint must apply to exactly one of ticker or asset_class, "
                f"got ticker={self.ticker!r} asset_class={self.asset_class!r}"
            )
        require_unit_interval(self.value, f"constraint.value ({self.describe_subject()})")

    @property
    def subject(self) -> str:
        """Stable identifier for what this constrains, e.g. ``"ticker:VOO"``."""
        if self.ticker is not None:
            return f"ticker:{self.ticker}"
        assert self.asset_class is not None  # guaranteed by __post_init__
        return f"asset_class:{self.asset_class}"

    def describe_subject(self) -> str:
        """Human-readable subject, for error messages."""
        return str(self.ticker) if self.ticker is not None else str(self.asset_class)

    def to_dict(self) -> dict[str, str | float | None]:
        """Flat, JSON-ready form for the API."""
        return {
            "kind": str(self.kind),
            "value": self.value,
            "ticker": str(self.ticker) if self.ticker else None,
            "asset_class": str(self.asset_class) if self.asset_class else None,
            "description": self.description,
        }

    @classmethod
    def min_weight(
        cls,
        subject: Ticker | str | AssetClass,
        value: float,
        description: str | None = None,
    ) -> Constraint:
        """Minimum allocation to a ticker or asset class."""
        return _build(cls, ConstraintKind.MIN_WEIGHT, subject, value, description)

    @classmethod
    def max_weight(
        cls,
        subject: Ticker | str | AssetClass,
        value: float,
        description: str | None = None,
    ) -> Constraint:
        """Maximum allocation to a ticker or asset class."""
        return _build(cls, ConstraintKind.MAX_WEIGHT, subject, value, description)

    @classmethod
    def target_weight(
        cls,
        subject: Ticker | str | AssetClass,
        value: float,
        description: str | None = None,
    ) -> Constraint:
        """Preferred allocation to a ticker or asset class."""
        return _build(cls, ConstraintKind.TARGET_WEIGHT, subject, value, description)


def _build(
    owner: type[Constraint],
    kind: ConstraintKind,
    subject: Ticker | str | AssetClass,
    value: float,
    description: str | None,
) -> Constraint:
    """Resolve a subject that may be given as a ticker or an asset class."""
    if isinstance(subject, AssetClass):
        return owner(kind=kind, value=value, asset_class=subject, description=description)
    return owner(kind=kind, value=value, ticker=Ticker(subject), description=description)


@dataclass(frozen=True, slots=True)
class ConstraintSet:
    """A validated collection of constraints.

    Owns the checks that need the whole picture:

    * no duplicate ``(subject, kind)`` pair -- a silent last-write-wins would
      make a user's limit ambiguous;
    * a minimum never exceeds the maximum for the same subject;
    * a target sits within the subject's bounds, when those bounds exist.
    """

    constraints: tuple[Constraint, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "constraints", tuple(self.constraints))
        for constraint in self.constraints:
            if not isinstance(constraint, Constraint):
                raise DomainValidationError(
                    f"ConstraintSet contains a non-Constraint: {constraint!r}"
                )

        seen: set[tuple[str, str]] = set()
        for constraint in self.constraints:
            key = (constraint.subject, str(constraint.kind))
            if key in seen:
                raise DomainValidationError(
                    f"duplicate constraint for {constraint.subject}: {constraint.kind}"
                )
            seen.add(key)

        bounds = self._bounds()
        for subject, (minimum, maximum) in bounds.items():
            if minimum is not None and maximum is not None and minimum > maximum + _EPS:
                raise DomainValidationError(
                    f"contradictory constraints for {subject}: minimum {minimum} "
                    f"exceeds maximum {maximum}"
                )
        for constraint in self.constraints:
            if constraint.kind is not ConstraintKind.TARGET_WEIGHT:
                continue
            minimum, maximum = bounds.get(constraint.subject, (None, None))
            if minimum is not None and constraint.value < minimum - _EPS:
                raise DomainValidationError(
                    f"target weight for {constraint.subject} ({constraint.value}) is below "
                    f"its minimum ({minimum})"
                )
            if maximum is not None and constraint.value > maximum + _EPS:
                raise DomainValidationError(
                    f"target weight for {constraint.subject} ({constraint.value}) is above "
                    f"its maximum ({maximum})"
                )

    def _bounds(self) -> dict[str, tuple[float | None, float | None]]:
        """Per-subject ``(minimum, maximum)``, ignoring targets."""
        bounds: dict[str, tuple[float | None, float | None]] = {}
        for constraint in self.constraints:
            minimum, maximum = bounds.get(constraint.subject, (None, None))
            if constraint.kind is ConstraintKind.MIN_WEIGHT:
                minimum = constraint.value
            elif constraint.kind is ConstraintKind.MAX_WEIGHT:
                maximum = constraint.value
            bounds[constraint.subject] = (minimum, maximum)
        return bounds

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.constraints)

    def __len__(self) -> int:
        return len(self.constraints)

    def for_subject(self, subject: Ticker | str | AssetClass) -> tuple[Constraint, ...]:
        """Every constraint applying to one subject."""
        key = (
            f"asset_class:{subject}"
            if isinstance(subject, AssetClass)
            else f"ticker:{Ticker(subject)}"
        )
        return tuple(c for c in self.constraints if c.subject == key)

    def tickers_constrained(self) -> tuple[Ticker, ...]:
        """Tickers named by at least one constraint."""
        return tuple(c.ticker for c in self.constraints if c.ticker is not None)

    def asset_classes_constrained(self) -> tuple[AssetClass, ...]:
        """Asset classes named by at least one constraint."""
        return tuple(c.asset_class for c in self.constraints if c.asset_class is not None)

    def min_for(self, subject: Ticker | str | AssetClass) -> float | None:
        return self._bounds().get(
            f"asset_class:{subject}"
            if isinstance(subject, AssetClass)
            else f"ticker:{Ticker(subject)}",
            (None, None),
        )[0]

    def max_for(self, subject: Ticker | str | AssetClass) -> float | None:
        return self._bounds().get(
            f"asset_class:{subject}"
            if isinstance(subject, AssetClass)
            else f"ticker:{Ticker(subject)}",
            (None, None),
        )[1]
