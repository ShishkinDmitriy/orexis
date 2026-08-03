"""The terms this package implements — the Python end of `ontology.ttl`.

Every capability package names its terms in one small file like this, so nothing central has
to know they exist. `term()` builds the IRI from the kernel prefix; nothing is imported from
another capability, because a term is spelled the same way wherever it is referred to.
"""

from __future__ import annotations

from agora.ontology import term

# The family. Anything that perceives is one of these — which is what lets another capability
# ask for "whoever perceives" without knowing which way it does it.
PERCEPTION = term("PerceptionCapability")

# The axis is who holds the clock, and these are in decreasing order of agent control.
POLLING = term("Polling")  # the agent asks, each time — RESERVED, nothing implements it yet
SUBSCRIBING = term("Subscribing")  # the agent states an interval; the device keeps to it
LISTENING = term("Listening")  # the device announces on its own clock; the agent records
