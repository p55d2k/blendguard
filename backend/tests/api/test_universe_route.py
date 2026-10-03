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


def test_universe_endpoint_returns_nine_supported_etfs(client) -> None:
    payload = client.get("/api/universe").json()

    assert len(payload["etfs"]) == 9
    assert payload["supported_tickers"] == supported_tickers()
    assert all(etf["supported"] for etf in payload["etfs"])


def test_universe_endpoint_exposes_every_metadata_field(client) -> None:
    fields = set(client.get("/api/universe").json()["etfs"][0])

    assert fields == {
        "ticker",
        "name",
        "asset_class",
        "region",
        "role",
        "exposure",
        "description",
        "supported",
    }


def test_universe_endpoint_groups_by_asset_class_and_region(client) -> None:
    payload = client.get("/api/universe").json()

    assert payload["by_asset_class"] == {
        "equity": ["VOO", "VTI", "VEA", "VWO"],
        "high_yield": ["HYG", "JNK"],
        "treasury": ["SHY", "IEF", "TLT"],
    }
    assert payload["by_region"] == {
        "us": ["VOO", "VTI", "HYG", "JNK", "SHY", "IEF", "TLT"],
        "developed_ex_us": ["VEA"],
        "emerging_markets": ["VWO"],
    }


def test_universe_endpoint_reports_counts(client) -> None:
    payload = client.get("/api/universe").json()

    assert payload["asset_class_counts"] == {"equity": 4, "high_yield": 2, "treasury": 3}
    assert payload["region_counts"] == {"us": 7, "developed_ex_us": 1, "emerging_markets": 1}


def test_high_yield_role_is_shared_in_the_payload(client) -> None:
    by_ticker = {e["ticker"]: e for e in client.get("/api/universe").json()["etfs"]}

    assert by_ticker["HYG"]["role"] == by_ticker["JNK"]["role"] == "high_yield_credit"
    assert by_ticker["HYG"]["name"] != by_ticker["JNK"]["name"]


def test_health_endpoint(client) -> None:
    assert client.get("/health").json()["status"] == "ok"
