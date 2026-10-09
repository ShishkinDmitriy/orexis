"""The ranges that apply to what a sensor observes, in SSN-System's words — read by `predict`
to place a crossing, and by the rules sensing ships to conclude a side. Nothing is
minted: a range is what the world says, and what is answered is its two numbers, its margin
and its name.

A range is stated by what hosts the sensor (`sosa:isHostedBy` — the subject, or a `sosa:Sample`
of it, which stands for it), by what that host is a sample of, or by the sensor itself: an
operating range or a survival range whose condition is for the property and states a floor and
a ceiling. Both kinds are answered together, since a number crosses either, and the crossing
needs nothing but the bounds and the margin — which kind it is stays in the store for whoever
asks, and the rules bind the range themselves.

**A MARGIN WIDENS A BOUND FOR A READING COMING FROM BEYOND IT** (`orexis:margin`, the kernel's,
knowledge/domain/kernel/margin.md): one judged below stays below until the floor and the margin, one
judged above stays above until the ceiling less it, and a condition stating none has a margin of
nought. `side` takes the same judgment the rules take, so a number this package writes is one the
rules conclude the side of that the package placed it on.
"""

from __future__ import annotations

from typing import NamedTuple

from agent.ontology import PUBLIC
from agent.store import graphs_of, remember, rows

#  EVERY RANGE FOR THE PROPERTY, with its name where it has one and its margin, nought where its
#  condition states none. A blank range is answered nameless and with a margin of nought whatever it
#  states: a side carried names its range, so none is ever carried for a blank one, the rules judge
#  it bare, and so must the crossing (`orexis-onboard` refuses such a margin besides).
_BOUNDS_Q = """
SELECT DISTINCT ?named ?low ?high ?margin WHERE {
  $sensor (sosa:isHostedBy/(sosa:isSampleOf)?)? ?holder .
  ?holder ssn-system:hasOperatingRange|ssn-system:hasSurvivalRange ?range .
  ?range ssn-system:inCondition ?condition .
  ?condition ssn:forProperty $property ; schema:minValue ?low ; schema:maxValue ?high
  OPTIONAL { ?condition orexis:margin ?stated }
  BIND(IF(isIRI(?range), COALESCE(?stated, 0), 0) AS ?margin)
  BIND(IF(isIRI(?range), STR(?range), "") AS ?named) }
ORDER BY ?low ?high ?named"""


class Range(NamedTuple):
    """One range that applies to what a sensor observes: its IRI, None for a blank one; its floor
    and its ceiling; and its margin, nought where its condition states none or the range is blank."""
    iri: str | None
    low: float
    high: float
    margin: float = 0.0


def ranges_of(store, sensor: str, observed_property: str, memo=None) -> list[Range]:
    """Every range that applies to what `sensor` observes of `observed_property`: its host's, its
    host's subject's where the host is a sample, and its own, off public knowledge, lowest floor
    first. Remembered per pass where a memo is given."""
    return remember(memo, ("ranges", sensor, observed_property), lambda: [
        Range(r["named"] or None, float(r["low"]), float(r["high"]), float(r["margin"]))
        for r in rows(store, _BOUNDS_Q, graphs_of(store, PUBLIC), sensor=sensor, property=observed_property)])


def side(low: float, high: float, value: float, margin: float = 0.0, was: int = 0) -> int:
    """Which side of a range a number lies on, the reading before it having been on `was`: -1 under
    the floor, or short of the floor and `margin` where it was below; +1 over the ceiling, or past
    the ceiling less `margin` where it was above; 0 inside, bounds included — the same judgment
    sensing's rules take."""
    if value < low or (was < 0 and value < cleared(low, margin)):
        return -1
    if value > high or (was > 0 and value > cleared(high, -margin)):
        return 1
    return 0


def cleared(bound: float, by: float) -> float:
    """`bound` moved `by`, rounded off its binary error: where a reading leaves the side beyond the
    bound — the floor and the margin, `by` the margin, or the ceiling less it, `by` its negation.
    The rules add two decimals exactly, and a float sum would put 0.3 + 0.0002 a hair off the 0.3002
    a reading is written as, and judge that reading on the other side."""
    return round(bound + by, 12)
