"""The ETF domain model.

Reference metadata for one supported ETF: what it is and why it exists. It
carries **no market data** -- prices and returns are separate concepts in
:mod:`app.domain.market`, and a model that mixed them would be impossible to
populate before the first price arrives.

The canonical table of instances lives in :mod:`app.universe`. This module owns
the *type*, so the API, the model, the optimizer and the tests all speak about
the same thing.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.types import (
    AssetClass,
    Currency,
    DomainValidationError,
    Exposure,
    Region,
    Role,
    Ticker,
)
from app.taxonomy import duration_rank


@dataclass(frozen=True, slots=True)
class ETF:
    """Reference metadata for one supported ETF.

    Attributes
    ----------
    ticker:
        Exchange symbol. Always a :class:`~app.domain.types.Ticker`, so a
        lowercase symbol from a provider is normalised rather than mismatched.
    name:
        Full fund name.
    asset_class:
        One of the asset classes in :mod:`app.taxonomy`.
    region:
        Broad portfolio-level geographic exposure.
    currency:
        Currency the ETF is priced in. Not the same as the exposure's currency:
        an EM local-currency bond fund listed in the US is priced in USD.
    role:
        Why the ETF exists in a portfolio. Overlapping ETFs may share a role.
    exposure:
        Core building block or satellite add-on.
    description:
        One plain-language sentence, safe to show a non-technical user.
    supported:
        Whether BlendGuard currently supports this ETF. Only supported ETFs may
        enter the optimizer.
    """

    ticker: Ticker
    name: str
    asset_class: AssetClass
    region: Region
    currency: Currency
    role: Role
    exposure: Exposure
    description: str
    supported: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.ticker, Ticker):
            raise DomainValidationError(
                f"ticker must be a Ticker, got {type(self.ticker).__name__}; "
                "wrap it with Ticker(...) so the symbol is validated"
            )
        if not isinstance(self.currency, Currency):
            raise DomainValidationError(
                f"{self.ticker}: currency must be a Currency, got {self.currency!r}"
            )
        if not self.name.strip():
            raise DomainValidationError(f"{self.ticker}: name must not be empty")
        if not self.description.strip():
            raise DomainValidationError(f"{self.ticker}: description must not be empty")
        # A Treasury role is what makes duration reasoning possible; an ETF
        # classified as a Treasury without a Treasury role would break the
        # short -> long ordering the optimizer relies on.
        if self.asset_class is AssetClass.TREASURY and duration_rank(self.role) is None:
            raise DomainValidationError(
                f"{self.ticker}: asset_class 'treasury' requires a Treasury role (got {self.role})"
            )

    @property
    def is_treasury(self) -> bool:
        return self.asset_class is AssetClass.TREASURY

    @property
    def duration_rank(self) -> int | None:
        """1 (shortest) .. 3 (longest) for Treasuries, else ``None``."""
        return duration_rank(self.role)

    def to_dict(self) -> dict[str, str | bool]:
        """Flat, JSON-ready metadata. Single source for API serialization.

        Field-for-field with :class:`app.models.universe.ETFOut`; if one gains a
        field the other must, or the UI sees two different shapes for one ETF.
        """
        return {
            "ticker": str(self.ticker),
            "name": self.name,
            "asset_class": str(self.asset_class),
            "region": str(self.region),
            "currency": str(self.currency),
            "role": str(self.role),
            "exposure": str(self.exposure),
            "description": self.description,
            "supported": self.supported,
        }
