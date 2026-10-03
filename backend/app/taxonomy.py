"""Classification vocabulary shared by the DATA, MODEL, and PRESENTATION layers.

The taxonomy is deliberately small and lives in exactly one place so the model,
the API, and the UI cannot drift apart. Everything here is a stable string
value: the wire format and the values used in configuration and tests are the
enum member values.

Do not add categories opportunistically. New asset classes, regions, or roles
are deliberate universe-expansion changes.
"""

from __future__ import annotations

from enum import StrEnum


class AssetClass(StrEnum):
    """The three initial asset classes."""

    EQUITY = "equity"
    HIGH_YIELD = "high_yield"
    TREASURY = "treasury"


class Region(StrEnum):
    """Broad portfolio-level geographic exposure.

    Countries, currency exposure, and sectors are intentionally not modelled.
    Fixed-income ETFs are all ``US`` because the initial Treasury and high-yield
    universe represents the US fixed-income market.
    """

    US = "us"
    DEVELOPED_EX_US = "developed_ex_us"
    EMERGING_MARKETS = "emerging_markets"


class Exposure(StrEnum):
    """Whether an ETF is a core building block or a satellite add-on."""

    CORE = "core"
    SATELLITE = "satellite"


class Role(StrEnum):
    """Why an ETF exists in a portfolio.

    Roles let the model reason about *purpose* rather than ticker identity.
    Overlapping ETFs deliberately share a role: ``HYG`` and ``JNK`` are both
    ``HIGH_YIELD_CREDIT``. Roles are not forced to be unique per ticker.
    """

    US_LARGE_CAP_CORE = "us_large_cap_core"
    US_TOTAL_MARKET = "us_total_market"
    DEVELOPED_INTERNATIONAL = "developed_international"
    EMERGING_MARKETS = "emerging_markets"
    HIGH_YIELD_CREDIT = "high_yield_credit"
    SHORT_DURATION_TREASURY = "short_duration_treasury"
    INTERMEDIATE_TREASURY = "intermediate_treasury"
    LONG_DURATION_TREASURY = "long_duration_treasury"


#: Treasury roles ordered by increasing interest-rate duration.
TREASURY_DURATION_ORDER: tuple[Role, ...] = (
    Role.SHORT_DURATION_TREASURY,
    Role.INTERMEDIATE_TREASURY,
    Role.LONG_DURATION_TREASURY,
)

_DURATION_RANK: dict[Role, int] = {role: i + 1 for i, role in enumerate(TREASURY_DURATION_ORDER)}


def duration_rank(role: Role) -> int | None:
    """Return 1 (shortest) .. 3 (longest) for Treasury roles, else ``None``.

    Useful for explaining why a Treasury ETF got a larger or smaller weight,
    and for asserting that duration is represented monotonically.
    """
    return _DURATION_RANK.get(role)
