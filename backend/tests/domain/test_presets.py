"""Domain layer: role-based presets."""

from __future__ import annotations

import pytest

from app.domain.constraints import Constraint, ConstraintSet
from app.domain.presets import PRESETS, Preset, PresetId, get_preset
from app.domain.types import AssetClass, DomainValidationError, Ticker
from app.domain.views import Confidence, View


def test_the_three_initial_presets_exist() -> None:
    assert set(PRESETS) == {
        PresetId.CONSERVATIVE,
        PresetId.BALANCED,
        PresetId.GROWTH,
    }


@pytest.mark.parametrize("preset_id", [PresetId.CONSERVATIVE, PresetId.BALANCED, PresetId.GROWTH])
def test_every_preset_has_a_name_and_a_plain_description(preset_id: str) -> None:
    preset = get_preset(preset_id)
    assert preset.name
    assert preset.description
    assert preset.description.endswith(".")


@pytest.mark.parametrize("preset_id", [PresetId.CONSERVATIVE, PresetId.BALANCED, PresetId.GROWTH])
def test_preset_descriptions_do_not_promise_an_outcome(preset_id: str) -> None:
    # These are product presets, not financial truths. A description that reads as
    # a promise turns a preference into advice, which is explicitly out of scope.
    preset = get_preset(preset_id)
    lowered = preset.description.lower()
    for promise in ("guarantee", "will return", "best", "safest", "optimal"):
        assert promise not in lowered


def test_preset_constraints_are_empty_until_the_numbers_are_decided() -> None:
    # A plausible-looking constraint number that nobody chose on purpose is worse
    # than no constraint at all: it silently limits a user's portfolio. The
    # financial assumptions are a separate, deliberate change.
    for preset_id, preset in PRESETS.items():
        assert len(preset.constraints) == 0, f"{preset_id} has constraints nobody documented"


def test_an_unknown_preset_names_the_alternatives() -> None:
    with pytest.raises(KeyError, match="conservative"):
        get_preset("aggressive")


def test_a_preset_defaults_to_medium_confidence() -> None:
    assert get_preset(PresetId.BALANCED).default_confidence is Confidence.MEDIUM


def test_a_preset_requires_an_id_and_a_name() -> None:
    with pytest.raises(DomainValidationError, match="id must not be empty"):
        Preset(id="", name="Balanced", description="A mix.")

    with pytest.raises(DomainValidationError, match="name must not be empty"):
        Preset(id="balanced", name="  ", description="A mix.")


def test_a_preset_requires_a_description() -> None:
    with pytest.raises(DomainValidationError, match="description must not be empty"):
        Preset(id="balanced", name="Balanced", description="")


def test_a_preset_requires_a_constraint_set() -> None:
    with pytest.raises(DomainValidationError, match="must be a ConstraintSet"):
        Preset(
            id="balanced",
            name="Balanced",
            description="A mix.",
            constraints=(Constraint.max_weight(Ticker("VOO"), 0.4),),  # type: ignore[arg-type]
        )


def test_with_constraints_returns_a_copy() -> None:
    # Presets are shared configuration. Mutating one in place would change what
    # every other user of that preset sees.
    preset = get_preset(PresetId.BALANCED)
    limits = ConstraintSet((Constraint.max_weight(AssetClass.EQUITY, 0.70),))

    constrained = preset.with_constraints(limits)

    assert constrained.constraints is limits
    assert len(preset.constraints) == 0
    assert constrained.name == preset.name


def test_a_preset_may_carry_views() -> None:
    preset = Preset(
        id="balanced",
        name="Balanced",
        description="A mix.",
        default_confidence=Confidence.LOW,
        views=(View.absolute("VOO", 0.07),),
    )
    assert preset.views[0].ticker == Ticker("VOO")
    assert preset.default_confidence is Confidence.LOW


def test_a_preset_rejects_non_view_entries() -> None:
    with pytest.raises(DomainValidationError, match="must be View objects"):
        Preset(
            id="balanced",
            name="Balanced",
            description="A mix.",
            views=("VOO",),  # type: ignore[arg-type]
        )
