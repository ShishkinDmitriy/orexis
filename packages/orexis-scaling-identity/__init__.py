"""The manifest: what this scaling contributes to a build."""

from pathlib import Path

from assembly import contributes, DERIVATION, SHAPES, VOCABULARY

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

def provides() -> tuple:
    """The classes this package contributes. Imported HERE and not at the top, so an
    agent granted none of them never pays for the import (#216) — and a missing optional
    extra costs only the agents that were granted the capability needing it."""
    from .scaling import IdentityScaling

    return (IdentityScaling,)
