"""Reading attested testimony — the agent's cite-a-fact path.

Queries Fuseki `:attested` (the witness of record) for a plant's current moisture. This is
the looser-leash qualitative path: read-only SPARQL over a small, gateway-signed graph.
Agents cite it; they never write it. See knowledge/domain/belief-base.md.
"""

from __future__ import annotations

import requests

from .ontology import ATTESTED_GRAPH, SOSA


def _parse_moisture(results: dict) -> float | None:
    """Pull the attested moisture value out of a SPARQL-JSON result, or None."""
    bindings = results.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    return float(bindings[0]["value"]["value"])


class Beliefs:
    """Read-only view of the attested *measurement*. The band (LOW/OK/HIGH) is the
    agent's own judgment, computed from this value — not read from here."""

    def __init__(self, fuseki_url: str):
        # secoresearch/fuseki serves queries at /ds/sparql (not /ds/query).
        self.query_url = fuseki_url.rstrip("/") + "/sparql"

    def current_moisture(self, plant_uri: str) -> float | None:
        query = f"""
PREFIX sosa: <{SOSA}>
SELECT ?value WHERE {{
  GRAPH <{ATTESTED_GRAPH}> {{
    ?obs sosa:hasFeatureOfInterest <{plant_uri}> ;
         sosa:hasSimpleResult ?value .
  }}
}} LIMIT 1"""
        resp = requests.get(
            self.query_url,
            params={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=5,
        )
        resp.raise_for_status()
        return _parse_moisture(resp.json())
