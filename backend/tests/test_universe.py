"""Tests for the canonical ETF universe.

One test group per validation requirement: the universe must stay exactly
fourteen supported ETFs, fully classified, with roles that explain why each ETF
exists.
"""

from __future__ import annotations

import pytest

from app.domain.types import Currency, Ticker
from app.models.universe import ETFOut
from app.providers.base import Asset, asset_from_etf
from app.taxonomy import (
    TREASURY_DURATION_ORDER,
    AssetClass,
    Exposure,
    Region,
    Role,
    duration_rank,
)
from app.universe import (
    EMERGING_DEBT,
    EQUITIES,
    HIGH_YIELD,
    INVESTMENT_GRADE,
    TICKERS,
    TREASURIES,
    UNIVERSE,
    UnsupportedTickerError,
    by_region,
    by_role,
    get,
    require_supported,
    select_tickers,
    supported_tickers,
    tickers_by_asset_class,
    treasuries_by_duration,
)

EXPECTED_TICKERS = [
    "VOO",
    "SPY",
    "VTI",
    "VEA",
    "VWO",
    "STTF",
    "HYG",
    "JNK",
    "USHY",
    "LQD",
    "SHY",
    "IEF",
    "TLT",
    "LEMB",
]


# --- exactly fourteen supported ETFs -----------------------------------------
def test_universe_contains_exactly_the_fourteen_supported_etfs() -> None:
    assert TICKERS == EXPECTED_TICKERS
    assert len(UNIVERSE) == 14


def test_exactly_fourteen_etfs_are_supported() -> None:
    assert supported_tickers() == EXPECTED_TICKERS
    assert all(etf.supported for etf in UNIVERSE.values())


def test_unsupported_etfs_are_not_silently_accepted() -> None:
    with pytest.raises(UnsupportedTickerError, match="QQQ"):
        require_supported(["VOO", "QQQ"])


def test_require_supported_rejects_an_unsupported_flagged_etf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shadowed = {
        **UNIVERSE,
        "QQQ": get("VOO").__class__(
            ticker=Ticker("QQQ"),
            name="Invesco QQQ Trust",
            asset_class=AssetClass.EQUITY,
            region=Region.US,
            currency=Currency.USD,
            role=Role.US_LARGE_CAP_CORE,
            exposure=Exposure.CORE,
            description="Nasdaq-100 tracker. Not part of the supported universe.",
            supported=False,
        ),
    }
    monkeypatch.setattr("app.universe.UNIVERSE", shadowed)

    with pytest.raises(UnsupportedTickerError) as excinfo:
        require_supported(["QQQ"])

    assert excinfo.value.tickers == ("QQQ",)
    assert "not supported" in str(excinfo.value)


def test_select_tickers_returns_universe_order_and_validates() -> None:
    assert select_tickers(["TLT", "VOO", "HYG"]) == ["VOO", "HYG", "TLT"]
    assert select_tickers(["VOO", "VOO"]) == ["VOO"]

    with pytest.raises(UnsupportedTickerError):
        select_tickers(["VOO", "EEM"])


# --- complete metadata ------------------------------------------------------
@pytest.mark.parametrize("ticker", EXPECTED_TICKERS)
def test_every_etf_has_complete_metadata(ticker: str) -> None:
    etf = get(ticker)

    assert etf.ticker == ticker
    for field in (
        "ticker",
        "name",
        "asset_class",
        "region",
        "currency",
        "role",
        "exposure",
        "description",
    ):
        value = getattr(etf, field)
        assert value is not None
        assert str(value).strip(), f"{ticker}.{field} must not be blank"

    assert isinstance(etf.supported, bool)
    assert etf.name == etf.name.strip()
    assert etf.description.endswith(".")
    assert len(etf.description.split()) >= 5


def test_tickers_are_unique_and_uppercase() -> None:
    assert len(set(TICKERS)) == len(TICKERS)
    assert all(t == t.upper() and t.isalnum() for t in TICKERS)


# --- taxonomy ---------------------------------------------------------------
def test_asset_classes_are_exactly_the_five_in_the_taxonomy() -> None:
    assert [ac.value for ac in AssetClass] == [
        "equity",
        "high_yield",
        "treasury",
        "investment_grade",
        "emerging_debt",
    ]
    assert set(EQUITIES) == {"VOO", "SPY", "VTI", "VEA", "VWO", "STTF"}
    assert set(HIGH_YIELD) == {"HYG", "JNK", "USHY"}
    assert set(INVESTMENT_GRADE) == {"LQD"}
    assert set(TREASURIES) == {"SHY", "IEF", "TLT"}
    assert set(EMERGING_DEBT) == {"LEMB"}


@pytest.mark.parametrize("ticker", EXPECTED_TICKERS)
def test_every_etf_belongs_to_exactly_one_asset_class(ticker: str) -> None:
    memberships = [ac for ac in AssetClass if ticker in tickers_by_asset_class()[ac]]
    assert len(memberships) == 1
    assert memberships[0] is get(ticker).asset_class


def test_no_unexpected_asset_classes() -> None:
    used = {etf.asset_class for etf in UNIVERSE.values()}
    assert used == set(AssetClass)


@pytest.mark.parametrize("ticker", EXPECTED_TICKERS)
def test_every_etf_has_a_defined_geographic_exposure(ticker: str) -> None:
    assert isinstance(get(ticker).region, Region)


def test_region_taxonomy_is_exactly_the_four_in_the_taxonomy() -> None:
    assert [r.value for r in Region] == [
        "us",
        "developed_ex_us",
        "emerging_markets",
        "singapore",
    ]


def test_regions_match_the_exposure_not_the_listing_venue() -> None:
    assert get("VOO").region is Region.US
    assert get("SPY").region is Region.US
    assert get("VTI").region is Region.US
    assert get("VEA").region is Region.DEVELOPED_EX_US
    assert get("VWO").region is Region.EMERGING_MARKETS

    # The US Treasury, investment-grade and high-yield markets are US markets.
    for ticker in HIGH_YIELD + INVESTMENT_GRADE + TREASURIES:
        assert get(ticker).region is Region.US


def test_emerging_debt_is_an_emerging_markets_exposure() -> None:
    # LEMB is the emerging-market bond sleeve, so it belongs with VWO rather than
    # with the US credit funds, even though it is listed and priced in dollars.
    assert get("LEMB").region is Region.EMERGING_MARKETS
    assert get("LEMB").asset_class is AssetClass.EMERGING_DEBT


def test_singapore_is_its_own_region() -> None:
    # Grouping the Straits Times ETF under a wider bucket would imply a
    # diversification claim the model cannot act on: it is Singapore, and only
    # Singapore.
    assert get("STTF").region is Region.SINGAPORE
    assert by_region(Region.SINGAPORE) == ["STTF"]


# --- currency ---------------------------------------------------------------
@pytest.mark.parametrize("ticker", EXPECTED_TICKERS)
def test_every_etf_declares_a_known_pricing_currency(ticker: str) -> None:
    assert isinstance(get(ticker).currency, Currency)


def test_only_the_singapore_etf_is_denominated_in_singapore_dollars() -> None:
    non_usd = [t for t, etf in UNIVERSE.items() if etf.currency is not Currency.USD]
    assert non_usd == ["STTF"]
    assert get("STTF").region is Region.SINGAPORE


def test_pricing_currency_is_not_the_exposure_currency() -> None:
    # LEMB holds emerging-market bonds in their local currencies but is priced in
    # dollars. Recording the trading currency keeps an SGD or local-currency
    # return series from being read as a USD one.
    assert get("LEMB").currency is Currency.USD
    assert get("USHY").currency is Currency.USD


# --- roles ------------------------------------------------------------------
@pytest.mark.parametrize("ticker", EXPECTED_TICKERS)
def test_every_etf_has_a_documented_portfolio_role(ticker: str) -> None:
    assert isinstance(get(ticker).role, Role)


def test_roles_map_to_the_documented_purpose() -> None:
    expected = {
        "VOO": Role.US_LARGE_CAP_CORE,
        "SPY": Role.US_LARGE_CAP_CORE,
        "VTI": Role.US_TOTAL_MARKET,
        "VEA": Role.DEVELOPED_INTERNATIONAL,
        "VWO": Role.EMERGING_MARKETS,
        "STTF": Role.SINGAPORE_LARGE_CAP,
        "HYG": Role.HIGH_YIELD_CREDIT,
        "JNK": Role.HIGH_YIELD_CREDIT,
        "USHY": Role.HIGH_YIELD_CREDIT,
        "LQD": Role.INVESTMENT_GRADE_CREDIT,
        "SHY": Role.SHORT_DURATION_TREASURY,
        "IEF": Role.INTERMEDIATE_TREASURY,
        "TLT": Role.LONG_DURATION_TREASURY,
        "LEMB": Role.EM_LOCAL_CURRENCY_DEBT,
    }
    assert {t: get(t).role for t in EXPECTED_TICKERS} == expected


def test_no_etf_uses_an_unused_role() -> None:
    assert {etf.role for etf in UNIVERSE.values()} == set(Role)


def test_high_yield_exposures_overlap_intentionally() -> None:
    """HYG, JNK and USHY are the same purpose, kept separate to allow comparison."""
    assert by_role(Role.HIGH_YIELD_CREDIT) == ["HYG", "JNK", "USHY"]
    assert get("HYG").role is get("JNK").role is get("USHY").role
    assert len({get(t).name for t in by_role(Role.HIGH_YIELD_CREDIT)}) == 3


def test_the_two_snp_500_trackers_share_one_role() -> None:
    """SPY and VOO track the same index, so the model treats them as one sleeve."""
    assert by_role(Role.US_LARGE_CAP_CORE) == ["VOO", "SPY"]
    assert get("VOO").asset_class is get("SPY").asset_class is AssetClass.EQUITY
    assert get("VOO").name != get("SPY").name


def test_roles_are_not_forced_unique_per_ticker() -> None:
    """Only deliberately overlapping instruments may share a role."""
    counts: dict[Role, int] = {}
    for etf in UNIVERSE.values():
        counts[etf.role] = counts.get(etf.role, 0) + 1
    shared = {role: n for role, n in counts.items() if n > 1}
    assert shared == {Role.US_LARGE_CAP_CORE: 2, Role.HIGH_YIELD_CREDIT: 3}


# --- Treasury duration ------------------------------------------------------
def test_treasuries_cover_increasing_duration() -> None:
    assert treasuries_by_duration() == ["SHY", "IEF", "TLT"]


def test_treasury_duration_ranks_are_strictly_increasing() -> None:
    ranks = [get(t).duration_rank for t in treasuries_by_duration()]
    assert ranks == [1, 2, 3]
    assert ranks == sorted(ranks)
    assert len(set(ranks)) == len(ranks)


def test_duration_rank_is_none_outside_treasuries() -> None:
    for ticker in EQUITIES + HIGH_YIELD + INVESTMENT_GRADE + EMERGING_DEBT:
        assert get(ticker).duration_rank is None
        assert duration_rank(get(ticker).role) is None


def test_duration_role_order_matches_treasury_set() -> None:
    assert set(TREASURY_DURATION_ORDER) == {
        Role.SHORT_DURATION_TREASURY,
        Role.INTERMEDIATE_TREASURY,
        Role.LONG_DURATION_TREASURY,
    }
    assert {t for role in TREASURY_DURATION_ORDER for t in by_role(role)} == set(TREASURIES)


# --- core vs satellite ------------------------------------------------------
@pytest.mark.parametrize("ticker", EXPECTED_TICKERS)
def test_every_etf_declares_core_or_satellite(ticker: str) -> None:
    assert isinstance(get(ticker).exposure, Exposure)


def test_satellite_sleeves_are_the_extra_credit_risk_ones() -> None:
    # Core = the building blocks a portfolio is built from. Satellite = a
    # deliberate, smaller add-on: speculative credit and emerging-market debt.
    satellites = [t for t, e in UNIVERSE.items() if e.exposure is Exposure.SATELLITE]
    assert satellites == ["HYG", "JNK", "USHY", "LEMB"]
    assert all(
        UNIVERSE[t].exposure is Exposure.CORE for t in EXPECTED_TICKERS if t not in satellites
    )


def test_investment_grade_credit_is_a_core_sleeve() -> None:
    # LQD sits between Treasuries and high yield: more yield, less default risk,
    # which makes it a building block rather than an add-on.
    assert get("LQD").exposure is Exposure.CORE
    assert get("LQD").asset_class is AssetClass.INVESTMENT_GRADE


# --- single canonical definition -------------------------------------------
def test_asset_from_etf_projects_onto_the_normalized_provider_type() -> None:
    asset = asset_from_etf(get("VEA"))
    assert isinstance(asset, Asset)
    assert asset.ticker == "VEA"
    assert asset.asset_class is AssetClass.EQUITY
    assert asset.region is Region.DEVELOPED_EX_US


def test_asset_from_etf_preserves_vendor_visible_fields() -> None:
    for ticker in EXPECTED_TICKERS:
        etf, asset = UNIVERSE[ticker], asset_from_etf(UNIVERSE[ticker])
        assert (asset.ticker, asset.name) == (etf.ticker, etf.name)
        assert (asset.asset_class, asset.region) == (etf.asset_class, etf.region)


def test_to_dict_is_json_ready_and_lossless() -> None:
    payload = get("TLT").to_dict()
    assert payload == {
        "ticker": "TLT",
        "name": "iShares 20+ Year Treasury Bond ETF",
        "asset_class": "treasury",
        "region": "us",
        "currency": "usd",
        "role": "long_duration_treasury",
        "exposure": "core",
        "description": get("TLT").description,
        "supported": True,
    }
    assert all(isinstance(v, (str, bool)) for v in payload.values())


def test_module_level_class_groups_partition_the_universe() -> None:
    assert EQUITIES + HIGH_YIELD + INVESTMENT_GRADE + TREASURIES + EMERGING_DEBT == TICKERS
    assert tickers_by_asset_class() == {
        AssetClass.EQUITY: EQUITIES,
        AssetClass.HIGH_YIELD: HIGH_YIELD,
        AssetClass.INVESTMENT_GRADE: INVESTMENT_GRADE,
        AssetClass.TREASURY: TREASURIES,
        AssetClass.EMERGING_DEBT: EMERGING_DEBT,
    }


def test_model_and_api_enumerate_the_same_canonical_table() -> None:
    """No layer may maintain its own ticker list."""
    from app.models.universe import universe_payload

    payload = universe_payload()

    assert payload.tickers == TICKERS
    assert payload.supported_tickers == supported_tickers()
    assert [e.ticker for e in payload.etfs] == TICKERS
    assert {e.ticker for e in payload.etfs} == set(UNIVERSE)
    assert payload.asset_class_counts == {
        AssetClass.EQUITY: 6,
        AssetClass.HIGH_YIELD: 3,
        AssetClass.TREASURY: 3,
        AssetClass.INVESTMENT_GRADE: 1,
        AssetClass.EMERGING_DEBT: 1,
    }
    assert payload.region_counts == {
        Region.US: 10,
        Region.DEVELOPED_EX_US: 1,
        Region.EMERGING_MARKETS: 2,
        Region.SINGAPORE: 1,
    }


def test_api_payload_metadata_matches_the_canonical_table() -> None:
    from app.models.universe import universe_payload

    by_ticker = {e.ticker: e for e in universe_payload().etfs}
    for ticker, etf in UNIVERSE.items():
        assert by_ticker[ticker] == ETFOut(**etf.to_dict())
