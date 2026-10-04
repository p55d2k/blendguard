"""Safe-to-log view of the configuration.

Nothing in BlendGuard prints a configuration object, a settings model, or
``os.environ`` directly. This module is the only sanctioned way to display
configuration, and it reveals *whether* a credential is present but never *what
it is*.

The dump is built from an explicit allowlist of fields rather than by walking
the model. That is deliberate: an explicit list is auditable, and a new secret
added to :mod:`app.config.settings` is redacted by default instead of silently
becoming loggable the moment someone iterates the model.
"""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from app.config.settings import Settings

#: Rendered in place of every secret value.
REDACTED = "********"


def _secret(value: SecretStr | None) -> str | None:
    """``REDACTED`` when set, ``None`` when absent. Never the value itself."""
    if value is None:
        return None
    return REDACTED if value.get_secret_value() != "" else None


def redacted_settings(settings: Settings) -> dict[str, Any]:
    """Configuration as a JSON-ready dict with every secret masked.

    Safe to log, return from a diagnostics endpoint, or snapshot in a test.
    """
    return {
        "environment": str(settings.environment),
        "logging": {
            "level": settings.logging.level,
            "format": settings.logging.format,
        },
        "api": {
            "host": settings.api.host,
            "port": settings.api.port,
            "cors_origins": list(settings.api.cors_origins),
        },
        "market_data": {
            "provider": settings.market_data.provider,
            "cache_dir": str(settings.market_data.cache_dir),
            "max_age_hours": settings.market_data.max_age_hours,
        },
        "features": {
            "scheduled_data_updates": settings.features.scheduled_data_updates,
            "verbose_explanations": settings.features.verbose_explanations,
        },
        "bloomberg": {
            "enabled": settings.bloomberg.enabled,
            "host": settings.bloomberg.host,
            "port": settings.bloomberg.port,
            "api_url": settings.bloomberg.api_url,
            "api_key": _secret(settings.bloomberg.api_key),
            "client_id": _secret(settings.bloomberg.client_id),
            "client_secret": _secret(settings.bloomberg.client_secret),
        },
        "tiingo": {
            "base_url": settings.tiingo.base_url,
            "api_key": _secret(settings.tiingo.api_key),
        },
        "fmp": {
            "base_url": settings.fmp.base_url,
            "api_key": _secret(settings.fmp.api_key),
        },
    }


def format_diagnostics(settings: Settings) -> str:
    """Human-readable, redacted, one line per setting."""
    lines: list[str] = []

    def emit(path: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                emit(f"{path}.{key}" if path else str(key), nested)
        else:
            lines.append(f"{path}={value}")

    emit("", redacted_settings(settings))
    return "\n".join(lines)
