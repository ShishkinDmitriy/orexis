"""The manifest: what this capability contributes to a build.

One of the two ways of reviewing. `review:Consulting` — asking a model instead of working it out — is
declared in `ontology.ttl` and deliberately absent here, exactly as `sensing:Polling` is for
sensing: the vocabulary should be honest that the judgement is the replaceable part, but
nothing implements this one yet and granting a capability no module provides only produces a
startup warning. Adding it is a class and one line of `PROVIDES`; no other package moves.
"""

from pathlib import Path

from assembly import contributes, DERIVATION, SHAPES, VOCABULARY
from .terms import CONSULTING, RECKONING, REVIEW

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
    from .module import ReviewModule

    return (ReviewModule,)

__all__ = ["REVIEW", "RECKONING", "CONSULTING"]
