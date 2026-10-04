"""API surface tests for the universe route.

The UI must enumerate from ``GET /api/universe`` rather than keeping its own
ticker list, so the payload is pinned to the canonical table here.
"""

from __future__ import annotations

from app.universe import TICKERS, supported_tickers


def test_universe_endpoint_returns_the_canonical_tickers(client) -> None:
    response = client.get("/api/universe")

    assert response.status_code == 200
    assert response.json()["tickers"] == TICKERS


def test_universe_endpoint_returns_fourteen_supported_etfs(client) -> None:
    payload = client.get("/api/universe").json()

    assert len(payload["etfs"]) == 14
    assert payload["supported_tickers"] == supported_tickers()
    assert all(etf["supported"] for etf in payload["etfs"])


def test_universe_endpoint_exposes_every_metadata_field(client) -> None:
    fields = set(client.get("/api/universe").json()["etfs"][0])

    assert fields == {
        "ticker",
        "name",
        "asset_class",
        "region",
        "currency",
        "role",
        "exposure",
        "description",
        "supported",
    }


def test_universe_endpoint_groups_by_asset_class_and_region(client) -> None:
    payload = client.get("/api/universe").json()

    assert payload["by_asset_class"] == {
        "equity": ["VOO", "SPY", "VTI", "VEA", "VWO", "STTF"],
        "high_yield": ["HYG", "JNK", "USHY"],
        "treasury": ["SHY", "IEF", "TLT"],
        "investment_grade": ["LQD"],
        "emerging_debt": ["LEMB"],
    }
    assert payload["by_region"] == {
        "us": ["VOO", "SPY", "VTI", "HYG", "JNK", "USHY", "LQD", "SHY", "IEF", "TLT"],
        "developed_ex_us": ["VEA"],
        "emerging_markets": ["VWO", "LEMB"],
        "singapore": ["STTF"],
    }


def test_universe_endpoint_reports_the_pricing_currency(client) -> None:
    # The UI cannot label or reason about a price series without knowing whether
    # it is in dollars or Singapore dollars.
    by_ticker = {e["ticker"]: e for e in client.get("/api/universe").json()["etfs"]}

    assert by_ticker["STTF"]["currency"] == "sgd"
    assert all(by_ticker[t]["currency"] == "usd" for t in by_ticker if t != "STTF")


def test_universe_endpoint_reports_counts(client) -> None:
    payload = client.get("/api/universe").json()

    assert payload["asset_class_counts"] == {
        "equity": 6,
        "high_yield": 3,
        "treasury": 3,
        "investment_grade": 1,
        "emerging_debt": 1,
    }
    assert payload["region_counts"] == {
        "us": 10,
        "developed_ex_us": 1,
        "emerging_markets": 2,
        "singapore": 1,
    }


def test_high_yield_role_is_shared_in_the_payload(client) -> None:
    by_ticker = {e["ticker"]: e for e in client.get("/api/universe").json()["etfs"]}

    assert by_ticker["HYG"]["role"] == "high_yield_credit"
    assert by_ticker["JNK"]["role"] == by_ticker["USHY"]["role"] == "high_yield_credit"
    assert len({by_ticker[t]["name"] for t in ("HYG", "JNK", "USHY")}) == 3


def test_health_endpoint(client) -> None:
    assert client.get("/health").json()["status"] == "ok"
