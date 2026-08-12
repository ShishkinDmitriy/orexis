"""The terms this package implements — the Python end of `ontology.ttl`.

Every capability package names its terms in one small file like this, so nothing central has
to know they exist. **This package owns a namespace**, and `term()` here builds into it —
perceiving is what an agent wired to a sensor does, not what every agent does, so `ag:` was
never the right place for it. `tests/test_layout.py` holds `NS` and the `@prefix` in
`ontology.ttl` together.
"""

from __future__ import annotations

NS = "http://example.org/agora/perception#"


def term(name: str) -> str:
    """A term of this package's, by local name."""
    return NS + name

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
PULL = term("PolledSampling")           # answers when asked — the unbuilt perception:Polling would serve it
SCHEDULED = term("ScheduledSampling")   # keeps an interval it is given -> perception:Subscribing
PUSH = term("PushReporting")            # keeps its own clock, takes no orders -> perception:Listening
