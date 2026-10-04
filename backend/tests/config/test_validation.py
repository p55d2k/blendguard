"""Startup validation.

The contract: development and testing never demand credentials; production
fails fast with a message that names the exact variable to set.
"""

from __future__ import annotations

import pytest

from app.config import ConfigurationError, load_settings, validate, validate_for_startup


class TestNonProduction:
    def test_development_needs_no_credentials(self) -> None:
        validate_for_startup(load_settings(overrides={"BLENDGUARD_ENV": "development"}))

    def test_testing_needs_no_credentials(self) -> None:
        validate_for_startup(load_settings(overrides={"BLENDGUARD_ENV": "testing"}))

    def test_testing_allows_the_stub_provider(self) -> None:
        settings = load_settings(
            overrides={"BLENDGUARD_ENV": "testing", "BLENDGUARD_MARKET_DATA_PROVIDER": "stub"}
        )
        validate_for_startup(settings)

    def test_development_allows_bloomberg_without_credentials(self) -> None:
        # The Desktop API auto-connects and needs no credentials at all.
        settings = load_settings(
            overrides={
                "BLENDGUARD_ENV": "development",
                "BLENDGUARD_MARKET_DATA_PROVIDER": "bloomberg",
                "BLOOMBERG_ENABLED": "true",
            }
        )
        validate_for_startup(settings)


class TestProductionCredentials:
    def test_stub_provider_is_rejected(self) -> None:
        settings = load_settings(overrides={"BLENDGUARD_ENV": "production"})
        with pytest.raises(ConfigurationError) as excinfo:
            validate_for_startup(settings)
        assert "stub" in str(excinfo.value)

    @pytest.mark.parametrize(
        ("provider", "variable"),
        [
            ("tiingo", "TIINGO_API_KEY"),
            ("fmp", "FMP_API_KEY"),
        ],
    )
    def test_missing_secret_names_the_variable(self, provider: str, variable: str) -> None:
        settings = load_settings(
            overrides={
                "BLENDGUARD_ENV": "production",
                "BLENDGUARD_MARKET_DATA_PROVIDER": provider,
            }
        )
        with pytest.raises(ConfigurationError) as excinfo:
            validate_for_startup(settings)
        assert variable in str(excinfo.value)

    def test_bloomberg_is_rejected_in_production_even_when_fully_configured(self) -> None:
        # Bloomberg is a development source. No amount of credential supply makes
        # it a valid production provider, so the policy check must win over the
        # credential check.
        settings = load_settings(
            overrides={
                "BLENDGUARD_ENV": "production",
                "BLENDGUARD_MARKET_DATA_PROVIDER": "bloomberg",
                "BLOOMBERG_ENABLED": "true",
                "BLOOMBERG_API_KEY": "configured",
            }
        )
        with pytest.raises(ConfigurationError) as excinfo:
            validate_for_startup(settings)
        assert "BLOOMBERG_ENABLED" in str(excinfo.value)

    def test_supplied_secret_satisfies_the_requirement(self) -> None:
        settings = load_settings(
            overrides={
                "BLENDGUARD_ENV": "production",
                "BLENDGUARD_MARKET_DATA_PROVIDER": "tiingo",
                "TIINGO_API_KEY": "a-real-looking-key",
            }
        )
        validate_for_startup(settings)

    def test_blank_secret_does_not_count_as_supplied(self) -> None:
        settings = load_settings(
            overrides={
                "BLENDGUARD_ENV": "production",
                "BLENDGUARD_MARKET_DATA_PROVIDER": "tiingo",
                "TIINGO_API_KEY": "",
            }
        )
        with pytest.raises(ConfigurationError) as excinfo:
            validate_for_startup(settings)
        assert "TIINGO_API_KEY" in str(excinfo.value)

    def test_uncredentialed_provider_is_allowed_in_production(self) -> None:
        # No provider is declared credentialed, so requiring one would be wrong.
        settings = load_settings(
            overrides={
                "BLENDGUARD_ENV": "production",
                "BLENDGUARD_MARKET_DATA_PROVIDER": "some-licensed-feed",
            }
        )
        validate_for_startup(settings)


class TestInvariants:
    def test_bloomberg_cannot_be_enabled_in_production(self) -> None:
        settings = load_settings(
            overrides={"BLENDGUARD_ENV": "production", "BLOOMBERG_ENABLED": "true"}
        )
        with pytest.raises(ConfigurationError) as excinfo:
            validate_for_startup(settings)
        assert "BLOOMBERG_ENABLED" in str(excinfo.value)

    def test_bloomberg_provider_requires_the_provider_enabled(self) -> None:
        settings = load_settings(
            overrides={
                "BLENDGUARD_ENV": "development",
                "BLENDGUARD_MARKET_DATA_PROVIDER": "bloomberg",
                "BLOOMBERG_ENABLED": "false",
            }
        )
        with pytest.raises(ConfigurationError) as excinfo:
            validate(settings)
        assert "BLOOMBERG_ENABLED" in str(excinfo.value)

    def test_negative_cache_age_is_rejected(self) -> None:
        settings = load_settings(overrides={"BLENDGUARD_MARKET_DATA_MAX_AGE_HOURS": "-1"})
        with pytest.raises(ConfigurationError) as excinfo:
            validate(settings)
        assert "BLENDGUARD_MARKET_DATA_MAX_AGE_HOURS" in str(excinfo.value)

    @pytest.mark.parametrize("port", ["0", "70000"])
    def test_out_of_range_port_is_rejected(self, port: str) -> None:
        settings = load_settings(overrides={"BLENDGUARD_API_PORT": port})
        with pytest.raises(ConfigurationError) as excinfo:
            validate(settings)
        assert "BLENDGUARD_API_PORT" in str(excinfo.value)

    def test_valid_settings_pass(self) -> None:
        validate(load_settings())


def test_error_messages_never_contain_a_secret_value() -> None:
    settings = load_settings(
        overrides={
            "BLENDGUARD_ENV": "production",
            "BLENDGUARD_MARKET_DATA_PROVIDER": "tiingo",
            "TIINGO_API_KEY": "super-secret-value",
            "BLOOMBERG_ENABLED": "true",
        }
    )
    with pytest.raises(ConfigurationError) as excinfo:
        validate_for_startup(settings)
    assert "super-secret-value" not in str(excinfo.value)
