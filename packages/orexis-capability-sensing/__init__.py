"""The manifest: what this capability contributes to a build.

Two of the three sensing capabilities. `sensing:Polling` is declared in the vocabulary and
deliberately absent here: it needs a device that is reachable at any moment, and nothing in
this world is. Adding it later is a class and one line of PROVIDES — no other package moves.
"""

from pathlib import Path

from assembly import contributes, ACTIONS, DERIVATION, REVIEW, SHAPES, VOCABULARY, WANTS
from .terms import LISTENING, SENSING, POLLING, SUBSCRIBING

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

@contributes(ACTIONS)
def actions(package: Path) -> list[Path]:
    """the ways of acting it brings."""
    return [package / "actions.ttl"]

@contributes(REVIEW)
def review(package: Path) -> list[Path]:
    """what an agent may reconsider about itself."""
    return [package / "review.rq"]

def provides() -> tuple:
    """The classes this package contributes. Imported HERE and not at the top, so an
    agent granted none of them never pays for the import (#216) — and a missing optional
    extra costs only the agents that were granted the capability needing it."""
    from .module import SubscribingModule, ListeningModule

    return (SubscribingModule, ListeningModule)

__all__ = ["SENSING", "POLLING", "SUBSCRIBING", "LISTENING"]
