"""What a reading looks like — sensing's, and asked of sensing.

`agent/beliefs.py` used to hold `Reading` and `current_reading`: the kernel knowing that a
belief about a property is a sosa observation with a result and a time, walking
`sosa:isSampleOf` for a sampled subject. That is what a reading LOOKS LIKE, and it is this
package's (the-stake-is-sensings-want): the same dataclass and the same query, one directory
over, and every caller reaches them through the sensing provider or, for a world a plan is
imagining, through `value_in` at that world's graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from orexis_progression_patience.ontology import STATE_GRAPH
from orexis_progression_patience.store import bindings


@dataclass(frozen=True)
class Reading:
    """A sensed value plus when it was taken — the pair a decision must cite."""

    value: float
    result_time: datetime | None

    def age_s(self, now: datetime | None = None) -> float | None:
        if self.result_time is None:
            return None
        return ((now or datetime.now(timezone.utc)) - self.result_time).total_seconds()

    def is_fresh(self, max_age_s: float, now: datetime | None = None) -> bool:
        """Untimed readings are never fresh — an unstamped number can't be shown to be current."""
        age = self.age_s(now)
        return age is not None and age <= max_age_s



def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)




def _parse(results) -> Reading | None:
    rows = bindings(results)
    if not rows or rows[0].get("value") is None:
        return None
    return Reading(value=float(rows[0]["value"]), result_time=_parse_datetime(rows[0].get("ts")))


def current_reading(query, subject_uri: str, observed_property: str,
                    state: str = STATE_GRAPH) -> Reading | None:
    """The newest reading of one property of one subject — or of a patch of it (#98): an
    observation of a `sosa:Sample` answers for what it samples. The sample link lives in the
    world graph and the observation in the sensed graph, so the walk sits OUTSIDE the GRAPH
    clause (AGENTS.md's narrowed-SELECT trap). Newest-across-patches is not aggregation."""
    return _parse(query(f"""
SELECT ?value ?ts WHERE {{
  {{ BIND(<{subject_uri}> AS ?foi) }} UNION {{ ?foi sosa:isSampleOf <{subject_uri}> }}
  GRAPH <{state}> {{
    ?obs sosa:hasFeatureOfInterest ?foi ;
         sosa:observedProperty <{observed_property}> ;
         sosa:hasSimpleResult ?value .
    OPTIONAL {{ ?obs sosa:resultTime ?ts }}
  }}
}} ORDER BY DESC(?ts) LIMIT 1"""))


def value_in(query, graph: str, subject_uri: str, observed_property: str) -> float | None:
    """What a property reads in the world `query` answers about, at `graph` — the planner's
    question about a candidate world, and the same query as `current_reading`'s."""
    reading = current_reading(query, subject_uri, observed_property, state=graph)
    return reading.value if reading is not None else None
