"""Runtime environments and their per-environment defaults.

BlendGuard runs in exactly three environments. The active one is selected with
``BLENDGUARD_ENV`` and defaults to :attr:`Environment.DEVELOPMENT`.

There is one configuration *schema* for all three environments (see
:mod:`app.config.settings`). This module only holds the values that differ per
environment, so switching environments never requires a code change.

Precedence, highest first:

1. process environment variable
2. ``.env`` file
3. the profile below, for the selected environment
4. the field's schema default
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Environment(StrEnum):
    """The three supported runtime environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

    def __str__(self) -> str:
        return str(self.value)


#: Used when ``BLENDGUARD_ENV`` is unset. Safe and predictable for local work.
DEFAULT_ENVIRONMENT: Environment = Environment.DEVELOPMENT

#: Name of the variable that selects the environment.
ENV_VAR: str = "BLENDGUARD_ENV"


@dataclass(frozen=True, slots=True)
class EnvironmentProfile:
    """Values that vary by environment.

    Attributes
    ----------
    log_level:
        Root logger level for this environment.
    debug:
        Verbose error detail. Never enabled in production.
    cors_origins:
        Browser origins allowed to call the API. Empty means no cross-origin
        access, which is the safe default for a same-origin deployment.
    market_data_max_age_hours:
        How long cached end-of-day data may be reused. ``0.0`` disables reuse.
    scheduled_data_updates:
        Whether the background cache-refresh job may run.
    verbose_explanations:
        Whether allocation explanations may include model internals.
    require_provider_credentials:
        Whether startup must fail when the selected market-data provider has no
        usable credentials. See :mod:`app.config.validation`.
    """

    log_level: str
    debug: bool
    cors_origins: tuple[str, ...]
    market_data_max_age_hours: float
    scheduled_data_updates: bool
    verbose_explanations: bool
    require_provider_credentials: bool


PROFILES: dict[Environment, EnvironmentProfile] = {
    Environment.DEVELOPMENT: EnvironmentProfile(
        log_level="DEBUG",
        debug=True,
        cors_origins=("http://localhost:3000",),
        market_data_max_age_hours=12.0,
        scheduled_data_updates=True,
        verbose_explanations=True,
        require_provider_credentials=False,
    ),
    Environment.TESTING: EnvironmentProfile(
        # Quiet by default: test output should show results, not log noise.
        log_level="WARNING",
        debug=False,
        cors_origins=(),
        # Deterministic tests must never reuse cached market data.
        market_data_max_age_hours=0.0,
        scheduled_data_updates=False,
        verbose_explanations=False,
        require_provider_credentials=False,
    ),
    Environment.PRODUCTION: EnvironmentProfile(
        log_level="INFO",
        debug=False,
        # No implicit browser origins. Set BLENDGUARD_CORS_ORIGINS explicitly
        # if the consumer UI is served from a different origin.
        cors_origins=(),
        market_data_max_age_hours=24.0,
        scheduled_data_updates=True,
        verbose_explanations=False,
        require_provider_credentials=True,
    ),
}


def profile_for(environment: Environment) -> EnvironmentProfile:
    """Return the defaults for ``environment``."""
    return PROFILES[environment]
