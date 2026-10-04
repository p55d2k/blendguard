"""Domain layer: price and return observations.

The arithmetic here is checked against values worked out by hand. These are the
first calculations in the pipeline, so an error here propagates into covariance,
into Black-Litterman, and into a portfolio a user is shown as advice.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.domain.market import Price, PriceKind, Return, ReturnFrequency
from app.domain.types import Currency, DomainValidationError, Ticker


# --- Price ------------------------------------------------------------------
def test_a_price_must_be_positive() -> None:
    # A zero price is not a data point to be handled downstream; it is a division
    # by zero waiting for the return calculation.
    with pytest.raises(DomainValidationError, match="must be > 0"):
        Price(Ticker("VOO"), date(2024, 1, 2), 0.0)


def test_a_price_rejects_a_negative_value() -> None:
    with pytest.raises(DomainValidationError):
        Price(Ticker("VOO"), date(2024, 1, 2), -1.0)


def test_a_price_rejects_a_datetime() -> None:
    with pytest.raises(DomainValidationError):
        Price(Ticker("VOO"), datetime(2024, 1, 2, 16, 0), 100.0)


def test_a_price_defaults_to_adjusted_close_in_usd() -> None:
    price = Price(Ticker("VOO"), date(2024, 1, 2), 100.0)
    assert price.kind is PriceKind.ADJUSTED_CLOSE
    assert price.currency is Currency.USD


# --- simple returns ---------------------------------------------------------
def test_simple_return_is_the_documented_formula() -> None:
    # 110 / 100 - 1 = 0.10
    previous = Price(Ticker("VOO"), date(2024, 1, 2), 100.0)
    current = Price(Ticker("VOO"), date(2024, 3, 1), 110.0)

    assert current.simple_return_to(previous) == pytest.approx(0.10)


def test_a_falling_price_gives_a_negative_return() -> None:
    previous = Price(Ticker("VOO"), date(2024, 1, 2), 100.0)
    current = Price(Ticker("VOO"), date(2024, 3, 1), 75.0)

    assert current.simple_return_to(previous) == pytest.approx(-0.25)


def test_returns_are_fractions_not_percentages() -> None:
    # Guards the single most consequential convention in the codebase.
    previous = Price(Ticker("VOO"), date(2024, 1, 2), 100.0)
    current = Price(Ticker("VOO"), date(2024, 3, 1), 110.0)

    assert current.simple_return_to(previous) < 1.0


def test_a_return_cannot_move_backwards_in_time() -> None:
    earlier = Price(Ticker("VOO"), date(2024, 1, 2), 110.0)
    later = Price(Ticker("VOO"), date(2024, 3, 1), 100.0)

    with pytest.raises(DomainValidationError, match="forward in time"):
        earlier.simple_return_to(later)


def test_a_return_needs_two_dates_in_order() -> None:
    same_day = Price(Ticker("VOO"), date(2024, 1, 2), 100.0)

    with pytest.raises(DomainValidationError, match="forward in time"):
        same_day.simple_return_to(same_day)


def test_a_return_cannot_cross_tickers() -> None:
    previous = Price(Ticker("VOO"), date(2024, 1, 2), 100.0)
    current = Price(Ticker("VTI"), date(2024, 3, 1), 110.0)

    with pytest.raises(DomainValidationError, match="cannot compute a return"):
        current.simple_return_to(previous)


def test_a_return_cannot_mix_adjusted_and_raw_prices() -> None:
    # Mixing a dividend-adjusted close with a raw close produces a return that
    # looks plausible and is not. Refusing is the only safe option.
    previous = Price(Ticker("VOO"), date(2024, 1, 2), 100.0, kind=PriceKind.RAW_CLOSE)
    current = Price(Ticker("VOO"), date(2024, 3, 1), 110.0, kind=PriceKind.ADJUSTED_CLOSE)

    with pytest.raises(DomainValidationError, match="cannot mix"):
        current.simple_return_to(previous)


# --- Return -----------------------------------------------------------------
def test_a_return_may_be_negative() -> None:
    # Unlike a weight or a price, a return is supposed to go down.
    assert Return(Ticker("VOO"), date(2024, 1, 3), -0.023).value == pytest.approx(-0.023)


def test_a_return_cannot_be_a_total_loss_or_worse() -> None:
    # -1 is a total loss: the series could never recover, and a sample containing
    # one is degenerate rather than merely extreme. Refused rather than averaged.
    with pytest.raises(DomainValidationError, match="greater than -1"):
        Return(Ticker("VOO"), date(2024, 1, 3), -1.0)

    with pytest.raises(DomainValidationError, match="greater than -1"):
        Return(Ticker("VOO"), date(2024, 1, 3), -1.01)


def test_a_return_is_not_capped_at_1() -> None:
    # A doubling is a +100% return. Capping this at 1.0 would quietly discard the
    # best days in a sample and bias every volatility estimate downwards.
    assert Return(Ticker("VOO"), date(2024, 1, 3), 3.0).value == 3.0


def test_a_return_rejects_nan() -> None:
    with pytest.raises(DomainValidationError):
        Return(Ticker("VOO"), date(2024, 1, 3), float("nan"))


def test_as_percent_is_for_display_only() -> None:
    assert Return(Ticker("VOO"), date(2024, 1, 3), 0.075).as_percent() == pytest.approx(7.5)


def test_returns_default_to_daily() -> None:
    assert Return(Ticker("VOO"), date(2024, 1, 3), 0.01).frequency is ReturnFrequency.DAILY
