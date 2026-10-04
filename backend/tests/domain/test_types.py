"""Domain layer: shared types and validators."""

from __future__ import annotations

import math
from datetime import date, datetime

import pytest

from app.domain.types import (
    Currency,
    DomainValidationError,
    Ticker,
    require_date,
    require_finite,
    require_non_negative,
    require_positive,
    require_unit_interval,
)


# --- Ticker -----------------------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("VOO", "VOO"),
        ("voo", "VOO"),  # case is a presentation detail, not identity
        ("Vti", "VTI"),
        ("BRK.B", "BRK.B"),  # class shares are separated by a dot
        ("BF-F", "BF-F"),  # and some by a hyphen
        ("VOO1", "VOO1"),  # digits are legal in a symbol
        ("  VOO  ", "VOO"),  # stray padding normalises rather than failing
    ],
)
def test_ticker_normalises_to_upper_case(raw: str, expected: str) -> None:
    assert Ticker(raw) == expected


def test_ticker_behaves_like_the_string_it_wraps() -> None:
    ticker = Ticker("voo")

    # The whole point of subclassing str: it stays usable as a key, a JSON value
    # and a dictionary key without a conversion step at every boundary.
    assert isinstance(ticker, str)
    assert {"VOO": 1}[ticker] == 1
    assert ticker.upper() == "VOO"
    assert json_roundtrip(ticker) == "VOO"


def json_roundtrip(value: str) -> str:
    import json

    decoded: str = json.loads(json.dumps(value))
    return decoded


@pytest.mark.parametrize(
    "raw",
    [
        "",  # empty
        " ",  # whitespace only strips to nothing
        "V OO",  # embedded space
        "-VOO",  # leading separator
        "VOO-",  # trailing separator
        "VOO.",  # separator with nothing after it
        "SPX500!",  # punctuation
        "V" * 13,  # longer than any real symbol
    ],
)
def test_ticker_rejects_malformed_symbols(raw: str) -> None:
    with pytest.raises(DomainValidationError):
        Ticker(raw)


def test_domain_validation_error_is_a_value_error() -> None:
    # Callers that already guard user input with ValueError keep working, and the
    # domain never invents a second unrelated hierarchy.
    assert issubclass(DomainValidationError, ValueError)


# --- numeric validators -----------------------------------------------------
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_require_finite_rejects_nan_and_infinity(bad: float) -> None:
    with pytest.raises(DomainValidationError):
        require_finite(bad, "x")


@pytest.mark.parametrize("bad", [True, False, None, "0.5", [0.5]])
def test_require_finite_rejects_non_numbers_and_bools(bad: object) -> None:
    with pytest.raises(DomainValidationError):
        require_finite(bad, "x")  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [True, False])
def test_bools_are_not_accepted_as_fractions(bad: bool) -> None:
    # bool subclasses int, so True would otherwise sail through as 1.0 -- a 100%
    # weight that looks perfectly valid to every downstream sum.
    with pytest.raises(DomainValidationError):
        require_unit_interval(bad, "weight")


def test_require_unit_interval_accepts_the_closed_range() -> None:
    assert require_unit_interval(0.0, "w") == 0.0
    assert require_unit_interval(1.0, "w") == 1.0
    assert require_unit_interval(0.42, "w") == pytest.approx(0.42)


@pytest.mark.parametrize("bad", [-0.01, 1.01, 25.0, 100.0])
def test_require_unit_interval_catches_percentages_and_out_of_range(bad: float) -> None:
    with pytest.raises(DomainValidationError):
        require_unit_interval(bad, "weight")


def test_percentage_error_message_names_the_likely_mistake() -> None:
    with pytest.raises(DomainValidationError, match="looks like a percentage"):
        require_unit_interval(40.0, "weight")


def test_require_non_negative_allows_zero() -> None:
    assert require_non_negative(0.0, "x") == 0.0
    with pytest.raises(DomainValidationError):
        require_non_negative(-1e-9, "x")


def test_require_positive_rejects_zero() -> None:
    assert require_positive(0.01, "price") == 0.01
    with pytest.raises(DomainValidationError):
        require_positive(0.0, "price")


def test_validators_report_the_field_that_failed() -> None:
    # An error naming the field is the difference between a one-line fix and an
    # afternoon of hunting through a solver's output.
    with pytest.raises(DomainValidationError, match=r"constraints\[VOO\]\.max_weight"):
        require_unit_interval(1.5, "constraints[VOO].max_weight")


# --- dates ------------------------------------------------------------------
def test_require_date_accepts_a_date() -> None:
    day = date(2024, 3, 15)
    assert require_date(day, "day") is day


def test_require_date_rejects_a_datetime() -> None:
    # datetime subclasses date, so this needs an explicit check: a timestamp in a
    # date field breaks day-boundary comparisons in a way nothing else catches.
    with pytest.raises(DomainValidationError, match="without a time component"):
        require_date(datetime(2024, 3, 15, 16, 0), "day")


def test_require_date_rejects_non_dates() -> None:
    with pytest.raises(DomainValidationError):
        require_date("2024-03-15", "day")  # type: ignore[arg-type]


def test_currency_is_usd_only() -> None:
    # The universe is entirely USD-denominated; widening this is a deliberate
    # decision, and it should be visible in the code rather than discovered later.
    assert [c.value for c in Currency] == ["usd"]


def test_finite_check_does_not_lose_tiny_values() -> None:
    tiny = math.nextafter(0.0, 1.0)
    assert require_finite(tiny, "x") == tiny
