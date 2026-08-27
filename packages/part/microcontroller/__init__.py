"""What `part/microcontroller` brings to a build.

Knowledge only: it contributes vocabulary and no behaviour, which is why there is no
`provides()` below. A board has no code a runtime could load.
"""

from pathlib import Path

from assembly import contributes, SHAPES, VOCABULARY

@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the vocabulary — what its terms mean."""
    return [package / "ontology.ttl"]

@contributes(SHAPES)
def shapes(package: Path) -> list[Path]:
    """what must be true of a thing that has it."""
    return [package / "shapes.ttl"]
