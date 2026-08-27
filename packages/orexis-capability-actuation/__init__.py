"""The manifest: what this capability contributes to a build.

Note what is absent: a `beliefs.py`. This capability decides nothing, so there is nothing for
its holder to believe — it reads the device's own calibration from the world and obeys.
"""

from pathlib import Path

from assembly import contributes, ACTIONS, DERIVATION, SHAPES, VOCABULARY
from .terms import ACTUATION

@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the vocabulary — what its terms mean."""
    return [package / "ontology.ttl"]

@contributes(SHAPES)
def shapes(package: Path) -> list[Path]:
    """what must be true of a thing that has it."""
    return [package / "shapes.ttl"]

@contributes(DERIVATION)
def derivation(package: Path) -> list[Path]:
    """the premise that grants it."""
    return [package / "rules.ru"]

@contributes(ACTIONS)
def actions(package: Path) -> list[Path]:
    """the ways of acting it brings."""
    return [package / "actions.ttl"]

def provides() -> tuple:
    """The classes this package contributes. Imported HERE and not at the top, so an
    agent granted none of them never pays for the import (#216) — and a missing optional
    extra costs only the agents that were granted the capability needing it."""
    from .module import ActuationModule

    return (ActuationModule,)

__all__ = ["Command", "ACTUATION"]
