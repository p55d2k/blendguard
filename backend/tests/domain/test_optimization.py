"""Domain layer: optimization request and result.

The weights-must-sum-to-one invariant is the most important test in this file.
CONTEXT.md is explicit that a result summing to anything other than 1 is a defect,
not a rounding detail, so it is enforced at construction rather than trusted to
the solver.
"""

from __future__ import annotations

import pytest

from app.domain.constraints import Constraint, ConstraintSet
from app.domain.optimization import (
    WEIGHT_SUM_TOLERANCE,
    Allocation,
    Goal,
    OptimizationParameters,
    OptimizationRequest,
    OptimizationResult,
    OptimizationStatus,
    PortfolioMetrics,
    RiskLevel,
)
from app.domain.presets import Preset, PresetId
from app.domain.types import AssetClass, DomainValidationError, Ticker
from app.domain.views import Confidence, View


def a_request(**overrides: object) -> OptimizationRequest:
    fields: dict[str, object] = {"tickers": (Ticker("VOO"), Ticker("SHY"))}
    fields.update(overrides)
    return OptimizationRequest(**fields)  # type: ignore[arg-type]


# --- request ----------------------------------------------------------------
def test_a_request_must_select_at_least_one_etf() -> None:
    with pytest.raises(DomainValidationError, match="at least one ETF"):
        a_request(tickers=())


def test_a_request_rejects_duplicate_tickers() -> None:
    with pytest.raises(DomainValidationError, match="duplicate tickers"):
        a_request(tickers=(Ticker("VOO"), Ticker("VOO")))


def test_a_request_requires_validated_tickers() -> None:
    with pytest.raises(DomainValidationError, match="must contain Ticker objects"):
        a_request(tickers=("VOO",))


def test_for_tickers_coerces_raw_symbols() -> None:
    request = OptimizationRequest.for_tickers(["voo", "shy"])
    assert request.tickers == (Ticker("VOO"), Ticker("SHY"))


def test_a_view_outside_the_selection_is_rejected() -> None:
    # Optimizing a portfolio while ignoring a view on an unheld ETF would
    # silently discard what the user asked for.
    with pytest.raises(DomainValidationError, match="outside the selected universe"):
        a_request(views=(View.absolute("VTI", 0.08),))


def test_a_relative_view_comparing_outside_the_selection_is_rejected() -> None:
    with pytest.raises(DomainValidationError, match="not in the selected universe"):
        a_request(views=(View.relative("VOO", "VEA", 0.02),))


def test_a_constraint_outside_the_selection_is_rejected() -> None:
    with pytest.raises(DomainValidationError, match="outside the selected universe"):
        a_request(
            constraints=ConstraintSet((Constraint.max_weight(Ticker("VTI"), 0.5),)),
        )


def test_an_asset_class_constraint_is_not_rejected_as_stray() -> None:
    # Asset-class constraints say nothing about which ETFs are selected.
    request = a_request(
        constraints=ConstraintSet((Constraint.max_weight(AssetClass.EQUITY, 0.9),)),
    )
    assert len(request.constraints) == 1


def test_current_weights_must_reference_selected_etfs() -> None:
    with pytest.raises(DomainValidationError, match="not selected"):
        a_request(current_weights={Ticker("VTI"): 0.5})


def test_current_weights_must_be_fractions() -> None:
    with pytest.raises(DomainValidationError, match="looks like a percentage"):
        a_request(current_weights={Ticker("VOO"): 50.0})


# --- merged constraints -----------------------------------------------------
def test_explicit_constraints_override_preset_constraints() -> None:
    preset = Preset(
        id=PresetId.BALANCED,
        name="Balanced",
        description="A mix.",
        constraints=ConstraintSet((Constraint.max_weight(Ticker("VOO"), 0.30),)),
    )
    request = a_request(
        preset=preset,
        constraints=ConstraintSet((Constraint.max_weight(Ticker("VOO"), 0.50),)),
    )

    merged = request.effective_constraints()
    assert merged.max_for(Ticker("VOO")) == pytest.approx(0.50)


def test_preset_constraints_fill_in_what_the_user_did_not_state() -> None:
    preset = Preset(
        id=PresetId.BALANCED,
        name="Balanced",
        description="A mix.",
        constraints=ConstraintSet(
            (
                Constraint.max_weight(Ticker("VOO"), 0.30),
                Constraint.min_weight(AssetClass.TREASURY, 0.20),
            )
        ),
    )
    request = a_request(
        preset=preset,
        constraints=ConstraintSet((Constraint.max_weight(Ticker("VOO"), 0.50),)),
    )

    merged = request.effective_constraints()
    assert merged.max_for(Ticker("VOO")) == pytest.approx(0.50)  # user wins
    assert merged.min_for(AssetClass.TREASURY) == pytest.approx(0.20)  # preset survives


def test_merging_is_validated() -> None:
    # A preset that contradicts an explicit constraint must not reach the solver.
    preset = Preset(
        id=PresetId.CONSERVATIVE,
        name="Conservative",
        description="Bonds.",
        constraints=ConstraintSet((Constraint.min_weight(Ticker("VOO"), 0.70),)),
    )
    request = a_request(
        preset=preset,
        constraints=ConstraintSet((Constraint.max_weight(Ticker("VOO"), 0.40),)),
    )

    with pytest.raises(DomainValidationError, match=r"minimum .* exceeds maximum"):
        request.effective_constraints()


def test_a_request_without_a_preset_uses_its_own_constraints() -> None:
    constraints = ConstraintSet((Constraint.max_weight(Ticker("VOO"), 0.40),))
    assert a_request(constraints=constraints).effective_constraints() is constraints


# --- parameters -------------------------------------------------------------
def test_risk_aversion_must_be_positive() -> None:
    with pytest.raises(DomainValidationError, match="risk_aversion must be > 0"):
        OptimizationParameters(risk_aversion=0.0)


def test_parameters_default_to_long_only() -> None:
    assert OptimizationParameters().long_only is True


def test_max_iterations_must_be_positive() -> None:
    with pytest.raises(DomainValidationError, match="max_iterations must be > 0"):
        OptimizationParameters(max_iterations=0)


# --- result invariants ------------------------------------------------------
def a_result(**overrides: object) -> OptimizationResult:
    fields: dict[str, object] = {
        "status": OptimizationStatus.SUCCESS,
        "allocations": (
            Allocation(Ticker("VOO"), 0.6, reasons=("Favorable expected return",)),
            Allocation(Ticker("SHY"), 0.4, limiters=("Minimum Treasury allocation",)),
        ),
        "metrics": PortfolioMetrics(expected_return=0.052, volatility=0.081, sharpe_ratio=0.64),
    }
    fields.update(overrides)
    return OptimizationResult(**fields)  # type: ignore[arg-type]


def test_a_successful_result_records_metrics() -> None:
    result = a_result()
    assert result.succeeded
    assert result.weights() == {Ticker("VOO"): 0.6, Ticker("SHY"): 0.4}
    assert result.metrics is not None
    assert result.metrics.expected_return == pytest.approx(0.052)


def test_a_successful_result_needs_at_least_one_allocation() -> None:
    # "Succeeded, with no recommendation" is not a result a user can act on.
    with pytest.raises(DomainValidationError, match="at least one allocation"):
        a_result(allocations=())


def test_weights_that_do_not_sum_to_one_are_rejected() -> None:
    # The invariant that must never be violated, whatever the solver returned.
    with pytest.raises(DomainValidationError, match="must sum to 1"):
        a_result(
            allocations=(
                Allocation(Ticker("VOO"), 0.6),
                Allocation(Ticker("SHY"), 0.3),
            )
        )


def test_weights_may_sum_to_one_within_tolerance() -> None:
    # Solver output is floating point. Rejecting a 1e-9 drift would make every
    # solve fail on a technicality, which trains people to ignore the check.
    total = 1.0 - WEIGHT_SUM_TOLERANCE / 2
    a_result(
        allocations=(Allocation(Ticker("VOO"), total), Allocation(Ticker("SHY"), 0.0)),
    )


def test_a_drift_beyond_tolerance_is_rejected() -> None:
    with pytest.raises(DomainValidationError, match="must sum to 1"):
        a_result(
            allocations=(
                Allocation(Ticker("VOO"), 0.6),
                Allocation(Ticker("SHY"), 0.3 + WEIGHT_SUM_TOLERANCE * 10),
            )
        )


def test_allocations_must_be_unique() -> None:
    with pytest.raises(DomainValidationError, match="duplicate allocation"):
        a_result(
            allocations=(Allocation(Ticker("VOO"), 0.5), Allocation(Ticker("VOO"), 0.5)),
        )


def test_an_allocation_must_be_a_fraction() -> None:
    with pytest.raises(DomainValidationError, match="looks like a percentage"):
        Allocation(Ticker("VOO"), 60.0)


def test_an_explanation_is_carried_on_the_allocation() -> None:
    # Explainability is a product requirement: the UI must not invent reasons for
    # weights it did not compute.
    allocation = Allocation(
        Ticker("VOO"),
        0.42,
        reasons=("Positive user view on US equities",),
        limiters=("Maximum equity allocation",),
    )
    assert allocation.reasons == ("Positive user view on US equities",)
    assert allocation.limiters == ("Maximum equity allocation",)


# --- failure states ---------------------------------------------------------
def test_infeasible_is_an_outcome_not_an_exception() -> None:
    # A user who sets contradictory limits deserves a clear message, not a 500.
    result = OptimizationResult.infeasible("Treasury minimum of 80% cannot be met.")

    assert result.status is OptimizationStatus.INFEASIBLE
    assert not result.succeeded
    assert result.allocations == ()
    assert "80%" in result.messages[0]


def test_failed_is_distinct_from_infeasible() -> None:
    # One means the user's limits conflict; the other means something broke.
    # Reporting them identically either alarms users about a typo or hides a fault.
    assert (
        OptimizationResult.failed("Solver error.").status
        is not OptimizationResult.infeasible("Solver error.").status
    )


def test_an_unsuccessful_result_must_explain_itself() -> None:
    with pytest.raises(DomainValidationError, match="must explain itself"):
        OptimizationResult(status=OptimizationStatus.INFEASIBLE)


def test_an_unsuccessful_result_must_not_carry_weights() -> None:
    # Suggesting weights that violate the user's limits is the failure mode this
    # whole layer exists to prevent.
    with pytest.raises(DomainValidationError, match="must not contain allocations"):
        OptimizationResult(
            status=OptimizationStatus.INFEASIBLE,
            messages=("Impossible.",),
            allocations=(Allocation(Ticker("VOO"), 1.0),),
        )


def test_success_with_warnings_requires_a_warning() -> None:
    with pytest.raises(DomainValidationError, match="at least one warning"):
        OptimizationResult(
            status=OptimizationStatus.SUCCESS_WITH_WARNINGS,
            allocations=(Allocation(Ticker("VOO"), 1.0),),
        )


def test_success_with_warnings_is_a_success() -> None:
    result = OptimizationResult(
        status=OptimizationStatus.SUCCESS_WITH_WARNINGS,
        allocations=(Allocation(Ticker("VOO"), 1.0),),
        warnings=("JNK omitted for lack of history.",),
    )
    assert result.succeeded


# --- metrics ----------------------------------------------------------------
def test_volatility_cannot_be_negative() -> None:
    with pytest.raises(DomainValidationError, match="volatility must be >= 0"):
        PortfolioMetrics(expected_return=0.05, volatility=-0.01)


def test_a_riskless_portfolio_has_zero_volatility_but_no_sharpe() -> None:
    metrics = PortfolioMetrics(expected_return=0.02, volatility=0.0)
    assert metrics.volatility == 0.0
    assert metrics.sharpe_ratio is None


# --- enums ------------------------------------------------------------------
def test_goals_and_risk_levels_cover_the_user_facing_choices() -> None:
    assert {g.value for g in Goal} == {"preserve", "balanced", "growth"}
    assert {r.value for r in RiskLevel} == {"lower", "medium", "higher"}


def test_a_request_carries_an_optional_goal_and_risk_level() -> None:
    request = a_request(goal=Goal.GROWTH, risk_level=RiskLevel.HIGHER, confidence=Confidence.LOW)
    assert request.goal is Goal.GROWTH
    assert request.risk_level is RiskLevel.HIGHER
    assert request.confidence is Confidence.LOW
