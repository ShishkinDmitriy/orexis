"""The manifest: a BRIDGE between two planning domains, and no Python at all.

The tower (#523, a-level-is-a-vocabulary-and-a-bridge): hanoi's disks and pegs on the
courier's grid. Hanoi's Move is planned at its own level and taken by nobody; this package
says what a Move's promise means in the courier's words — the disk at the target peg's cell
— and how far that is, so the level beneath plans the drives. One axiom, one bridge, one
estimate, and a world that names both domains.
"""
from pathlib import Path

from assembly import contributes, VOCABULARY


@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the vocabulary — the bridge, and the axiom that makes a disk a parcel."""
    return [package / "ontology.ttl"]
