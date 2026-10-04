"""Configuration validation.

Fails loudly and early. The goal is that a missing or contradictory setting
surfaces as one clear sentence at startup, not as an obscure authentication or
network error twenty minutes into a request.

Policy
------
* Development and testing never require production credentials. The test suite
  must run with no Bloomberg Terminal and no API keys.
* Production requires the *selected* provider to be usable. Requiring every
  vendor's credentials at once would be wrong, and would leak which vendors
  BlendGuard is wired to.
* Secrets are never substituted with fake values. A placeholder credential is
  worse than a clear failure: it becomes an authentication error later.
"""

from __future__ import annotations

from app.config.environment import profile_for
from app.config.settings import Settings

#: Providers that must never serve a public deployment. ``stub`` returns
#: synthetic prices; letting it reach production would publish invented market
#: data as if it were real.
NON_PRODUCTION_PROVIDERS: frozenset[str] = frozenset({"stub"})

#: Provider name -> environment variables that provider needs before use.
#: Only the selected provider is checked.
REQUIRED_CREDENTIALS: dict[str, tuple[str, ...]] = {
    "bloomberg": ("BLOOMBERG_API_KEY",),
    "tiingo": ("TIINGO_API_KEY",),
    "fmp": ("FMP_API_KEY",),
}


class ConfigurationError(RuntimeError):
    """Raised when configuration is missing, invalid or self-contradictory."""


def _is_supplied(settings: Settings, variable: str) -> bool:
    """Whether ``variable`` was supplied with a non-empty value."""
    match variable:
        case "BLOOMBERG_API_KEY":
            return settings.bloomberg.api_key is not None
        case "TIINGO_API_KEY":
            return settings.tiingo.has_api_key
        case "FMP_API_KEY":
            return settings.fmp.has_api_key
        case _:  # pragma: no cover - guards against a typo in the table above
            return False


def validate(settings: Settings) -> None:
    """Environment-independent invariants.

    Raises
    ------
    ConfigurationError
        On the first violated invariant.
    """
    if settings.market_data.max_age_hours < 0:
        raise ConfigurationError(
            "BLENDGUARD_MARKET_DATA_MAX_AGE_HOURS must be >= 0 "
            f"(got {settings.market_data.max_age_hours})"
        )
    if not 1 <= settings.api.port <= 65535:
        raise ConfigurationError(
            f"BLENDGUARD_API_PORT must be between 1 and 65535 (got {settings.api.port})"
        )
    if settings.market_data.provider == "bloomberg" and not settings.bloomberg.enabled:
        raise ConfigurationError(
            "BLENDGUARD_MARKET_DATA_PROVIDER is 'bloomberg' but BLOOMBERG_ENABLED is false. "
            "Set BLOOMBERG_ENABLED=true, or choose a different provider."
        )
    if settings.is_production and settings.bloomberg.enabled:
        raise ConfigurationError(
            "BLOOMBERG_ENABLED must be false in production. Bloomberg is a development and "
            "validation source only, and its data must not reach a public deployment."
        )


def validate_for_startup(settings: Settings) -> None:
    """Everything in :func:`validate`, plus production credential requirements.

    Called once at application start. Raises :class:`ConfigurationError` naming
    the exact environment variable that is missing.
    """
    validate(settings)

    if not profile_for(settings.environment).require_provider_credentials:
        return

    provider = settings.market_data.provider

    if provider in NON_PRODUCTION_PROVIDERS:
        raise ConfigurationError(
            f"Production configuration cannot use the {provider!r} market-data provider: "
            "it returns synthetic prices, not market data. Set BLENDGUARD_MARKET_DATA_PROVIDER "
            "to a real licensed provider and supply its credentials."
        )

    missing = [v for v in REQUIRED_CREDENTIALS.get(provider, ()) if not _is_supplied(settings, v)]
    if missing:
        raise ConfigurationError(
            f"Production configuration requires {', '.join(missing)} for market-data provider "
            f"{provider!r}. Inject it as an environment variable via your deployment "
            f"platform's secret store; never commit it."
        )
