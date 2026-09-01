"""The manifest: a second planning DOMAIN, no Python at all.

A courier on a grid — the world that makes a heuristic worth having. Hanoi's want is binary,
so no world is nearer than another and nothing can guide a search; here the distance to a
parcel is a NUMBER in the same units a move costs, which is what an admissible heuristic
needs. Three actions, one of which is the first effect in this repository that genuinely
DELETES.
"""

from pathlib import Path

from assembly import contributes, ACTIONS, VOCABULARY

@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the vocabulary — what its terms mean."""
    return [package / "ontology.ttl"]

@contributes(ACTIONS)
def actions(package: Path) -> list[Path]:
    """the ways of acting it brings."""
    return [package / "actions.ttl"]
