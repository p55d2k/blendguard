"""Tests for the canonical ETF universe.

One test group per validation requirement: the universe must stay exactly nine
supported ETFs, fully classified, with roles that explain why each ETF exists.
"""

from __future__ import annotations

import pytest

from app.models.universe import ETFOut
from app.providers.base import Asset
from app.taxonomy import (
    TREASURY_DURATION_ORDER,
    AssetClass,
    Exposure,
    Region,
    Role,
    duration_rank,
)
from app.universe import (
    EQUITIES,
    HIGH_YIELD,
    TICKERS,
    TREASURIES,
    UNIVERSE,
    UnsupportedTickerError,
    by_role,
    get,
    require_supported,
    select_tickers,
    supported_tickers,
    tickers_by_asset_class,
    treasuries_by_duration,
)

EXPECTED_TICKERS = ["VOO", "VTI", "VEA", "VWO", "HYG", "JNK", "SHY", "IEF", "TLT"]


# --- exactly nine supported ETFs --------------------------------------------
def test_universe_contains_exactly_the_nine_initial_etfs() -> None:
    assert TICKERS == EXPECTED_TICKERS
    assert len(UNIVERSE) == 9


def test_exactly_nine_etfs_are_supported() -> None:
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
            ticker="QQQ",
            name="Invesco QQQ Trust",
            asset_class=AssetClass.EQUITY,
            region=Region.US,
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
        select_tickers(["VOO", "SPY"])


# --- complete metadata ------------------------------------------------------
@pytest.mark.parametrize("ticker", EXPECTED_TICKERS)
def test_every_etf_has_complete_metadata(ticker: str) -> None:
    etf = get(ticker)

    assert etf.ticker == ticker
    for field in ("ticker", "name", "asset_class", "region", "role", "exposure", "description"):
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
def test_asset_classes_are_exactly_the_three_initial_ones() -> None:
    assert [ac.value for ac in AssetClass] == ["equity", "high_yield", "treasury"]
    assert set(EQUITIES) == {"VOO", "VTI", "VEA", "VWO"}
    assert set(HIGH_YIELD) == {"HYG", "JNK"}
    assert set(TREASURIES) == {"SHY", "IEF", "TLT"}


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


def test_region_taxonomy_is_exactly_the_three_initial_ones() -> None:
    assert [r.value for r in Region] == ["us", "developed_ex_us", "emerging_markets"]


def test_equity_regions_and_fixed_income_region() -> None:
    assert get("VOO").region is Region.US
    assert get("VTI").region is Region.US
    assert get("VEA").region is Region.DEVELOPED_EX_US
    assert get("VWO").region is Region.EMERGING_MARKETS

    # The initial Treasury and high-yield universe is the US fixed-income market.
    for ticker in HIGH_YIELD + TREASURIES:
        assert get(ticker).region is Region.US


# --- roles ------------------------------------------------------------------
@pytest.mark.parametrize("ticker", EXPECTED_TICKERS)
def test_every_etf_has_a_documented_portfolio_role(ticker: str) -> None:
    assert isinstance(get(ticker).role, Role)


def test_roles_map_to_the_documented_purpose() -> None:
    expected = {
        "VOO": Role.US_LARGE_CAP_CORE,
        "VTI": Role.US_TOTAL_MARKET,
        "VEA": Role.DEVELOPED_INTERNATIONAL,
        "VWO": Role.EMERGING_MARKETS,
        "HYG": Role.HIGH_YIELD_CREDIT,
        "JNK": Role.HIGH_YIELD_CREDIT,
        "SHY": Role.SHORT_DURATION_TREASURY,
        "IEF": Role.INTERMEDIATE_TREASURY,
        "TLT": Role.LONG_DURATION_TREASURY,
    }
    assert {t: get(t).role for t in EXPECTED_TICKERS} == expected


def test_no_etf_uses_an_unused_role() -> None:
    assert {etf.role for etf in UNIVERSE.values()} == set(Role)


def test_high_yield_exposures_overlap_intentionally() -> None:
    """HYG and JNK are the same purpose, kept separate to allow comparison."""
    assert by_role(Role.HIGH_YIELD_CREDIT) == ["HYG", "JNK"]
    assert get("HYG").role is get("JNK").role
    assert get("HYG").name != get("JNK").name


def test_roles_are_not_forced_unique_per_ticker() -> None:
    """Only the high-yield pair may share a role; everything else is distinct."""
    counts: dict[Role, int] = {}
    for etf in UNIVERSE.values():
        counts[etf.role] = counts.get(etf.role, 0) + 1
    shared = {role: n for role, n in counts.items() if n > 1}
    assert shared == {Role.HIGH_YIELD_CREDIT: 2}


# --- Treasury duration ------------------------------------------------------
def test_treasuries_cover_increasing_duration() -> None:
    assert treasuries_by_duration() == ["SHY", "IEF", "TLT"]


def test_treasury_duration_ranks_are_strictly_increasing() -> None:
    ranks = [get(t).duration_rank for t in treasuries_by_duration()]
    assert ranks == [1, 2, 3]
    assert ranks == sorted(ranks)
    assert len(set(ranks)) == len(ranks)


def test_duration_rank_is_none_outside_treasuries() -> None:
    for ticker in EQUITIES + HIGH_YIELD:
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


def test_high_yield_is_the_only_satellite_sleeve() -> None:
    satellites = [t for t, e in UNIVERSE.items() if e.exposure is Exposure.SATELLITE]
    assert satellites == ["HYG", "JNK"]
    assert all(
        UNIVERSE[t].exposure is Exposure.CORE for t in EXPECTED_TICKERS if t not in satellites
    )


# --- single canonical definition -------------------------------------------
def test_to_asset_projects_onto_the_normalized_provider_type() -> None:
    asset = get("VEA").to_asset()
    assert isinstance(asset, Asset)
    assert asset.ticker == "VEA"
    assert asset.asset_class is AssetClass.EQUITY
    assert asset.region is Region.DEVELOPED_EX_US


def test_to_asset_preserves_vendor_visible_fields() -> None:
    for ticker in EXPECTED_TICKERS:
        etf, asset = UNIVERSE[ticker], UNIVERSE[ticker].to_asset()
        assert (asset.ticker, asset.name) == (etf.ticker, etf.name)
        assert (asset.asset_class, asset.region) == (etf.asset_class, etf.region)


def test_to_dict_is_json_ready_and_lossless() -> None:
    payload = get("TLT").to_dict()
    assert payload == {
        "ticker": "TLT",
        "name": "iShares 20+ Year Treasury Bond ETF",
        "asset_class": "treasury",
        "region": "us",
        "role": "long_duration_treasury",
        "exposure": "core",
        "description": get("TLT").description,
        "supported": True,
    }
    assert all(isinstance(v, (str, bool)) for v in payload.values())


def test_module_level_class_groups_partition_the_universe() -> None:
    assert EQUITIES + HIGH_YIELD + TREASURIES == TICKERS
    assert tickers_by_asset_class() == {
        AssetClass.EQUITY: EQUITIES,
        AssetClass.HIGH_YIELD: HIGH_YIELD,
        AssetClass.TREASURY: TREASURIES,
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
        AssetClass.EQUITY: 4,
        AssetClass.HIGH_YIELD: 2,
        AssetClass.TREASURY: 3,
    }
    assert payload.region_counts == {
        Region.US: 7,
        Region.DEVELOPED_EX_US: 1,
        Region.EMERGING_MARKETS: 1,
    }


def test_api_payload_metadata_matches_the_canonical_table() -> None:
    from app.models.universe import universe_payload

    by_ticker = {e.ticker: e for e in universe_payload().etfs}
    for ticker, etf in UNIVERSE.items():
        assert by_ticker[ticker] == ETFOut(**etf.to_dict())
