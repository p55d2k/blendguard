"""Domain layer: investor views and confidence."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.domain.types import DomainValidationError, Ticker
from app.domain.views import Confidence, View, ViewKind


# --- confidence -------------------------------------------------------------
def test_confidence_is_ordered_low_to_high() -> None:
    order = [Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH]
    assert [c.value for c in order] == ["low", "medium", "high"]


def test_confidence_carries_no_number() -> None:
    # The mapping from a confidence label to Omega belongs to the MODEL layer.
    # Baking it in here would make "high confidence" a mathematical assumption
    # dressed as a UI label.
    assert all(isinstance(c.value, str) for c in Confidence)
    assert not any(isinstance(c.value, float) for c in Confidence)


# --- absolute views ---------------------------------------------------------
def test_an_absolute_view_states_an_expected_return() -> None:
    view = View.absolute("VOO", 0.08, Confidence.HIGH, "US earnings are resilient")

    assert view.ticker == Ticker("VOO")
    assert view.kind is ViewKind.ABSOLUTE
    assert view.expected_return == pytest.approx(0.08)
    assert view.confidence is Confidence.HIGH
    assert view.rationale == "US earnings are resilient"


def test_an_absolute_view_defaults_to_medium_confidence() -> None:
    assert View.absolute("VOO", 0.08).confidence is Confidence.MEDIUM


def test_an_absolute_view_requires_a_return() -> None:
    with pytest.raises(DomainValidationError, match="requires expected_return"):
        View(Ticker("VOO"), ViewKind.ABSOLUTE)


def test_an_absolute_view_rejects_relative_fields() -> None:
    # Silently ignoring a stray relative_to would let a user believe they had
    # expressed a comparison that the model never saw.
    with pytest.raises(DomainValidationError, match="must not set relative_to"):
        View(
            Ticker("VOO"),
            ViewKind.ABSOLUTE,
            expected_return=0.08,
            relative_to=Ticker("VEA"),
        )


def test_an_absolute_view_rejects_nan() -> None:
    with pytest.raises(DomainValidationError):
        View.absolute("VOO", float("nan"))


# --- relative views ---------------------------------------------------------
def test_a_relative_view_states_an_outperformance() -> None:
    view = View.relative("VOO", "VEA", 0.02)

    assert view.kind is ViewKind.RELATIVE
    assert view.relative_to == Ticker("VEA")
    assert view.outperforming == pytest.approx(0.02)


def test_a_relative_view_requires_a_comparison() -> None:
    with pytest.raises(DomainValidationError, match="requires relative_to"):
        View(Ticker("VOO"), ViewKind.RELATIVE, outperforming=0.02)


def test_a_relative_view_requires_an_outperformance() -> None:
    with pytest.raises(DomainValidationError, match="requires outperforming"):
        View(Ticker("VOO"), ViewKind.RELATIVE, relative_to=Ticker("VEA"))


def test_a_relative_view_cannot_compare_an_etf_to_itself() -> None:
    with pytest.raises(DomainValidationError, match="cannot compare it to itself"):
        View.relative("VOO", "VOO", 0.02)


def test_a_relative_view_rejects_an_absolute_return() -> None:
    with pytest.raises(DomainValidationError, match="must not set expected_return"):
        View(
            Ticker("VOO"),
            ViewKind.RELATIVE,
            relative_to=Ticker("VEA"),
            outperforming=0.02,
            expected_return=0.08,
        )


# --- validation and explanation ---------------------------------------------
def test_a_view_requires_a_validated_ticker() -> None:
    with pytest.raises(DomainValidationError, match="must be a Ticker"):
        View(ticker="VOO", kind=ViewKind.ABSOLUTE, expected_return=0.08)  # type: ignore[arg-type]


def test_a_view_requires_a_confidence() -> None:
    with pytest.raises(DomainValidationError, match="must be a Confidence"):
        View(
            Ticker("VOO"),
            ViewKind.ABSOLUTE,
            expected_return=0.08,
            confidence="high",  # type: ignore[arg-type]
        )


def test_a_view_is_immutable() -> None:
    view = View.absolute("VOO", 0.08)
    with pytest.raises(FrozenInstanceError):
        view.expected_return = 0.5  # type: ignore[misc]


def test_describe_uses_plain_language_and_percentages() -> None:
    # The sentence a user reads back. A percentage here, not a fraction: this is
    # presentation, and presentation is where 0.08 becomes 8%.
    absolute = View.absolute("VOO", 0.08, Confidence.HIGH)
    assert "VOO" in absolute.describe()
    assert "8.0%" in absolute.describe()
    assert "high confidence" in absolute.describe()


def test_describe_handles_a_relative_view() -> None:
    text = View.relative("VOO", "VEA", 0.02).describe()
    assert "beat VEA" in text
    assert "2.0 points" in text
    assert "%" not in text  # an excess return is points, not a percentage of capital
