"""DATA layer: market data providers.

All providers normalize to the same internal representation so the MODEL and
OPTIMIZER layers never see provider-specific formats.

Bloomberg, when enabled, lives in :mod:`app.providers.bloomberg` and is a
DEVELOPMENT / VALIDATION source only. Production must use a licensed or public
provider. The optimizer must never import anything Bloomberg-specific beyond the
:class:`MarketDataProvider` interface.
"""

from app.providers.base import (
    Asset,
    AssetClass,
    MarketData,
    MarketDataProvider,
    PriceSeries,
)

__all__ = [
    "Asset",
    "AssetClass",
    "MarketData",
    "MarketDataProvider",
    "PriceSeries",
]
