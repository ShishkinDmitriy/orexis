"""The manifest: what this capability contributes to a build.

One member, `aversion:Heeding` — judging entered-or-held by running the ratified pattern.
A member that asked a model where a pattern cannot be written would be a sibling class and
one line of PROVIDES; no other package moves.
"""

from pathlib import Path

from assembly import contributes, DERIVATION, SHAPES, VOCABULARY, WANTS
from .terms import AVERSION, AVERSION_CAPABILITY, AVOIDS, HEEDING

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

@contributes(WANTS)
def wants(package: Path) -> list[Path]:
    """what holding it makes an agent want."""
    return [package / "desires.ru"]

def provides() -> tuple:
    """The classes this package contributes. Imported HERE and not at the top, so an
    agent granted none of them never pays for the import (#216)."""
    from .module import AversionModule

    return (AversionModule,)

__all__ = ["AVERSION", "AVERSION_CAPABILITY", "AVOIDS", "HEEDING"]
