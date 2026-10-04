"""Domain layer: runtime type guards.

Several checks in the domain exist only for values that arrive at runtime with
the wrong type -- a raw ``str`` from a provider, a ``dict`` where a ``Constraint``
was expected. mypy rejects all of these at the call site, so nothing else covers
them, and a guard nobody has ever executed is a guard that does not work.

Every test here deliberately passes a wrong type and needs a ``type: ignore``.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from app.domain.constraints import Constraint, ConstraintKind, ConstraintSet
from app.domain.etf import ETF
from app.domain.market import Price, Return
from app.domain.optimization import (
    Allocation,
    OptimizationRequest,
    OptimizationResult,
    OptimizationStatus,
)
from app.domain.presets import Preset
from app.domain.types import AssetClass, Currency, DomainValidationError, Ticker
from app.domain.views import Confidence, View, ViewKind


def test_constraint_rejects_an_unvalidated_ticker() -> None:
    with pytest.raises(DomainValidationError, match=r"constraint\.ticker must be a Ticker"):
        Constraint(kind=ConstraintKind.MAX_WEIGHT, value=0.4, ticker="VOO")  # type: ignore[arg-type]


def test_constraint_rejects_an_unrecognised_kind() -> None:
    with pytest.raises(DomainValidationError, match="must be a ConstraintKind"):
        Constraint(kind="max_weight", value=0.4, ticker=Ticker("VOO"))  # type: ignore[arg-type]


def test_a_constraint_set_rejects_non_constraints() -> None:
    with pytest.raises(DomainValidationError, match="non-Constraint"):
        ConstraintSet(("max 40% of VOO",))  # type: ignore[arg-type]


def test_price_rejects_an_unvalidated_ticker() -> None:
    with pytest.raises(DomainValidationError, match=r"price\.ticker must be a Ticker"):
        Price("VOO", date(2024, 1, 2), 100.0)  # type: ignore[arg-type]


def test_return_rejects_an_unvalidated_ticker() -> None:
    with pytest.raises(DomainValidationError, match=r"return\.ticker must be a Ticker"):
        Return("VOO", date(2024, 1, 2), 0.01)  # type: ignore[arg-type]


def test_allocation_rejects_an_unvalidated_ticker() -> None:
    with pytest.raises(DomainValidationError, match=r"allocation\.ticker must be a Ticker"):
        Allocation("VOO", 0.5)  # type: ignore[arg-type]


def test_a_view_rejects_an_unvalidated_comparison_ticker() -> None:
    with pytest.raises(DomainValidationError, match="relative_to must be a Ticker"):
        View(
            ticker=Ticker("VOO"),
            kind=ViewKind.RELATIVE,
            relative_to="VEA",  # type: ignore[arg-type]
            outperforming=0.02,
        )


def test_a_request_rejects_a_non_preset() -> None:
    with pytest.raises(DomainValidationError, match="preset must be a Preset"):
        OptimizationRequest(tickers=(Ticker("VOO"),), preset="conservative")  # type: ignore[arg-type]


def test_a_result_rejects_a_non_status() -> None:
    with pytest.raises(DomainValidationError, match="must be an OptimizationStatus"):
        OptimizationResult(status="success")  # type: ignore[arg-type]


def test_a_result_rejects_non_allocation_entries() -> None:
    with pytest.raises(DomainValidationError, match="non-Allocation"):
        OptimizationResult(
            status=OptimizationStatus.SUCCESS,
            allocations=("VOO",),  # type: ignore[arg-type]
            messages=("nope",),
        )


def test_a_result_rejects_non_view_entries() -> None:
    with pytest.raises(DomainValidationError, match="non-View"):
        OptimizationResult(
            status=OptimizationStatus.SUCCESS,
            allocations=(Allocation(Ticker("VOO"), 1.0),),
            views=("VOO is bullish",),  # type: ignore[arg-type]
        )


def test_a_result_rejects_non_constraint_entries() -> None:
    with pytest.raises(DomainValidationError, match="non-Constraint"):
        OptimizationResult(
            status=OptimizationStatus.SUCCESS,
            allocations=(Allocation(Ticker("VOO"), 1.0),),
            applied_constraints=("max 40%",),  # type: ignore[arg-type]
        )


def test_etf_rejects_a_raw_ticker() -> None:
    with pytest.raises(DomainValidationError, match="ticker must be a Ticker"):
        ETF(
            ticker="VOO",  # type: ignore[arg-type]
            name="Vanguard S&P 500 ETF",
            asset_class=AssetClass.EQUITY,
            region=None,  # type: ignore[arg-type]
            currency=Currency.USD,
            role=None,  # type: ignore[arg-type]
            exposure=None,  # type: ignore[arg-type]
            description="US large-company stocks.",
        )


def test_a_preset_rejects_a_non_constraint_set() -> None:
    with pytest.raises(DomainValidationError, match="must be a ConstraintSet"):
        Preset(
            id="balanced",
            name="Balanced",
            description="A mix.",
            constraints=(),  # type: ignore[arg-type]
        )


def test_a_confidence_given_as_a_plain_string_is_refused() -> None:
    # StrEnum means "high" would otherwise be accepted as Confidence.HIGH by any
    # code path that forgot to convert. Refusing it keeps one representation.
    with pytest.raises(DomainValidationError, match="must be a Confidence"):
        View(
            ticker=Ticker("VOO"),
            kind=ViewKind.ABSOLUTE,
            expected_return=0.08,
            confidence="high",  # type: ignore[arg-type]
        )


def test_frozen_domain_types_cannot_be_mutated() -> None:
    # Belt and braces alongside the frozen dataclass: a domain value that changes
    # after it has been used as a dict key or a constraint subject is worse than
    # no value at all.
    allocation = Allocation(Ticker("VOO"), 0.5)
    with pytest.raises(FrozenInstanceError):
        allocation.weight = 0.9  # type: ignore[misc]


def test_an_equality_check_ignores_nothing() -> None:
    # Two domain values built the same way must compare equal, or a caller cannot
    # tell whether a rebuild changed anything.
    assert Constraint.max_weight("VOO", 0.4) == Constraint.max_weight(Ticker("VOO"), 0.4)
    assert Confidence.HIGH is Confidence("high")
