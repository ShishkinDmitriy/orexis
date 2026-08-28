"""What `tool/wokwi` brings to a build.

Knowledge only: it contributes vocabulary and no behaviour, which is why there is no
`provides()` below. A rendering concern: it says how a part is DRAWN, and nothing loads it.
"""

from pathlib import Path

from assembly import contributes, VOCABULARY

@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the vocabulary — what its terms mean."""
    return [package / "ontology.ttl"]
