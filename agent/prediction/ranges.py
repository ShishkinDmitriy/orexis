"""The ranges that apply to what a sensor observes, in SSN-System's words — read by `predict`
to place a crossing, and by the rules sensing ships to conclude a side. Nothing is
minted: a range is what the world says, and what is answered is its two numbers.

A range is stated by what hosts the sensor (`sosa:isHostedBy` — the subject, or a `sosa:Sample`
of it, which stands for it), by what that host is a sample of, or by the sensor itself: an
operating range or a survival range whose condition is for the property and states a floor and
a ceiling. Both kinds are answered together, since a number crosses either, and the crossing
needs nothing but the bounds — which range it is, and of which kind, stays in the store for
whoever asks, and the rules bind the range themselves.
"""

from __future__ import annotations

from agent.ontology import PUBLIC
from agent.store import graphs_of, remember, rows

_BOUNDS_Q = """
SELECT DISTINCT ?low ?high WHERE {
  $sensor (sosa:isHostedBy/(sosa:isSampleOf)?)? ?holder .
  ?holder ssn-system:hasOperatingRange|ssn-system:hasSurvivalRange ?range .
  ?range ssn-system:inCondition ?condition .
  ?condition ssn:forProperty $property ; schema:minValue ?low ; schema:maxValue ?high }
ORDER BY ?low ?high"""


def ranges_of(store, sensor: str, observed_property: str, memo=None) -> list[tuple[float, float]]:
    """The floor and the ceiling of every range that applies to what `sensor` observes of
    `observed_property`: its host's, its host's subject's where the host is a sample, and its
    own, off public knowledge. Remembered per pass where a memo is given."""
    return remember(memo, ("ranges", sensor, observed_property), lambda: [
        (float(r["low"]), float(r["high"]))
        for r in rows(store, _BOUNDS_Q, graphs_of(store, PUBLIC), sensor=sensor, property=observed_property)])


def side(low: float, high: float, value: float) -> int:
    """Which side of a range a number lies on: -1 under the floor, 0 inside, bounds included,
    +1 over the ceiling — the same reading sensing's rules take."""
    return -1 if value < low else 1 if value > high else 0
