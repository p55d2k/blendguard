"""Environment selection and per-environment profiles."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import (
    DEFAULT_ENVIRONMENT,
    Environment,
    load_settings,
    profile_for,
)


def test_defaults_to_development_when_unset() -> None:
    assert load_settings().environment is DEFAULT_ENVIRONMENT
    assert DEFAULT_ENVIRONMENT is Environment.DEVELOPMENT


@pytest.mark.parametrize("name", ["development", "testing", "production"])
def test_explicit_environment_selection(name: str) -> None:
    settings = load_settings(overrides={"BLENDGUARD_ENV": name})
    assert settings.environment == Environment(name)


def test_environment_selection_is_case_insensitive() -> None:
    assert load_settings(overrides={"BLENDGUARD_ENV": "PRODUCTION"}).environment is (
        Environment.PRODUCTION
    )


def test_unknown_environment_is_rejected_with_a_useful_message() -> None:
    with pytest.raises(ValidationError) as excinfo:
        load_settings(overrides={"BLENDGUARD_ENV": "prod"})

    message = str(excinfo.value)
    assert "BLENDGUARD_ENV" in message
    # The reader should tell the operator what was allowed, not just that it
    # failed: a typo must not silently fall back to development.
    for allowed in ("development", "testing", "production"):
        assert allowed in message


def test_profiles_differ_where_it_matters() -> None:
    development = profile_for(Environment.DEVELOPMENT)
    production = profile_for(Environment.PRODUCTION)
    testing = profile_for(Environment.TESTING)

    assert development.debug is True
    assert production.debug is False
    assert testing.debug is False

    # Tests must never reuse cached market data.
    assert testing.market_data_max_age_hours == 0.0
    assert production.market_data_max_age_hours > 0.0

    assert development.cors_origins  # local UI allowed by default
    assert production.cors_origins == ()  # nothing allowed unless configured

    # Only production demands real credentials.
    assert production.require_provider_credentials is True
    assert development.require_provider_credentials is False
    assert testing.require_provider_credentials is False


def test_every_environment_has_a_profile() -> None:
    for environment in Environment:
        assert profile_for(environment).log_level
