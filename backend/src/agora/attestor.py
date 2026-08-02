"""Fuseki = the citable current-state (:attested). The gateway's attestation step.

Overwrites rather than accumulates: one SOSA observation per plant, replaced each
reading. Provenance (prov:wasGeneratedBy :gateway) is the leash hook — agents may cite
this graph but never write it.
"""

from __future__ import annotations

from datetime import datetime, timezone

import requests

from .ontology import ATTESTED_GRAPH

_PREFIXES = """
PREFIX ag:   <http://example.org/agora#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""


class Attestor:
    """Materializes the current-state triple into the :attested named graph."""

    def __init__(self, fuseki_url: str, user: str = "admin", password: str = "admin"):
        self.update_url = fuseki_url.rstrip("/") + "/update"
        self.auth = (user, password)

    def attest(
        self,
        plant_uri: str,
        plant_id: str,
        value: float,
        band: str,
        sensor: str,
        world_version: int | None = None,
        ts: str | None = None,
    ) -> None:
        ts = ts or datetime.now(timezone.utc).isoformat()
        obs = f"ag:obs_{plant_id}"
        # provenance: which world-version was in force when this was sensed
        wv_line = f"    ag:underWorldVersion {int(world_version)} ;\n" if world_version is not None else ""

        # Delete the plant's previous current-state, then insert the fresh observation.
        # Three ops in one request (separated by ';'): idempotent overwrite.
        update = f"""{_PREFIXES}
WITH <{ATTESTED_GRAPH}>
DELETE {{ {obs} ?p ?o }} WHERE {{ {obs} ?p ?o }} ;
WITH <{ATTESTED_GRAPH}>
DELETE {{ <{plant_uri}> ag:hasCurrentMoisture ?b }}
WHERE  {{ <{plant_uri}> ag:hasCurrentMoisture ?b }} ;
INSERT DATA {{ GRAPH <{ATTESTED_GRAPH}> {{
  {obs} a sosa:Observation ;
    sosa:hasFeatureOfInterest <{plant_uri}> ;
    sosa:observedProperty ag:SoilMoisture ;
    sosa:hasSimpleResult "{value}"^^xsd:decimal ;
    ag:qualitativeBand ag:{band} ;
    sosa:resultTime "{ts}"^^xsd:dateTime ;
    sosa:madeBySensor ag:{sensor} ;
{wv_line}    prov:wasGeneratedBy ag:gateway .
  <{plant_uri}> ag:hasCurrentMoisture ag:{band} .
}} }}
"""
        resp = requests.post(
            self.update_url,
            data={"update": update},
            auth=self.auth,
            timeout=5,
        )
        resp.raise_for_status()
