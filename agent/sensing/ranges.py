"""The ranges that apply to what a sensor observes, in SSN-System's words — read by `predict`
to place a crossing, and by the rules this layer registers to conclude a side. Nothing is
minted: a range is what the world says.

A range is stated by what hosts the sensor (`sosa:isHostedBy` — the subject, or a `sosa:Sample`
of it, which stands for it), by what that host is a sample of, or by the sensor itself: an
operating range or a survival range whose condition is for the property and states a floor and
a ceiling. Both kinds are answered together, since a number crosses either; which kind a range
is rides on it.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.ontology import PUBLIC
from agent.store import graphs_of, remember, rows

_RANGES_Q = """
SELECT DISTINCT ?range ?kind ?low ?high WHERE {
  $sensor (sosa:isHostedBy/(sosa:isSampleOf)?)? ?holder .
  { ?holder ssn-system:hasOperatingRange ?range . BIND(ssn-system:OperatingRange AS ?kind) }
  UNION { ?holder ssn-system:hasSurvivalRange ?range . BIND(ssn-system:SurvivalRange AS ?kind) }
  ?range ssn-system:inCondition ?condition .
  ?condition ssn:forProperty $property ; schema:minValue ?low ; schema:maxValue ?high }
ORDER BY ?range"""


@dataclass(frozen=True)
class Range:
    """One range the world states: which node it is, which kind, and its two bounds."""

    uri: str
    kind: str
    low: float
    high: float

    def side(self, value: float) -> int:
        """Which side of this range a number lies on: -1 under the floor, 0 inside, bounds
        included, +1 over the ceiling — the same reading the registered rules take."""
        return -1 if value < self.low else 1 if value > self.high else 0


def ranges_of(store, sensor: str, observed_property: str, memo=None) -> list[Range]:
    """Every range that applies to what `sensor` observes of `observed_property`: its host's,
    its host's subject's where the host is a sample, and its own, off public knowledge.
    Remembered per pass where a memo is given."""
    return remember(memo, ("ranges", sensor, observed_property), lambda: [
        Range(r["range"], r["kind"], float(r["low"]), float(r["high"]))
        for r in rows(store, _RANGES_Q, graphs_of(store, PUBLIC), sensor=sensor, property=observed_property)])
