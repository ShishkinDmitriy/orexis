"""Writing what a sensor read into :sensed — the agent's own assertion.

Trusted-agent mode: no witness, so the reading is authored by the agent that polled it
(`prov:wasGeneratedBy`). Everything about the observation is passed in from the world — the
subject, the sensor, and which property it observes — so nothing here knows a name.

One observation per subject, replaced each reading; the *series* lives in Influx. The
observation's own IRI is minted from the subject id, and nothing ever looks it up by that
name: readers match on `sosa:hasFeatureOfInterest`.

See knowledge/decisions/trusted-agent-mode.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .ontology import SENSED_GRAPH
from .store import Store


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
        obs = f"ag:obs_{subject_id}"
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
