"""The terms this package implements — the Python end of `ontology.ttl`."""

from __future__ import annotations

from agora.ontology import term

# A member of perception's family, so "whoever perceives" finds it. Referring to another
# package's family term is how that works; importing its Python is not.
PERCEPTION = term("PerceptionCapability")

SIMULATED_SENSING = term("SimulatedSensing")
