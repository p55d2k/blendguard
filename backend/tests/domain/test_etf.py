"""Domain layer: the ETF model and its curated table."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.domain.etf import ETF
from app.domain.types import Currency, DomainValidationError, Ticker
from app.models.universe import ETFOut
from app.taxonomy import AssetClass, Exposure, Region, Role
from app.universe import TICKERS, UNIVERSE, get


def an_etf(**overrides: object) -> ETF:
    """A minimal valid ETF, for tests that only care about one field."""
    fields: dict[str, object] = {
        "ticker": Ticker("VOO"),
        "name": "Vanguard S&P 500 ETF",
        "asset_class": AssetClass.EQUITY,
        "region": Region.US,
        "currency": Currency.USD,
        "role": Role.US_LARGE_CAP_CORE,
        "exposure": Exposure.CORE,
        "description": "US large-company stocks.",
    }
    fields.update(overrides)
    return ETF(**fields)  # type: ignore[arg-type]


# --- construction -----------------------------------------------------------
def test_an_etf_requires_a_validated_ticker() -> None:
    with pytest.raises(DomainValidationError, match="wrap it with Ticker"):
        an_etf(ticker="VOO")


def test_an_etf_requires_a_known_currency() -> None:
    # A free-form currency string would let an SGD fund be read as a USD one, so
    # the field is a closed set rather than text.
    with pytest.raises(DomainValidationError, match="currency must be a Currency"):
        an_etf(currency="SGD")


def test_an_etf_requires_a_name() -> None:
    with pytest.raises(DomainValidationError, match="name must not be empty"):
        an_etf(name="   ")


def test_an_etf_requires_a_description() -> None:
    # The description is what the user reads instead of a ticker symbol, so an
    # ETF without one cannot be explained.
    with pytest.raises(DomainValidationError, match="description must not be empty"):
        an_etf(description="")


def test_a_treasury_classification_requires_a_treasury_role() -> None:
    # Duration reasoning (short -> long ordering) reads the Treasury role. An ETF
    # claiming to be a Treasury without one would break that ordering silently.
    with pytest.raises(DomainValidationError, match="requires a Treasury role"):
        an_etf(
            ticker=Ticker("SHY"),
            asset_class=AssetClass.TREASURY,
            role=Role.US_LARGE_CAP_CORE,
        )


def test_an_etf_is_immutable() -> None:
    etf = an_etf()
    with pytest.raises(FrozenInstanceError):
        etf.name = "something else"  # type: ignore[misc]


# --- derived facts ----------------------------------------------------------
def test_duration_rank_orders_treasuries_short_to_long() -> None:
    short = UNIVERSE["SHY"].duration_rank
    medium = UNIVERSE["IEF"].duration_rank
    long = UNIVERSE["TLT"].duration_rank

    # Every Treasury must have a rank, or the short -> long ordering that the
    # optimizer relies on would silently have holes in it.
    assert short is not None and medium is not None and long is not None
    assert short < medium < long


def test_non_treasuries_have_no_duration_rank() -> None:
    assert get("VOO").duration_rank is None
    assert get("VOO").is_treasury is False
    assert get("SHY").is_treasury is True


# --- serialization ----------------------------------------------------------
def test_to_dict_is_json_ready() -> None:
    payload = get("TLT").to_dict()
    assert payload["ticker"] == "TLT"
    assert payload["asset_class"] == "treasury"
    assert payload["currency"] == "usd"
    assert payload["supported"] is True


def test_to_dict_matches_the_api_schema_field_for_field() -> None:
    # to_dict claims to be the single source for API serialization. If the two
    # drift, the UI sees two different shapes for the same ETF, so the claim is
    # checked rather than asserted in a comment.
    for ticker in TICKERS:
        assert set(get(ticker).to_dict()) == set(ETFOut.model_fields)


def test_the_domain_ticker_compares_equal_to_its_text() -> None:
    etf = get("VOO")
    assert etf.ticker == "VOO"
    assert UNIVERSE["VOO"] is etf
    assert UNIVERSE[Ticker("VOO")] is etf
