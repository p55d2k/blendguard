"""The one configuration layer.

Every runtime setting BlendGuard understands is declared here, exactly once.
Nothing else in the codebase reads ``os.environ``; application code receives a
frozen :class:`Settings` and reads typed attributes off it.

Design
------
``_EnvSource`` is a flat ``BaseSettings`` whose only job is to read the process
environment and ``.env`` file, using an explicit ``validation_alias`` per field
so each setting maps to exactly one variable name. It is private.

The public surface is :class:`Settings`: a frozen, validated, *grouped* model.
Grouping gives consumers a readable shape (``settings.market_data.provider``)
while the flat reader keeps exact control over variable names, which is exactly
what nested settings models cost.

Secrets
-------
Every credential is a :class:`~pydantic.SecretStr`, so ``repr()`` and ``str()``
render ``********``. :mod:`app.config.diagnostics` produces a dump that is safe
to log. Call ``get_secret_value()`` only at the point of use, inside the
provider that needs the credential.

Naming convention
-----------------
``BLENDGUARD_*``
    Settings BlendGuard owns.
``BLOOMBERG_*``, ``TIINGO_*``, ``FMP_*``
    Settings a vendor owns, under the vendor's own prefix, so credentials map
    one-to-one onto the vendor's documentation and can be injected verbatim by a
    deployment platform's secret store.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from app.config.environment import (
    DEFAULT_ENVIRONMENT,
    ENV_VAR,
    Environment,
    profile_for,
)

#: Repository root: <root>/backend/app/config/settings.py -> parents[3].
REPO_ROOT: Path = Path(__file__).resolve().parents[3]

#: Optional explicit override for the dotenv location.
ENV_FILE_VAR: str = "BLENDGUARD_ENV_FILE"

LogFormat = Literal["text", "json"]

T = TypeVar("T")


def default_env_files() -> tuple[Path, ...]:
    """Dotenv locations to read, in precedence order.

    ``BLENDGUARD_ENV_FILE`` overrides everything. Otherwise the repository-root
    ``.env`` is preferred over the working directory, because the documented
    setup (``cp .env.example .env``) puts it at the root while the server
    process runs from ``backend/``.
    """
    override = os.environ.get(ENV_FILE_VAR, "").strip()
    if override:
        return (Path(override).expanduser(),)
    return (REPO_ROOT / ".env", Path.cwd() / ".env")


# ---------------------------------------------------------------------------
# Public grouped settings
# ---------------------------------------------------------------------------
class LoggingSettings(BaseModel):
    """``BLENDGUARD_LOG_*``."""

    model_config = ConfigDict(frozen=True)

    level: str
    format: LogFormat


class ApiSettings(BaseModel):
    """``BLENDGUARD_API_*``."""

    model_config = ConfigDict(frozen=True)

    host: str
    port: int
    cors_origins: tuple[str, ...]


class MarketDataSettings(BaseModel):
    """``BLENDGUARD_MARKET_DATA_*``. Cache location and provider selection."""

    model_config = ConfigDict(frozen=True)

    provider: str
    cache_dir: Path
    max_age_hours: float


class FeatureFlags(BaseModel):
    """``BLENDGUARD_FEATURE_*``.

    Read by the layer that owns each flag. These are switches, not secrets, so
    they are always safe to log.
    """

    model_config = ConfigDict(frozen=True)

    scheduled_data_updates: bool
    verbose_explanations: bool


class _VendorSettings(BaseModel):
    """Shared shape for credentialed vendor integrations."""

    model_config = ConfigDict(frozen=True)

    api_key: SecretStr | None = None
    base_url: str | None = None

    @property
    def has_api_key(self) -> bool:
        return self.api_key is not None and self.api_key.get_secret_value() != ""


class BloombergSettings(_VendorSettings):
    """``BLOOMBERG_*``. Development and validation only.

    Bloomberg is never a production dependency: it must not be reachable from a
    public deployment, and its data must not be distributed. See
    ``docs/architecture.md``.

    Bloomberg has no single authentication scheme. The Desktop API
    auto-connects and needs no credentials at all, which is the usual local
    case; a hosted Server API integration instead needs an api key plus a
    client id/secret pair. Both shapes are represented so the eventual
    integration needs no change to this schema.
    """

    enabled: bool = False
    host: str = "localhost"
    port: int = 8194
    api_url: str | None = None
    client_id: SecretStr | None = None
    client_secret: SecretStr | None = None

    @property
    def has_client_credentials(self) -> bool:
        return (
            self.client_id is not None
            and self.client_id.get_secret_value() != ""
            and self.client_secret is not None
            and self.client_secret.get_secret_value() != ""
        )


class TiingoSettings(_VendorSettings):
    """``TIINGO_*``."""


class FMPSettings(_VendorSettings):
    """``FMP_*``."""


class Settings(BaseModel):
    """Fully resolved, immutable application configuration."""

    model_config = ConfigDict(frozen=True)

    environment: Environment
    logging: LoggingSettings
    api: ApiSettings
    market_data: MarketDataSettings
    features: FeatureFlags
    bloomberg: BloombergSettings
    tiingo: TiingoSettings
    fmp: FMPSettings

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.environment is Environment.TESTING


# ---------------------------------------------------------------------------
# Private flat reader
# ---------------------------------------------------------------------------
class _EnvSource(BaseSettings):
    """Flat reader over the process environment and ``.env`` file.

    Private on purpose: it exposes optional, unresolved values. Application code
    must use :class:`Settings`.
    """

    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=False,
        # Lets `overrides=` populate fields by their Python name. Environment
        # variable lookup still goes through `validation_alias`.
        populate_by_name=True,
    )

    environment: Environment = Field(default=DEFAULT_ENVIRONMENT, validation_alias=ENV_VAR)

    log_level: str | None = Field(default=None, validation_alias="BLENDGUARD_LOG_LEVEL")
    log_format: LogFormat | None = Field(default=None, validation_alias="BLENDGUARD_LOG_FORMAT")
    debug: bool | None = Field(default=None, validation_alias="BLENDGUARD_DEBUG")

    api_host: str | None = Field(default=None, validation_alias="BLENDGUARD_API_HOST")
    api_port: int | None = Field(default=None, validation_alias="BLENDGUARD_API_PORT")
    cors_origins: Annotated[list[str] | None, NoDecode] = Field(
        default=None, validation_alias="BLENDGUARD_CORS_ORIGINS"
    )

    market_data_provider: str | None = Field(
        default=None, validation_alias="BLENDGUARD_MARKET_DATA_PROVIDER"
    )
    market_data_cache_dir: Path | None = Field(
        default=None, validation_alias="BLENDGUARD_MARKET_DATA_CACHE_DIR"
    )
    market_data_max_age_hours: float | None = Field(
        default=None, validation_alias="BLENDGUARD_MARKET_DATA_MAX_AGE_HOURS"
    )

    feature_scheduled_data_updates: bool | None = Field(
        default=None, validation_alias="BLENDGUARD_FEATURE_SCHEDULED_DATA_UPDATES"
    )
    feature_verbose_explanations: bool | None = Field(
        default=None, validation_alias="BLENDGUARD_FEATURE_VERBOSE_EXPLANATIONS"
    )

    bloomberg_enabled: bool | None = Field(default=None, validation_alias="BLOOMBERG_ENABLED")
    bloomberg_host: str | None = Field(default=None, validation_alias="BLOOMBERG_HOST")
    bloomberg_port: int | None = Field(default=None, validation_alias="BLOOMBERG_PORT")
    bloomberg_api_url: str | None = Field(default=None, validation_alias="BLOOMBERG_API_URL")
    bloomberg_api_key: SecretStr | None = Field(default=None, validation_alias="BLOOMBERG_API_KEY")
    bloomberg_client_id: SecretStr | None = Field(
        default=None, validation_alias="BLOOMBERG_CLIENT_ID"
    )
    bloomberg_client_secret: SecretStr | None = Field(
        default=None, validation_alias="BLOOMBERG_CLIENT_SECRET"
    )

    tiingo_api_key: SecretStr | None = Field(default=None, validation_alias="TIINGO_API_KEY")
    tiingo_base_url: str | None = Field(default=None, validation_alias="TIINGO_BASE_URL")
    fmp_api_key: SecretStr | None = Field(default=None, validation_alias="FMP_API_KEY")
    fmp_base_url: str | None = Field(default=None, validation_alias="FMP_BASE_URL")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Accept ``a,b,c`` as well as a JSON list for list-valued variables.

        A blank value means an explicitly empty allow-list, so a same-origin
        deployment can switch CORS off without unsetting the variable.
        """
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("environment", mode="before")
    @classmethod
    def _normalize_environment(cls, value: object) -> object:
        """Accept any casing, and explain a bad name in terms of the variable.

        A typo must not silently select development defaults, so an unrecognised
        value is an error naming both the variable and the allowed values.
        """
        if not isinstance(value, str):
            return value
        candidate = value.strip().lower()
        try:
            return Environment(candidate)
        except ValueError as exc:
            allowed = ", ".join(e.value for e in Environment)
            raise ValueError(
                f"{ENV_VAR}={value!r} is not a valid environment; expected one of: {allowed}"
            ) from exc

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object, info: ValidationInfo) -> object:
        """Treat an empty variable as unset.

        Without this, the ``BLOOMBERG_API_URL=`` line in ``.env.example`` would
        override a real default with an empty string. Applies to every field so a
        newly added setting cannot forget the rule.

        ``cors_origins`` is excluded because there an empty value is meaningful:
        it means "allow no cross-origin callers".
        """
        if info.field_name == "cors_origins":
            return value
        if isinstance(value, str) and not value.strip():
            return None
        return value


class _OverrideSource(_EnvSource):
    """Reader that ignores the ambient environment entirely.

    Used by ``overrides=`` so tests never inherit a developer's shell and never
    read real credentials. Values are still parsed and validated exactly as they
    would be coming from a real environment variable.
    """

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


#: ``BaseSettings.__init__`` accepts runtime-only arguments such as ``_env_file``
#: that are not model fields. Without the pydantic mypy plugin, mypy sees a
#: field-derived ``__init__`` and rejects them, so construction is funnelled
#: through one loosely-typed helper instead of a ``type: ignore`` per call.
def _construct_source(
    source_cls: type[_EnvSource],
    env_file: Path | Sequence[Path] | None,
    values: Mapping[str, str] | None = None,
) -> _EnvSource:
    ctor: Callable[..., _EnvSource] = source_cls
    payload: dict[str, Any] = {"_env_file": env_file}
    if values:
        payload.update(values)
    return ctor(**payload)


#: Environment-variable name -> reader field name, for ``overrides``.
_FIELD_BY_ENV: dict[str, str] = {
    alias: name
    for name, field in _EnvSource.model_fields.items()
    if isinstance(alias := field.validation_alias, str)
}


def _resolve(source: _EnvSource) -> Settings:
    """Merge the reader over its environment profile into :class:`Settings`."""
    environment = source.environment
    profile = profile_for(environment)

    def pick(name: str, fallback: T) -> T:
        """Explicitly configured value if present, else the profile default."""
        value: T | None = getattr(source, name)
        return fallback if value is None else value

    return Settings(
        environment=environment,
        logging=LoggingSettings(
            level=pick("log_level", profile.log_level).upper(),
            format=pick("log_format", "text"),
        ),
        api=ApiSettings(
            host=pick("api_host", "127.0.0.1"),
            port=pick("api_port", 8000),
            cors_origins=tuple(pick("cors_origins", list(profile.cors_origins))),
        ),
        market_data=MarketDataSettings(
            provider=pick("market_data_provider", "stub").lower(),
            cache_dir=pick("market_data_cache_dir", REPO_ROOT / "data" / "cache"),
            max_age_hours=pick("market_data_max_age_hours", profile.market_data_max_age_hours),
        ),
        features=FeatureFlags(
            scheduled_data_updates=pick(
                "feature_scheduled_data_updates", profile.scheduled_data_updates
            ),
            verbose_explanations=pick("feature_verbose_explanations", profile.verbose_explanations),
        ),
        bloomberg=BloombergSettings(
            enabled=pick("bloomberg_enabled", False),
            host=pick("bloomberg_host", "localhost"),
            port=pick("bloomberg_port", 8194),
            api_url=source.bloomberg_api_url,
            api_key=source.bloomberg_api_key,
            client_id=source.bloomberg_client_id,
            client_secret=source.bloomberg_client_secret,
        ),
        tiingo=TiingoSettings(
            api_key=source.tiingo_api_key,
            base_url=source.tiingo_base_url,
        ),
        fmp=FMPSettings(
            api_key=source.fmp_api_key,
            base_url=source.fmp_base_url,
        ),
    )


def _as_paths(env_file: Path | Sequence[Path]) -> tuple[Path, ...]:
    if isinstance(env_file, Path):
        return (env_file,)
    return tuple(env_file)


def load_settings(
    env_file: Path | Sequence[Path] | None = None,
    overrides: dict[str, str] | None = None,
) -> Settings:
    """Build :class:`Settings` from the environment.

    Parameters
    ----------
    env_file:
        Dotenv path(s) to read. Defaults to :func:`default_env_files`.
    overrides:
        Environment-variable name to value, applied with the highest precedence
        and *in isolation* -- the ambient process environment and ``.env`` are
        both ignored, so a test can never pick up a developer's real
        credentials. Values are still parsed and validated as if they came from
        the environment.

    Raises
    ------
    pydantic.ValidationError
        If a value is present but invalid: unknown environment name, non-numeric
        port, unrecognised log format, negative cache age, and so on.
    ValueError
        If ``overrides`` contains a variable this layer does not own.
    """
    if overrides is not None:
        unknown = sorted(k for k in overrides if k not in _FIELD_BY_ENV)
        if unknown:
            owned = ", ".join(sorted(_FIELD_BY_ENV))
            raise ValueError(
                f"unknown configuration override(s): {', '.join(unknown)}. Known variables: {owned}"
            )
        kwargs = {_FIELD_BY_ENV[k]: v for k, v in overrides.items()}
        return _resolve(_construct_source(_OverrideSource, env_file=None, values=kwargs))

    return _resolve(
        _construct_source(
            _EnvSource, env_file=default_env_files() if env_file is None else _as_paths(env_file)
        )
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings, loaded once.

    Cached because loading touches the filesystem and is deterministic for the
    lifetime of a process. Call :func:`reset_settings_cache` after changing the
    environment in a test.
    """
    return load_settings()


def reset_settings_cache() -> None:
    """Drop the cached settings. For tests."""
    get_settings.cache_clear()
