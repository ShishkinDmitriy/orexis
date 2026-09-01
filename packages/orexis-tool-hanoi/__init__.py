"""The manifest: a planning DOMAIN with no Python at all.

Tower of Hanoi as the plug-in claim under test (#257): an ontology and six ground actions,
loaded like any package's, planned by the ordinary search. No module, no grant, no measure —
the goal is a world-ratified desire judged by its own pattern, and optimality falls out of
`orexis:costs` because the cheapest achiever is the shortest solution.
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
