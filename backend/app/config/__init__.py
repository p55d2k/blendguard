"""Configuration layer.

The single boundary between the process environment and the rest of the
application. Application code imports from here and nowhere else; no module
outside this package reads ``os.environ``.

Typical use::

    from app.config import get_settings

    settings = get_settings()
    if settings.features.verbose_explanations:
        ...

At startup the application validates configuration and fails loudly rather than
deferring the error to the first request::

    from app.config import get_settings, validate_for_startup

    settings = get_settings()
    validate_for_startup(settings)

See ``.env.example`` for the documented variables and ``docs/architecture.md``
for the layering rules.
"""

from __future__ import annotations

from app.config.diagnostics import REDACTED, format_diagnostics, redacted_settings
from app.config.environment import (
    DEFAULT_ENVIRONMENT,
    ENV_VAR,
    Environment,
    EnvironmentProfile,
    profile_for,
)
from app.config.settings import (
    ENV_FILE_VAR,
    REPO_ROOT,
    ApiSettings,
    BloombergSettings,
    FeatureFlags,
    FMPSettings,
    LoggingSettings,
    MarketDataSettings,
    Settings,
    TiingoSettings,
    default_env_files,
    get_settings,
    load_settings,
    reset_settings_cache,
)
from app.config.validation import (
    NON_PRODUCTION_PROVIDERS,
    REQUIRED_CREDENTIALS,
    ConfigurationError,
    validate,
    validate_for_startup,
)

__all__ = [
    "DEFAULT_ENVIRONMENT",
    "ENV_FILE_VAR",
    "ENV_VAR",
    "NON_PRODUCTION_PROVIDERS",
    "REDACTED",
    "REPO_ROOT",
    "REQUIRED_CREDENTIALS",
    "ApiSettings",
    "BloombergSettings",
    "ConfigurationError",
    "Environment",
    "EnvironmentProfile",
    "FMPSettings",
    "FeatureFlags",
    "LoggingSettings",
    "MarketDataSettings",
    "Settings",
    "TiingoSettings",
    "default_env_files",
    "format_diagnostics",
    "get_settings",
    "load_settings",
    "profile_for",
    "redacted_settings",
    "reset_settings_cache",
    "validate",
    "validate_for_startup",
]
