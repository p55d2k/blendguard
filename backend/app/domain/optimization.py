"""Optimization request and result: the contract either side of the optimizer.

An :class:`OptimizationRequest` is everything the optimizer needs and nothing it
does not. It carries no HTTP request, no UI state, no environment variable and no
provider object, so the engine can be driven from a test, a backtest, or an API
call without changing.

An :class:`OptimizationResult` distinguishes outcomes *structurally* rather than
by exception alone. An infeasible constraint set is an expected result of a
constraint-driven optimizer, not an exception -- a user who sets contradictory
limits deserves a clear "these limits cannot all be met", not a 500. Exceptions
remain for genuine bugs.

Invariants checked on construction
----------------------------------
* allocations are non-negative (BlendGuard is long-only);
* a ``SUCCESS`` result's weights sum to 1 within
  :data:`WEIGHT_SUM_TOLERANCE`;
* every view and ticker-scoped constraint in a request refers to a selected ETF.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.constraints import Constraint, ConstraintSet
from app.domain.presets import Preset
from app.domain.types import (
    DomainValidationError,
    Ticker,
    require_finite,
    require_unit_interval,
)
from app.domain.views import Confidence, View

#: How far the weights of a successful portfolio may drift from summing to 1.
#: Solver output is floating point, so exact equality is the wrong test; 1e-6 is
#: far tighter than any rounding a weight displayed to a user would show.
WEIGHT_SUM_TOLERANCE = 1e-6


class Goal(StrEnum):
    """What the user is trying to achieve."""

    PRESERVE = "preserve"
    BALANCED = "balanced"
    GROWTH = "growth"


class RiskLevel(StrEnum):
    """How much movement the user is willing to accept."""

    LOWER = "lower"
    MEDIUM = "medium"
    HIGHER = "higher"


class OptimizationStatus(StrEnum):
    """How the optimization ended.

    ``INFEASIBLE`` and ``FAILED`` are separate: one means the user's own limits
    cannot all be satisfied, the other means something went wrong. Presenting
    them identically would either alarm users about a typo or hide a real fault.
    """

    SUCCESS = "success"
    SUCCESS_WITH_WARNINGS = "success_with_warnings"
    INFEASIBLE = "infeasible"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class OptimizationParameters:
    """Optimizer knobs that are not constraints.

    Attributes
    ----------
    risk_aversion:
        How strongly to penalise volatility. Higher means a more conservative
        portfolio. ``None`` lets the optimizer choose.
    long_only:
        Whether short positions are forbidden. BlendGuard assumes long-only.
    max_iterations:
        Optional solver iteration cap.
    """

    risk_aversion: float | None = None
    long_only: bool = True
    max_iterations: int | None = None

    def __post_init__(self) -> None:
        if (
            self.risk_aversion is not None
            and require_finite(self.risk_aversion, "risk_aversion") <= 0.0
        ):
            raise DomainValidationError(f"risk_aversion must be > 0, got {self.risk_aversion}")
        if self.max_iterations is not None and self.max_iterations <= 0:
            raise DomainValidationError(f"max_iterations must be > 0, got {self.max_iterations}")


@dataclass(frozen=True, slots=True)
class OptimizationRequest:
    """A complete, self-contained optimization request.

    Attributes
    ----------
    tickers:
        The ETFs to allocate across. Must be non-empty and free of duplicates.
    views:
        Expressed opinions. Each must concern a selected ETF.
    confidence:
        Optional default confidence for views that do not state their own.
    constraints:
        Limits the result must respect.
    preset:
        Optional preset whose constraints act as a starting point.
    current_weights:
        Optional existing weights, for drift or rebalancing analysis.
    parameters:
        Optimizer knobs that are not constraints.
    goal:
        Optional user goal.
    risk_level:
        Optional risk tolerance.
    """

    tickers: tuple[Ticker, ...]
    views: tuple[View, ...] = field(default_factory=tuple)
    confidence: Confidence | None = None
    constraints: ConstraintSet = field(default_factory=ConstraintSet)
    preset: Preset | None = None
    current_weights: Mapping[Ticker, float] = field(default_factory=dict)
    parameters: OptimizationParameters = field(default_factory=OptimizationParameters)
    goal: Goal | None = None
    risk_level: RiskLevel | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "tickers", tuple(self.tickers))
        object.__setattr__(self, "views", tuple(self.views))
        object.__setattr__(self, "current_weights", dict(self.current_weights))

        if not self.tickers:
            raise DomainValidationError("an optimization request must select at least one ETF")
        for ticker in self.tickers:
            if not isinstance(ticker, Ticker):
                raise DomainValidationError(
                    f"request.tickers must contain Ticker objects, got {ticker!r}"
                )
        duplicates = sorted({t for t in self.tickers if self.tickers.count(t) > 1})
        if duplicates:
            raise DomainValidationError(f"duplicate tickers in request: {', '.join(duplicates)}")

        selected = set(self.tickers)
        for view in self.views:
            if view.ticker not in selected:
                raise DomainValidationError(
                    f"view on {view.ticker} is outside the selected universe"
                )
            if view.relative_to is not None and view.relative_to not in selected:
                raise DomainValidationError(
                    f"view on {view.ticker} compares against {view.relative_to}, "
                    "which is not in the selected universe"
                )

        stray = [t for t in self.constraints.tickers_constrained() if t not in selected]
        if stray:
            raise DomainValidationError(
                "constraints reference ETFs outside the selected universe: "
                + ", ".join(sorted(stray))
            )

        for ticker, weight in self.current_weights.items():
            if ticker not in selected:
                raise DomainValidationError(
                    f"current_weights includes {ticker}, which is not selected"
                )
            require_unit_interval(weight, f"current_weights[{ticker}]")

        if self.preset is not None and not isinstance(self.preset, Preset):
            raise DomainValidationError("request.preset must be a Preset")

    def effective_constraints(self) -> ConstraintSet:
        """Preset constraints merged with explicit ones, explicit winning.

        A preset is a starting point, not a ceiling: a preset limit the user did
        not restate is kept, and one they did restate is replaced by theirs.
        Comparing on ``(subject, kind)`` means a user's *maximum* never inherits
        the preset's *minimum*, which would quietly tighten a limit they set.

        The merged set is re-validated, so a preset that contradicts an explicit
        constraint is caught here rather than by the solver.
        """
        if self.preset is None:
            return self.constraints
        stated = {(c.subject, c.kind) for c in self.constraints}
        merged = [c for c in self.preset.constraints if (c.subject, c.kind) not in stated]
        merged.extend(self.constraints)
        return ConstraintSet(tuple(merged))

    @classmethod
    def for_tickers(
        cls,
        tickers: tuple[Ticker, ...] | list[Ticker] | list[str],
        **kwargs: object,
    ) -> OptimizationRequest:
        """Convenience constructor that coerces tickers."""
        return cls(tickers=tuple(Ticker(t) for t in tickers), **kwargs)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class PortfolioMetrics:
    """Expected performance of a recommended portfolio.

    All values are fractions per year: ``0.07`` expected return is 7%, ``0.12``
    volatility is 12%.
    """

    expected_return: float
    volatility: float
    sharpe_ratio: float | None = None

    def __post_init__(self) -> None:
        require_finite(self.expected_return, "expected_return")
        if self.volatility < 0.0:
            raise DomainValidationError(f"volatility must be >= 0, got {self.volatility}")
        if self.sharpe_ratio is not None:
            require_finite(self.sharpe_ratio, "sharpe_ratio")


@dataclass(frozen=True, slots=True)
class Allocation:
    """One ETF's recommended weight, with its explanation.

    Explainability is a product requirement, not a nicety: every allocation
    carries the reasons it earned the weight and the limits that held it back,
    so the UI never has to invent an explanation for a number it did not
    compute.

    Attributes
    ----------
    ticker:
        The ETF.
    weight:
        Fraction of the portfolio, ``0.42`` is 42%.
    reasons:
        Why this ETF earned its allocation.
    limiters:
        What stopped it earning more.
    """

    ticker: Ticker
    weight: float
    reasons: tuple[str, ...] = field(default_factory=tuple)
    limiters: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "reasons", tuple(self.reasons))
        object.__setattr__(self, "limiters", tuple(self.limiters))
        if not isinstance(self.ticker, Ticker):
            raise DomainValidationError(f"allocation.ticker must be a Ticker, got {self.ticker!r}")
        require_unit_interval(self.weight, f"allocation.weight[{self.ticker}]")


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """The outcome of one optimization.

    Attributes
    ----------
    status:
        How it ended. Infeasible and failed are distinct from success.
    allocations:
        Recommended weights. Empty when the status is not a success.
    metrics:
        Expected return and risk, when a portfolio was produced.
    applied_constraints:
        The limits that were enforced.
    views:
        The views the portfolio was built against, echoed for explanation.
    messages:
        Human-readable outcome. Required for infeasible and failed results, so a
        user is always told what happened.
    warnings:
        Non-fatal diagnostics.
    """

    status: OptimizationStatus
    allocations: tuple[Allocation, ...] = field(default_factory=tuple)
    metrics: PortfolioMetrics | None = None
    applied_constraints: tuple[Constraint, ...] = field(default_factory=tuple)
    views: tuple[View, ...] = field(default_factory=tuple)
    messages: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "allocations", tuple(self.allocations))
        object.__setattr__(self, "applied_constraints", tuple(self.applied_constraints))
        object.__setattr__(self, "views", tuple(self.views))
        object.__setattr__(self, "messages", tuple(self.messages))
        object.__setattr__(self, "warnings", tuple(self.warnings))

        if not isinstance(self.status, OptimizationStatus):
            raise DomainValidationError(
                f"result.status must be an OptimizationStatus, got {self.status!r}"
            )

        for constraint in self.applied_constraints:
            if not isinstance(constraint, Constraint):
                raise DomainValidationError(
                    f"result.applied_constraints contains a non-Constraint: {constraint!r}"
                )
        for view in self.views:
            if not isinstance(view, View):
                raise DomainValidationError(f"result.views contains a non-View: {view!r}")

        seen: set[Ticker] = set()
        for allocation in self.allocations:
            # Checked here so a bad entry is a named domain error rather than an
            # AttributeError from somewhere below.
            if not isinstance(allocation, Allocation):
                raise DomainValidationError(
                    f"result.allocations contains a non-Allocation: {allocation!r}"
                )
            if allocation.ticker in seen:
                raise DomainValidationError(f"duplicate allocation for {allocation.ticker}")
            seen.add(allocation.ticker)

        succeeded = self.status in (
            OptimizationStatus.SUCCESS,
            OptimizationStatus.SUCCESS_WITH_WARNINGS,
        )

        if succeeded:
            if not self.allocations:
                raise DomainValidationError(
                    f"a {self.status} result must contain at least one allocation"
                )
            total = sum(a.weight for a in self.allocations)
            if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
                raise DomainValidationError(
                    f"weights must sum to 1 (within {WEIGHT_SUM_TOLERANCE}), got {total:.10f}"
                )
        else:
            if self.allocations:
                raise DomainValidationError(
                    f"a {self.status} result must not contain allocations; "
                    "return weights only when the optimization succeeded"
                )
            if not self.messages:
                raise DomainValidationError(
                    f"a {self.status} result must explain itself in messages"
                )

        if self.status is OptimizationStatus.SUCCESS_WITH_WARNINGS and not self.warnings:
            raise DomainValidationError(
                "a SUCCESS_WITH_WARNINGS result must carry at least one warning"
            )

    @property
    def succeeded(self) -> bool:
        return self.status in (
            OptimizationStatus.SUCCESS,
            OptimizationStatus.SUCCESS_WITH_WARNINGS,
        )

    def weights(self) -> dict[Ticker, float]:
        """Ticker -> weight, for callers that do not want the full allocations."""
        return {a.ticker: a.weight for a in self.allocations}

    @classmethod
    def infeasible(cls, message: str, **kwargs: object) -> OptimizationResult:
        """A constraint set that cannot be satisfied.

        An expected outcome, not an error: the user's own limits conflict.
        """
        return cls(
            status=OptimizationStatus.INFEASIBLE,
            messages=(message,),
            **kwargs,  # type: ignore[arg-type]
        )

    @classmethod
    def failed(cls, message: str, **kwargs: object) -> OptimizationResult:
        """The optimization could not be carried out."""
        return cls(
            status=OptimizationStatus.FAILED,
            messages=(message,),
            **kwargs,  # type: ignore[arg-type]
        )
