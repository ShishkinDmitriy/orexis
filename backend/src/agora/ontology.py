"""The gateway's one job that isn't plumbing: numeric -> qualitative band.

This is the single authority for what a number *means*. It lives here (gateway side),
never per-agent and never in ESP32 firmware.
"""

from __future__ import annotations

# RDF vocabulary. Terms are defined in the shared T-Box (ontology/agora.ttl); these are the
# canonical IRIs the code references. The named graphs are typed, self-describing resources
# (agora:AttestedGraph, etc.) — the meaning lives in RDF, not in the string.
AG = "http://example.org/agora#"
SOSA = "http://www.w3.org/ns/sosa/"
PROV = "http://www.w3.org/ns/prov#"

_GRAPH = "http://example.org/agora/graph/"
ONTOLOGY_GRAPH = _GRAPH + "ontology"   # the T-Box
STRUCTURE_GRAPH = _GRAPH + "structure"  # sovereign-authored: topology, charters, world version
ATTESTED_GRAPH = _GRAPH + "attested"    # gateway-sensed current state

BANDS = ("LOW", "OK", "HIGH")


def band_for(value: float, low: float, high: float) -> str:
    """Map a raw moisture reading to a qualitative band."""
    if value < low:
        return "LOW"
    if value > high:
        return "HIGH"
    return "OK"
