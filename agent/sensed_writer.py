"""Writing what a sensor read into :sensed — the agent's own assertion.

Trusted-agent mode: no witness, so the reading is authored by the agent that polled it
(`prov:wasGeneratedBy`). Everything about the observation is passed in from the world — the
subject, the sensor, and which property it observes — so nothing here knows a name.

One observation per subject **and observed property**, replaced each reading; the *series*
lives in Influx. The property is part of the identity because a subject can be watched by more
than one sensor: a pot with a moisture probe and a thermometer is one feature of interest with
two properties, and keying on the subject alone made the two overwrite each other. Worse than
the loss was the substitution — a lookup by subject returned whichever had written last, so a
caller asking for moisture could be handed a temperature, a plausible number in the wrong unit
that a market will act on without hesitating.

The observation's own IRI is minted from the subject id and the property's local name, and
nothing ever looks it up by that name: readers match on `sosa:hasFeatureOfInterest` and
`sosa:observedProperty`. The IRI only has to be stable and distinct, which is why sanitising
it down to word characters is safe.

See knowledge/decisions/trusted-agent-mode.md and decisions/one-agent-many-sensors.md.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .ontology import SENSED_GRAPH
from .store import Store


def _slug(uri: str) -> str:
    """The local name of a term, safe to paste into an IRI."""
    return re.sub(r"[^A-Za-z0-9_]", "_", re.split(r"[#/]", uri.rstrip("#/"))[-1])


def observation_uri(subject_id: str, observed_property: str) -> str:
    """The node one (subject, property) pair owns. Two properties, two nodes."""
    return f"ag:obs_{_slug(subject_id)}_{_slug(observed_property)}"


class SensedWriter:
    def __init__(self, store: Store):
        self.store = store

    def write(
        self,
        subject_uri: str,
        subject_id: str,
        value: float,
        sensor_uri: str,
        observed_property: str,
        author_uri: str,
        world_version: int | None = None,
        ts: str | None = None,
    ) -> None:
        ts = ts or datetime.now(timezone.utc).isoformat()
        obs = observation_uri(subject_id, observed_property)
        wv = f"    ag:underWorldVersion {int(world_version)} ;\n" if world_version is not None else ""

        self.store.update(f"""
WITH <{SENSED_GRAPH}>
DELETE {{ {obs} ?p ?o }} WHERE {{ {obs} ?p ?o }} ;
INSERT DATA {{ GRAPH <{SENSED_GRAPH}> {{
  {obs} a sosa:Observation ;
    sosa:hasFeatureOfInterest <{subject_uri}> ;
    sosa:observedProperty <{observed_property}> ;
    sosa:hasSimpleResult "{value}"^^xsd:decimal ;
    sosa:resultTime "{ts}"^^xsd:dateTime ;
    sosa:madeBySensor <{sensor_uri}> ;
{wv}    prov:wasGeneratedBy <{author_uri}> .
}} }}
""")
