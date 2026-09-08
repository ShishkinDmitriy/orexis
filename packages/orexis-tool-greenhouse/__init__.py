"""The manifest: a heated bed, and no Python at all.

The world this exists for holds ONE want about TWO properties — the bed is comfortable when
its soil is in its region and its air is too — which is the first shipped want a single lever
cannot serve. Watering is actuation's, unchanged; warming is this package's one action.

KNOWLEDGE-ONLY, and the heater is deliberately un-taken: nothing contributes
`greenhouse:Heating`, so it is planned and never executed, exactly as hanoi's Move is. What
this world is for is the SEARCH — how a want across two properties is planned, what it costs,
and what happens when one lever's effect reaches into the other property.
"""

from pathlib import Path

from assembly import contributes, ACTIONS, VOCABULARY


@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the vocabulary — what its terms mean."""
    return [package / "ontology.ttl"]


@contributes(ACTIONS)
def actions(package: Path) -> list[Path]:
    """the ways of acting this domain brings."""
    return [package / "actions.ttl"]
