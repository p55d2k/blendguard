"""Configuration tests.

Every test in this package is hermetic: the ambient process environment is
cleared and the dotenv lookup is redirected to a path that does not exist, so a
developer running the suite with real Bloomberg credentials in their shell, or
with a populated `.env`, still gets the same result as CI.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from app.config import reset_settings_cache

#: Prefixes owned by the configuration layer.
CONFIG_PREFIXES = ("BLENDGUARD_", "BLOOMBERG_", "TIINGO_", "FMP_")


@pytest.fixture(autouse=True)
def isolated_config_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip every configuration variable and neutralise dotenv discovery."""
    for name in [n for n in os.environ if n.startswith(CONFIG_PREFIXES)]:
        monkeypatch.delenv(name, raising=False)

    # Redirect the dotenv lookup at a missing file so a real `.env` cannot leak
    # into the suite. Set after the sweep, since it is itself BLENDGUARD_*.
    monkeypatch.setenv(
        "BLENDGUARD_ENV_FILE", str(Path(tempfile.gettempdir()) / "absent-blendguard.env")
    )

    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture
def write_dotenv() -> Callable[[str], Path]:
    """Factory writing a temporary ``.env`` file and returning its path."""

    def _write(body: str) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".env", prefix="blendguard-cfg-", delete=False
        ) as handle:
            handle.write(body)
            return Path(handle.name)

    return _write
