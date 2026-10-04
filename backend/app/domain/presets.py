"""Role-based presets.

A preset is a named, reusable bundle of a :class:`~app.domain.constraints.ConstraintSet`,
a default confidence, and optional default views. It composes the domain models
rather than restating their fields as loose configuration, so a preset cannot
drift from the constraint vocabulary.

**The financial numbers are not here.** Conservative / Balanced / Growth are
product assumptions, and choosing them is a separate, deliberate piece of work
with its own validation. This task defines the *container* and registers the
three names so the vocabulary is stable; every constraint set is deliberately
empty until that decision is made and documented. A preset with no constraints is
honest about having no opinion yet -- better than a plausible-looking number that
nobody chose on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.constraints import ConstraintSet
from app.domain.types import DomainValidationError
from app.domain.views import Confidence, View


class PresetId:
    """Stable preset identifiers.

    Plain string constants rather than an enum: a preset is a product concept
    that grows by adding an entry to :data:`PRESETS`, and an enum would make an
    added preset a code change in two places.
    """

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    GROWTH = "growth"


@dataclass(frozen=True, slots=True)
class Preset:
    """A named, reusable optimization configuration.

    Attributes
    ----------
    id:
        Stable machine identifier, e.g. ``"balanced"``.
    name:
        Display name.
    description:
        One plain-language sentence. Must not promise an outcome.
    constraints:
        Default limits. May be empty; see the module docstring.
    default_confidence:
        Confidence applied to views that do not state their own.
    views:
        Default views, if the preset implies any.
    """

    id: str
    name: str
    description: str
    constraints: ConstraintSet = field(default_factory=ConstraintSet)
    default_confidence: Confidence = Confidence.MEDIUM
    views: tuple[View, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "views", tuple(self.views))
        if not self.id.strip():
            raise DomainValidationError("preset.id must not be empty")
        if not self.name.strip():
            raise DomainValidationError(f"preset {self.id!r}: name must not be empty")
        if not self.description.strip():
            raise DomainValidationError(f"preset {self.id!r}: description must not be empty")
        if not isinstance(self.constraints, ConstraintSet):
            raise DomainValidationError(f"preset {self.id!r}: constraints must be a ConstraintSet")
        for view in self.views:
            if not isinstance(view, View):
                raise DomainValidationError(f"preset {self.id!r}: views must be View objects")

    def with_constraints(self, constraints: ConstraintSet) -> Preset:
        """A copy carrying different constraints."""
        return Preset(
            id=self.id,
            name=self.name,
            description=self.description,
            constraints=constraints,
            default_confidence=self.default_confidence,
            views=self.views,
        )


#: The three initial presets. Constraint sets are intentionally empty pending the
#: documented product decision on their numbers.
PRESETS: dict[str, Preset] = {
    PresetId.CONSERVATIVE: Preset(
        id=PresetId.CONSERVATIVE,
        name="Conservative",
        description="Leans toward government bonds and limits how much can go into any one ETF.",
    ),
    PresetId.BALANCED: Preset(
        id=PresetId.BALANCED,
        name="Balanced",
        description="A mix of stocks and bonds, without leaning hard either way.",
    ),
    PresetId.GROWTH: Preset(
        id=PresetId.GROWTH,
        name="Growth",
        description="Leans toward stocks and accepts more movement for longer-term growth.",
    ),
}


def get_preset(preset_id: str) -> Preset:
    """Return a preset, raising :class:`KeyError` for an unknown id."""
    try:
        return PRESETS[preset_id]
    except KeyError as exc:
        known = ", ".join(sorted(PRESETS))
        raise KeyError(f"unknown preset {preset_id!r}; expected one of: {known}") from exc
