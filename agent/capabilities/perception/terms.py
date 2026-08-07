"""The terms this package implements — the Python end of `ontology.ttl`.

Every capability package names its terms in one small file like this, so nothing central has
to know they exist. `term()` builds the IRI from the kernel prefix; nothing is imported from
another capability, because a term is spelled the same way wherever it is referred to.
"""

from __future__ import annotations

from agent.ontology import term

# The family. Anything that perceives is one of these — which is what lets another capability
# ask for "whoever perceives" without knowing which way it does it.
PERCEPTION = term("PerceptionCapability")

# The axis is who holds the clock, and these are in decreasing order of agent control.
POLLING = term("Polling")  # the agent asks, each time — RESERVED, nothing implements it yet
SUBSCRIBING = term("Subscribing")  # the agent states an interval; the device keeps to it
LISTENING = term("Listening")  # the device announces on its own clock; the agent records

# The other end of the same axis: what a DEVICE is, from which the capability above is derived.
# A module names the mode it serves so it can take only the sensors it is actually for — the
# pairing is stated in rules.ru as well, and the alternative is introspecting a SPARQL update to
# recover it, which is worse. Both are T-Box terms, which the first rule permits in code.
PULL = term("Pull")            # answers when asked — the unbuilt ag:Polling would serve it
SCHEDULED = term("Scheduled")  # keeps an interval it is given -> ag:Subscribing
PUSH = term("Push")            # keeps its own clock, takes no orders -> ag:Listening
