"""What `plant/water` brings to a build.

Knowledge only: it contributes vocabulary and no behaviour, which is why there is no
`provides()` below. A domain says what is sensed and allocated; it runs nothing.
"""

from pathlib import Path

from assembly import ACTIONS, contributes, DERIVATION, SHAPES, VOCABULARY

@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the vocabulary — what its terms mean."""
    return [package / "ontology.ttl"]

@contributes(ACTIONS)
def actions(package: Path) -> list[Path]:
    """what the world does to a pot while nobody waters it — a DRIFT and no action (#592).

    The point is named ACTIONS and this file carries no `orexis:Action`, which is the honest
    reading of it: what a package contributes here is what the store's action graph holds —
    the rules a search runs — and a drift is one of those with nobody choosing it.
    """
    return [package / "actions.ttl"]

@contributes(SHAPES)
def shapes(package: Path) -> list[Path]:
    """what must be true of a thing that has it."""
    return [package / "shapes.ttl"]

@contributes(DERIVATION)
def derivation(package: Path) -> list[Path]:
    """the premise that grants it."""
    return [package / "rules.ru"]
