"""Domain layer: architectural boundaries.

The layering rules in CONTEXT.md are easy to state and easy to break with one
convenient import. These tests turn them into a test failure instead, so the
rules survive the next person who finds a shortcut.

The rules:

* ``app.domain`` imports nothing third-party at all -- no pydantic, no pandas,
  no numpy, no solver library;
* ``app.domain`` imports no other app module except ``app.taxonomy``, which
  holds the canonical enums the domain re-exports;
* the provider layer may reference the domain for type hints only.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2] / "app"
DOMAIN_DIR = APP_DIR / "domain"

#: Standard-library modules a framework-independent domain model may use. Kept
#: deliberately short: adding to this list is a decision, not a convenience.
ALLOWED_STDLIB = frozenset(
    {
        "__future__",
        "collections.abc",
        "dataclasses",
        "datetime",
        "enum",
        "math",
        "re",
        "typing",
    }
)

#: App-internal modules the domain layer may depend on. ``app.taxonomy`` holds
#: the canonical enums the domain re-exports; ``app.domain.*`` is itself.
ALLOWED_APP = frozenset({"app.taxonomy"})

#: Modules the domain must never import, however they are spelled. The universe
#: is the sharpest case: it is *data*, and the domain is the vocabulary that data
#: has to be described in.
FORBIDDEN_APP_PREFIXES = (
    "app.providers",
    "app.universe",
    "app.optimizer",
    "app.models",
    "app.api",
    "app.config",
    "app.main",
)


def domain_modules() -> list[Path]:
    return sorted(DOMAIN_DIR.glob("*.py"))


def dotted_imports(path: Path) -> set[str]:
    """Every module path imported by ``path``, relative imports excluded.

    Full dotted paths, not roots: ``from app.taxonomy import AssetClass`` and
    ``from app.universe import UNIVERSE`` share a root, and collapsing them is
    exactly how a boundary test becomes a rubber stamp.
    """
    tree = ast.parse(path.read_text(), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            found.add(node.module)
    return found


def test_the_domain_package_has_the_expected_modules() -> None:
    assert {p.name for p in domain_modules()} >= {
        "__init__.py",
        "constraints.py",
        "etf.py",
        "market.py",
        "optimization.py",
        "presets.py",
        "types.py",
        "views.py",
    }


@pytest.mark.parametrize("path", domain_modules(), ids=lambda p: p.name)
def test_domain_modules_import_only_the_standard_library_and_the_taxonomy(path: Path) -> None:
    # A domain type that needs a framework is a transport or numerics concern
    # wearing a domain costume, and it makes the model unusable from a backtest.
    # pydantic, pandas, numpy, cvxpy and pypfopt are all absent from
    # ALLOWED_STDLIB, so they cannot slip through this check.
    unapproved = {
        name
        for name in dotted_imports(path)
        if name.split(".")[0] != "__future__"
        and not name.startswith("app.domain")
        and name not in ALLOWED_STDLIB
        and name not in ALLOWED_APP
    }
    assert not unapproved, f"{path.name} imports unapproved {sorted(unapproved)}"


@pytest.mark.parametrize("path", domain_modules(), ids=lambda p: p.name)
def test_domain_modules_do_not_reach_outside_the_domain(path: Path) -> None:
    app_imports = {name for name in dotted_imports(path) if name.startswith("app")}
    outside = {
        name
        for name in app_imports
        if not name.startswith("app.domain") and name not in ALLOWED_APP
    }
    assert not outside, f"{path.name} imports {sorted(outside)}"


@pytest.mark.parametrize("path", domain_modules(), ids=lambda p: p.name)
def test_domain_modules_never_import_a_forbidden_app_module(path: Path) -> None:
    # ast.walk descends into function bodies, so this also catches a deferred
    # ``import app.universe`` smuggled inside a method to dodge an import cycle.
    forbidden = {name for name in dotted_imports(path) if name.startswith(FORBIDDEN_APP_PREFIXES)}
    assert not forbidden, f"{path.name} imports {sorted(forbidden)}"


def test_the_provider_layer_references_the_domain_for_type_hints_only() -> None:
    # ``Asset`` is a provider-boundary type. A *runtime* import of the domain into
    # the provider layer inverts the dependency the layering depends on, so the
    # reference must stay inside ``if TYPE_CHECKING``.
    source = (APP_DIR / "providers" / "base.py").read_text()
    tree = ast.parse(source)

    guarded: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If) and _is_type_checking(node)):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.ImportFrom) and (child.module or "").startswith("app.domain"):
                guarded.append(child.module or "")

    all_domain_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("app.domain")
    ]
    assert all_domain_imports, "expected providers/base.py to type-hint against the domain"
    assert len(guarded) == len(all_domain_imports), (
        "every app.domain import in providers/base.py must sit inside `if TYPE_CHECKING`"
    )


def _is_type_checking(node: ast.If) -> bool:
    test = node.test
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )
