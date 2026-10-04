"""Loading, precedence, coercion and the shape of :class:`Settings`."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Environment, Settings, load_settings


class TestDefaults:
    def test_development_defaults_need_no_configuration(self) -> None:
        settings = load_settings()
        assert settings.environment is Environment.DEVELOPMENT
        assert settings.logging.level == "DEBUG"
        assert settings.api.host == "127.0.0.1"
        assert settings.api.port == 8000
        assert settings.api.cors_origins == ("http://localhost:3000",)
        assert settings.market_data.provider == "stub"
        assert settings.market_data.max_age_hours == 12.0
        assert settings.bloomberg.enabled is False

    def test_production_defaults_apply_without_env_file(self) -> None:
        settings = load_settings(overrides={"BLENDGUARD_ENV": "production"})
        assert settings.logging.level == "INFO"
        assert settings.api.cors_origins == ()
        assert settings.market_data.max_age_hours == 24.0
        assert settings.features.verbose_explanations is False

    def test_testing_profile_is_quiet_and_offline(self) -> None:
        settings = load_settings(overrides={"BLENDGUARD_ENV": "testing"})
        assert settings.logging.level == "WARNING"
        assert settings.market_data.max_age_hours == 0.0
        assert settings.features.scheduled_data_updates is False


class TestOverrides:
    def test_explicit_value_beats_the_profile(self) -> None:
        settings = load_settings(
            overrides={"BLENDGUARD_ENV": "production", "BLENDGUARD_LOG_LEVEL": "error"}
        )
        assert settings.logging.level == "ERROR"

    def test_log_level_is_normalised_to_upper_case(self) -> None:
        assert load_settings(overrides={"BLENDGUARD_LOG_LEVEL": "debug"}).logging.level == "DEBUG"

    def test_provider_name_is_normalised_to_lower_case(self) -> None:
        settings = load_settings(overrides={"BLENDGUARD_MARKET_DATA_PROVIDER": "Tiingo"})
        assert settings.market_data.provider == "tiingo"

    def test_strings_are_coerced_to_numbers(self) -> None:
        settings = load_settings(
            overrides={"BLENDGUARD_API_PORT": "9001", "BLENDGUARD_MARKET_DATA_MAX_AGE_HOURS": "6"}
        )
        assert settings.api.port == 9001
        assert settings.market_data.max_age_hours == 6.0

    def test_booleans_accept_the_usual_spellings(self) -> None:
        for raw, expected in (("true", True), ("1", True), ("false", False), ("0", False)):
            settings = load_settings(overrides={"BLENDGUARD_FEATURE_VERBOSE_EXPLANATIONS": raw})
            assert settings.features.verbose_explanations is expected

    def test_unknown_override_is_rejected_with_the_known_list(self) -> None:
        with pytest.raises(ValueError) as excinfo:
            load_settings(overrides={"BLENDGUARD_NOT_A_SETTING": "x"})

        message = str(excinfo.value)
        assert "BLENDGUARD_NOT_A_SETTING" in message
        assert "BLENDGUARD_ENV" in message  # the message lists what is valid

    def test_overrides_ignore_the_ambient_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A developer with real credentials exported must not affect the result.
        monkeypatch.setenv("BLOOMBERG_API_KEY", "real-key-from-shell")
        monkeypatch.setenv("BLENDGUARD_LOG_LEVEL", "CRITICAL")
        settings = load_settings(overrides={"BLENDGUARD_ENV": "testing"})
        assert settings.bloomberg.api_key is None
        assert settings.logging.level == "WARNING"


class TestListValues:
    def test_comma_separated_origins(self) -> None:
        settings = load_settings(
            overrides={"BLENDGUARD_CORS_ORIGINS": "https://a.example, https://b.example"}
        )
        assert settings.api.cors_origins == ("https://a.example", "https://b.example")

    def test_single_origin(self) -> None:
        settings = load_settings(overrides={"BLENDGUARD_CORS_ORIGINS": "https://a.example"})
        assert settings.api.cors_origins == ("https://a.example",)

    def test_empty_value_means_no_origins(self) -> None:
        settings = load_settings(overrides={"BLENDGUARD_CORS_ORIGINS": ""})
        assert settings.api.cors_origins == ()


class TestDotenv:
    def test_reads_values_from_a_dotenv_file(self, write_dotenv: Callable[[str], Path]) -> None:
        path = write_dotenv(
            "BLENDGUARD_ENV=production\n"
            "BLENDGUARD_LOG_LEVEL=WARNING\n"
            "BLENDGUARD_MARKET_DATA_PROVIDER=tiingo\n"
        )
        settings = load_settings(env_file=path)
        assert settings.environment is Environment.PRODUCTION
        assert settings.logging.level == "WARNING"
        assert settings.market_data.provider == "tiingo"

    def test_ignores_comments_and_blank_lines(self, write_dotenv: Callable[[str], Path]) -> None:
        path = write_dotenv("# a comment\n\nBLENDGUARD_LOG_LEVEL=INFO\n\n# another comment\n")
        assert load_settings(env_file=path).logging.level == "INFO"

    def test_environment_variable_beats_the_dotenv_file(
        self, write_dotenv: Callable[[str], Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = write_dotenv("BLENDGUARD_LOG_LEVEL=WARNING\n")
        monkeypatch.setenv("BLENDGUARD_LOG_LEVEL", "ERROR")
        assert load_settings(env_file=path).logging.level == "ERROR"

    def test_env_file_variable_selects_the_file(
        self, write_dotenv: Callable[[str], Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = write_dotenv("BLENDGUARD_LOG_LEVEL=CRITICAL\n")
        monkeypatch.setenv("BLENDGUARD_ENV_FILE", str(path))
        assert load_settings().logging.level == "CRITICAL"

    def test_missing_dotenv_is_not_an_error(self, write_dotenv: Callable[[str], Path]) -> None:
        missing = write_dotenv("")
        missing.unlink()
        assert load_settings(env_file=missing).environment is Environment.DEVELOPMENT

    def test_secrets_come_from_the_dotenv_file_without_being_echoed(
        self, write_dotenv: Callable[[str], Path]
    ) -> None:
        path = write_dotenv("BLOOMBERG_API_KEY=dotenv-secret-value\n")
        settings = load_settings(env_file=path)
        assert settings.bloomberg.api_key is not None
        assert settings.bloomberg.api_key.get_secret_value() == "dotenv-secret-value"
        assert "dotenv-secret-value" not in repr(settings)


class TestImmutability:
    def test_settings_cannot_be_mutated(self) -> None:
        settings = load_settings()
        with pytest.raises(ValidationError):
            settings.api.port = 1  # type: ignore[misc]

    def test_nested_groups_cannot_be_mutated(self) -> None:
        settings = load_settings()
        with pytest.raises(ValidationError):
            settings.market_data.provider = "bloomberg"  # type: ignore[misc]


class TestInvalidValues:
    @pytest.mark.parametrize(
        ("variable", "value"),
        [
            ("BLENDGUARD_API_PORT", "not-a-port"),
            ("BLENDGUARD_LOG_FORMAT", "xml"),
            ("BLENDGUARD_MARKET_DATA_MAX_AGE_HOURS", "soon"),
            ("BLENDGUARD_ENV", "staging"),
        ],
    )
    def test_bad_values_are_rejected_at_load(self, variable: str, value: str) -> None:
        with pytest.raises(ValidationError):
            load_settings(overrides={variable: value})


def test_empty_value_is_treated_as_unset() -> None:
    # `.env.example` ships blank vendor variables; blank must not override the
    # schema default with an empty string.
    settings = load_settings(
        overrides={"BLOOMBERG_API_URL": "", "BLENDGUARD_MARKET_DATA_PROVIDER": ""}
    )
    assert settings.bloomberg.api_url is None
    assert settings.market_data.provider == "stub"


def test_cache_dir_is_a_resolved_path() -> None:
    settings = load_settings(overrides={"BLENDGUARD_MARKET_DATA_CACHE_DIR": "./data/cache"})
    assert isinstance(settings.market_data.cache_dir, Path)


def test_settings_is_a_frozen_settings_instance() -> None:
    assert isinstance(load_settings(), Settings)
