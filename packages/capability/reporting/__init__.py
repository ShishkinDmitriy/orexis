"""The manifest: what this capability contributes to a build.

One of the two ways of reporting. `reporting:Announcing` — putting the account on the bus rather
than in a series bucket — is declared in `ontology.ttl` and deliberately absent here, exactly as
`review:Consulting` and `sensing:Polling` are: the vocabulary should be honest that the sink is
the replaceable part, but nothing implements this one yet. Adding it is a class and one line of
`PROVIDES`; no other package moves.

The two would fail independently, which is the reason it is the member worth building next — and
also its limit: a member reporting over the bus cannot report having lost the bus.
"""

from pathlib import Path

from assembly import contributes, DERIVATION, SHAPES, VOCABULARY
from .terms import ANNOUNCING, INTERVAL_S, REPORTING, STORING

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
    from .module import StoringModule

    return (StoringModule,)

__all__ = ["REPORTING", "STORING", "ANNOUNCING", "INTERVAL_S"]
