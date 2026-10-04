"""Secret redaction.

A secret must never appear in a log line, a diagnostics dump, a repr, or an
error message. These tests use an unmistakable marker value so an accidental
leak cannot hide behind something that looks like a real credential.
"""

from __future__ import annotations

import json

from app.config import REDACTED, format_diagnostics, load_settings, redacted_settings

#: Deliberately not a plausible credential, so a failure points at the leak.
MARKER = "LEAK-CANARY-9f3a2b"

_ALL_SECRETS = {
    "BLENDGUARD_ENV": "production",
    "BLOOMBERG_API_KEY": MARKER,
    "BLOOMBERG_CLIENT_ID": MARKER,
    "BLOOMBERG_CLIENT_SECRET": MARKER,
    "TIINGO_API_KEY": MARKER,
    "FMP_API_KEY": MARKER,
}


def _settings():
    return load_settings(overrides=_ALL_SECRETS)


def test_every_secret_is_redacted_in_the_dump() -> None:
    dump = redacted_settings(_settings())
    assert dump["bloomberg"]["api_key"] == REDACTED  # type: ignore[index]
    assert dump["bloomberg"]["client_id"] == REDACTED  # type: ignore[index]
    assert dump["bloomberg"]["client_secret"] == REDACTED  # type: ignore[index]
    assert dump["tiingo"]["api_key"] == REDACTED  # type: ignore[index]
    assert dump["fmp"]["api_key"] == REDACTED  # type: ignore[index]


def test_the_marker_never_appears_in_the_dump() -> None:
    serialised = json.dumps(redacted_settings(_settings()))
    assert MARKER not in serialised


def test_the_marker_never_appears_in_the_text_dump() -> None:
    assert MARKER not in format_diagnostics(_settings())


def test_the_marker_never_appears_in_repr() -> None:
    assert MARKER not in repr(_settings())


def test_the_marker_never_appears_in_str_of_a_secret() -> None:
    key = _settings().bloomberg.api_key
    assert key is not None
    assert MARKER not in str(key)


def test_absent_secrets_are_reported_as_absent_not_blanked() -> None:
    dump = redacted_settings(load_settings(overrides={"BLENDGUARD_ENV": "testing"}))
    assert dump["bloomberg"]["api_key"] is None  # type: ignore[index]
    assert dump["tiingo"]["api_key"] is None  # type: ignore[index]


def test_blank_secret_is_reported_as_absent() -> None:
    dump = redacted_settings(load_settings(overrides={"TIINGO_API_KEY": ""}))
    assert dump["tiingo"]["api_key"] is None  # type: ignore[index]


def test_non_secret_settings_are_still_visible() -> None:
    dump = redacted_settings(
        load_settings(overrides={"BLENDGUARD_ENV": "testing", "BLENDGUARD_API_PORT": "9100"})
    )
    assert dump["environment"] == "testing"
    assert dump["api"]["port"] == 9100  # type: ignore[index]
    assert dump["market_data"]["provider"] == "stub"  # type: ignore[index]


def test_text_dump_names_every_variable_group() -> None:
    text = format_diagnostics(_settings())
    for prefix in ("environment=", "logging.", "api.", "market_data.", "features."):
        assert prefix in text
    assert "bloomberg.api_key=********" in text
