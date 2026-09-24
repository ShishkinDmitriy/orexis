"""The ranges a subject states for a property, in SSN-System's words — read by `predict` to
place a crossing, and by the rules this layer registers to conclude a side. Nothing is
minted: a range is what the world says.

A range is the subject's own or an instrument's that monitors it, an operating range or a
survival range, whose condition is for the property and states a floor and a ceiling. Both
kinds are answered together, since a number crosses either; which kind a range is rides on it.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.ontology import PUBLIC
from agent.store import graphs_of, remember, rows

_RANGES_Q = """
SELECT DISTINCT ?range ?kind ?low ?high WHERE {
  { $subject ssn-system:hasOperatingRange ?range . BIND(ssn-system:OperatingRange AS ?kind) }
  UNION { $subject ssn-system:hasSurvivalRange ?range . BIND(ssn-system:SurvivalRange AS ?kind) }
  UNION { ?instrument sensing:monitors $subject ; ssn-system:hasOperatingRange ?range . BIND(ssn-system:OperatingRange AS ?kind) }
  UNION { ?instrument sensing:monitors $subject ; ssn-system:hasSurvivalRange ?range . BIND(ssn-system:SurvivalRange AS ?kind) }
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


def ranges_of(store, subject: str, observed_property: str, memo=None) -> list[Range]:
    """Every range `subject` states for `observed_property`, itself or through an instrument
    that monitors it, off public knowledge. Remembered per pass where a memo is given."""
    return remember(memo, ("ranges", subject, observed_property), lambda: [
        Range(r["range"], r["kind"], float(r["low"]), float(r["high"]))
        for r in rows(store, _RANGES_Q, graphs_of(store, PUBLIC), subject=subject, property=observed_property)])
