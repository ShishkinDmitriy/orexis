"""The plant's own sensed-data writer (trusted-agent mode — no witness).

Each plant asserts its current reading into :sensed as its *own* opinion —
prov:wasGeneratedBy the plant itself, not a gateway. Overwrites: one SOSA observation per
plant, replaced each reading. See knowledge/decisions/trusted-agent-mode.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

import requests

from .ontology import SENSED_GRAPH

_PREFIXES = """
PREFIX ag:   <http://example.org/agora#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""


class SensedWriter:
    """Writes a plant's self-asserted current reading into the :sensed graph."""

    def __init__(self, fuseki_url: str, user: str = "admin", password: str = "admin"):
        self.update_url = fuseki_url.rstrip("/") + "/update"
        self.auth = (user, password)

    def write(
        self,
        plant_uri: str,
        plant_id: str,
        value: float,
        sensor: str,
        world_version: int | None = None,
        ts: str | None = None,
    ) -> None:
        ts = ts or datetime.now(timezone.utc).isoformat()
        obs = f"ag:obs_{plant_id}"
        wv_line = f"    ag:underWorldVersion {int(world_version)} ;\n" if world_version is not None else ""

        # Self-asserted: authored by the plant, not a gateway. Overwrite prior observation.
        update = f"""{_PREFIXES}
WITH <{SENSED_GRAPH}>
DELETE {{ {obs} ?p ?o }} WHERE {{ {obs} ?p ?o }} ;
INSERT DATA {{ GRAPH <{SENSED_GRAPH}> {{
  {obs} a sosa:Observation ;
    sosa:hasFeatureOfInterest <{plant_uri}> ;
    sosa:observedProperty ag:SoilMoisture ;
    sosa:hasSimpleResult "{value}"^^xsd:decimal ;
    sosa:resultTime "{ts}"^^xsd:dateTime ;
    sosa:madeBySensor ag:{sensor} ;
{wv_line}    prov:wasGeneratedBy <{plant_uri}> .
}} }}
"""
        resp = requests.post(self.update_url, data={"update": update}, auth=self.auth, timeout=5)
        resp.raise_for_status()
