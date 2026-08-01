"""The gateway's one job that isn't plumbing: numeric -> qualitative band.

This is the single authority for what a number *means*. It lives here (gateway side),
never per-agent and never in ESP32 firmware.
"""

from __future__ import annotations

# RDF vocabulary used by the attested current-state graph.
PA = "http://example.org/pa#"
SOSA = "http://www.w3.org/ns/sosa/"
PROV = "http://www.w3.org/ns/prov#"
ATTESTED_GRAPH = "http://example.org/pa/graph/attested"

BANDS = ("LOW", "OK", "HIGH")


def band_for(value: float, low: float, high: float) -> str:
    """Map a raw moisture reading to a qualitative band."""
    if value < low:
        return "LOW"
    if value > high:
        return "HIGH"
    return "OK"
