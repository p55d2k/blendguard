"""BlendGuard's typed domain model.

One vocabulary for the things the product reasons about, independent of any
framework: no FastAPI, no Pydantic, no pandas, no optimizer library. Everything
else in the codebase is a *layer built on top of* this package:

    DATA       app.providers   vendor payloads  -> Price, Return
    MODEL      app.optimizer   Black-Litterman and portfolio statistics
    OPTIMIZER  app.optimizer   the weights
    PRESENTATION  app.models, app.api, the web app

Two rules keep this package useful rather than merely decorative.

**No framework imports.** A domain type that needed Pydantic to exist would be
a transport concern wearing a domain costume, and the backtester and the optimizer
would inherit that dependency for no reason.

**No outbound dependencies on the app.** Nothing in :mod:`app.domain` may import
:mod:`app.providers`, :mod:`app.universe`, :mod:`app.optimizer` or
:mod:`app.models`. Where the domain needs a value the rest of the app defines,
the value lives here and the app imports it -- not the other way round.

Numeric convention: every fractional quantity is a plain fraction. ``0.25`` is
25%, never ``25``. Weights, returns, volatilities and confidence all follow it.
"""

from app.domain.constraints import (
    Constraint,
    ConstraintKind,
    ConstraintSet,
)
from app.domain.etf import ETF
from app.domain.market import Price, PriceKind, Return, ReturnFrequency
from app.domain.optimization import (
    WEIGHT_SUM_TOLERANCE,
    Allocation,
    Goal,
    OptimizationParameters,
    OptimizationRequest,
    OptimizationResult,
    OptimizationStatus,
    PortfolioMetrics,
    RiskLevel,
)
from app.domain.presets import PRESETS, Preset, PresetId, get_preset
from app.domain.types import (
    AssetClass,
    Currency,
    DomainValidationError,
    Exposure,
    Region,
    Role,
    Ticker,
)
from app.domain.views import Confidence, View, ViewKind

__all__ = [
    "ETF",
    "PRESETS",
    "WEIGHT_SUM_TOLERANCE",
    "Allocation",
    "AssetClass",
    "Confidence",
    "Constraint",
    "ConstraintKind",
    "ConstraintSet",
    "Currency",
    "DomainValidationError",
    "Exposure",
    "Goal",
    "OptimizationParameters",
    "OptimizationRequest",
    "OptimizationResult",
    "OptimizationStatus",
    "PortfolioMetrics",
    "Preset",
    "PresetId",
    "Price",
    "PriceKind",
    "Region",
    "Return",
    "ReturnFrequency",
    "RiskLevel",
    "Role",
    "Ticker",
    "View",
    "ViewKind",
    "get_preset",
]
