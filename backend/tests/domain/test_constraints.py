"""Domain layer: portfolio construction constraints.

The invariant that matters most here: BlendGuard must never silently relax a
user's limits. These tests pin the checks that turn a contradictory limit into a
clear error at construction time, rather than a portfolio nobody can explain.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.domain.constraints import Constraint, ConstraintKind, ConstraintSet
from app.domain.types import AssetClass, DomainValidationError, Ticker


# --- subject resolution -----------------------------------------------------
def test_a_ticker_constraint_and_an_asset_class_constraint_are_different() -> None:
    # "VOO max 40%" and "equity max 70%" are different instructions. Collapsing
    # them into one shape is how an optimizer ends up guessing which was meant.
    single = Constraint.max_weight(Ticker("VOO"), 0.40)
    aggregate = Constraint.max_weight(AssetClass.EQUITY, 0.70)

    assert single.subject == "ticker:VOO"
    assert aggregate.subject == "asset_class:equity"
    assert single.subject != aggregate.subject


def test_a_bare_string_is_treated_as_a_ticker() -> None:
    assert Constraint.max_weight("VOO", 0.40).ticker == Ticker("VOO")


def test_a_constraint_must_name_exactly_one_subject() -> None:
    with pytest.raises(DomainValidationError, match=r"exactly one of ticker or asset_class"):
        Constraint(kind=ConstraintKind.MAX_WEIGHT, value=0.40)

    with pytest.raises(DomainValidationError, match=r"exactly one of ticker or asset_class"):
        Constraint(
            kind=ConstraintKind.MAX_WEIGHT,
            value=0.40,
            ticker=Ticker("VOO"),
            asset_class=AssetClass.EQUITY,
        )


def test_a_constraint_value_is_a_fraction() -> None:
    with pytest.raises(DomainValidationError, match="looks like a percentage"):
        Constraint.max_weight(Ticker("VOO"), 40.0)


# --- set-level consistency --------------------------------------------------
def test_a_minimum_above_its_maximum_is_contradictory() -> None:
    # No solver should be handed this. It is caught before the optimizer runs.
    with pytest.raises(DomainValidationError, match=r"minimum 0\.6 exceeds maximum 0\.4"):
        ConstraintSet(
            (
                Constraint.min_weight(Ticker("VOO"), 0.60),
                Constraint.max_weight(Ticker("VOO"), 0.40),
            )
        )


def test_a_minimum_equal_to_its_maximum_is_allowed() -> None:
    # An exact allocation is a legitimate instruction: "60% in VOO, not a penny
    # more, not a penny less."
    fixed = ConstraintSet(
        (
            Constraint.min_weight(Ticker("VOO"), 0.60),
            Constraint.max_weight(Ticker("VOO"), 0.60),
        )
    )
    assert fixed.min_for(Ticker("VOO")) == pytest.approx(0.60)


def test_asset_class_bounds_are_checked_too() -> None:
    with pytest.raises(DomainValidationError, match=r"minimum .* exceeds maximum"):
        ConstraintSet(
            (
                Constraint.min_weight(AssetClass.TREASURY, 0.50),
                Constraint.max_weight(AssetClass.TREASURY, 0.20),
            )
        )


def test_bounds_on_different_subjects_do_not_interfere() -> None:
    constraints = ConstraintSet(
        (
            Constraint.min_weight(Ticker("VOO"), 0.60),
            Constraint.max_weight(AssetClass.EQUITY, 0.40),
        )
    )
    assert len(constraints) == 2


def test_a_target_outside_its_bounds_is_contradictory() -> None:
    with pytest.raises(DomainValidationError, match=r"target weight .* is below its minimum"):
        ConstraintSet(
            (
                Constraint.min_weight(Ticker("VOO"), 0.30),
                Constraint.max_weight(Ticker("VOO"), 0.60),
                Constraint.target_weight(Ticker("VOO"), 0.10),
            )
        )

    with pytest.raises(DomainValidationError, match=r"target weight .* is above its maximum"):
        ConstraintSet(
            (
                Constraint.min_weight(Ticker("VOO"), 0.30),
                Constraint.max_weight(Ticker("VOO"), 0.60),
                Constraint.target_weight(Ticker("VOO"), 0.90),
            )
        )


def test_a_target_within_its_bounds_is_accepted() -> None:
    constraints = ConstraintSet(
        (
            Constraint.min_weight(Ticker("VOO"), 0.30),
            Constraint.max_weight(Ticker("VOO"), 0.60),
            Constraint.target_weight(Ticker("VOO"), 0.45),
        )
    )
    assert constraints.min_for(Ticker("VOO")) == pytest.approx(0.30)
    assert constraints.max_for(Ticker("VOO")) == pytest.approx(0.60)


def test_a_target_on_its_own_bounds_is_accepted() -> None:
    # target == max is a consistent instruction, not a contradiction.
    constraints = ConstraintSet(
        (
            Constraint.max_weight(Ticker("VOO"), 0.60),
            Constraint.target_weight(Ticker("VOO"), 0.60),
        )
    )
    assert constraints.max_for(Ticker("VOO")) == pytest.approx(0.60)


def test_duplicate_constraints_for_one_subject_are_rejected() -> None:
    # A silent last-write-wins would make the user's limit ambiguous, and the
    # ambiguity would only surface as an unexplainable portfolio.
    with pytest.raises(DomainValidationError, match="duplicate constraint"):
        ConstraintSet(
            (
                Constraint.max_weight(Ticker("VOO"), 0.40),
                Constraint.max_weight(Ticker("VOO"), 0.60),
            )
        )


def test_the_same_kind_on_different_subjects_is_not_a_duplicate() -> None:
    constraints = ConstraintSet(
        (
            Constraint.max_weight(Ticker("VOO"), 0.40),
            Constraint.max_weight(Ticker("VTI"), 0.40),
        )
    )
    assert len(constraints) == 2


def test_an_empty_set_is_valid() -> None:
    assert len(ConstraintSet()) == 0


# --- lookups ----------------------------------------------------------------
def test_lookups_work_by_ticker_or_asset_class() -> None:
    constraints = ConstraintSet(
        (
            Constraint.max_weight(Ticker("VOO"), 0.40),
            Constraint.min_weight(AssetClass.TREASURY, 0.20),
        )
    )

    assert constraints.tickers_constrained() == (Ticker("VOO"),)
    assert constraints.asset_classes_constrained() == (AssetClass.TREASURY,)
    assert constraints.min_for(AssetClass.TREASURY) == pytest.approx(0.20)
    assert constraints.max_for("VOO") == pytest.approx(0.40)


def test_for_subject_returns_only_that_subjects_constraints() -> None:
    constraints = ConstraintSet(
        (
            Constraint.max_weight(Ticker("VOO"), 0.40),
            Constraint.min_weight(Ticker("VOO"), 0.10),
            Constraint.max_weight(Ticker("SHY"), 0.30),
        )
    )
    assert len(constraints.for_subject(Ticker("VOO"))) == 2
    assert len(constraints.for_subject(Ticker("SHY"))) == 1


def test_an_unconstrained_subject_has_no_bounds() -> None:
    constraints = ConstraintSet((Constraint.max_weight(Ticker("VOO"), 0.40),))
    assert constraints.min_for(Ticker("SHY")) is None
    assert constraints.max_for(Ticker("SHY")) is None


# --- serialization ----------------------------------------------------------
def test_to_dict_is_json_ready() -> None:
    payload = Constraint.min_weight(AssetClass.TREASURY, 0.2, description="Ballast").to_dict()
    assert payload == {
        "kind": "min_weight",
        "value": 0.2,
        "ticker": None,
        "asset_class": "treasury",
        "description": "Ballast",
    }


def test_a_constraint_set_is_immutable() -> None:
    constraints = ConstraintSet((Constraint.max_weight(Ticker("VOO"), 0.40),))
    with pytest.raises(FrozenInstanceError):
        constraints.constraints = ()  # type: ignore[misc]


def test_a_constraint_set_iterates_its_constraints() -> None:
    constraints = ConstraintSet(
        (
            Constraint.max_weight(Ticker("VOO"), 0.40),
            Constraint.min_weight(AssetClass.TREASURY, 0.20),
        )
    )
    assert [c.kind for c in constraints] == [
        ConstraintKind.MAX_WEIGHT,
        ConstraintKind.MIN_WEIGHT,
    ]
