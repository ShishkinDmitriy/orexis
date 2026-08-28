"""What `bus/onewire` brings to a build.

Knowledge only: it contributes vocabulary and no behaviour, which is why there is no
`provides()` below. A protocol is a wiring fact, not code.
"""

from pathlib import Path

from assembly import contributes, VOCABULARY

@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the vocabulary — what its terms mean."""
    return [package / "ontology.ttl"]
