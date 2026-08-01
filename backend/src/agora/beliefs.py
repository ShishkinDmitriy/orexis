"""Reading attested testimony — the agent's cite-a-fact path.

Queries Fuseki `:attested` (the witness of record) for a plant's current moisture. This is
the looser-leash qualitative path: read-only SPARQL over a small, gateway-signed graph.
Agents cite it; they never write it. See knowledge/domain/belief-base.md.
"""

from __future__ import annotations

import requests

from .ontology import AG, ATTESTED_GRAPH, SOSA


def _parse_current_state(results: dict) -> tuple[float, str] | None:
    """Pull (value, band) out of a SPARQL-JSON result, or None if unattested."""
    bindings = results.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    row = bindings[0]
    value = float(row["value"]["value"])
    band_uri = row["band"]["value"]
    band = band_uri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]  # local name
    return value, band


class Beliefs:
    """Read-only view of the attested current-state graph."""

    def __init__(self, fuseki_url: str):
        # secoresearch/fuseki serves queries at /ds/sparql (not /ds/query).
        self.query_url = fuseki_url.rstrip("/") + "/sparql"

    def current_state(self, plant_uri: str) -> tuple[float, str] | None:
        query = f"""
PREFIX ag:   <{AG}>
PREFIX sosa: <{SOSA}>
SELECT ?value ?band WHERE {{
  GRAPH <{ATTESTED_GRAPH}> {{
    ?obs sosa:hasFeatureOfInterest <{plant_uri}> ;
         sosa:hasSimpleResult ?value ;
         ag:qualitativeBand ?band .
  }}
}} LIMIT 1"""
        resp = requests.get(
            self.query_url,
            params={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=5,
        )
        resp.raise_for_status()
        return _parse_current_state(resp.json())

    def current_moisture(self, plant_uri: str) -> float | None:
        state = self.current_state(plant_uri)
        return state[0] if state else None
