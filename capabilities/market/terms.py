"""The terms this package implements — the Python end of `ontology.ttl`.

Also the terms it *refers to*. A capability that needs something from another names that
other's family term and asks the agent for a provider; it never imports the other's Python.
The term is the interface, exactly as the constitution says.
"""

from __future__ import annotations

from agora.ontology import term

BIDDING = term("Bidding")  # plumbed into a market: it answers offers with a private number
HOSTING = term("Hosting")  # owns the venue: it runs rounds

# --- what this package asks OF others, by family ---
PERCEPTION = term("PerceptionCapability")  # whoever can look, however it looks
ACTUATION = term("Actuation")  # whoever can touch the hardware, if this agent can at all
